import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from .tavily_search import TavilySearch

# Exa is an optional dependency for Tavily-only runs.
# `exa_search` imports `exa_py`, which may not be installed in the current environment.
try:
    from .exa_search import ExaSearch  # type: ignore
except ModuleNotFoundError:
    ExaSearch = None  # type: ignore


class AllAccountsExhausted(Exception):
    """Raised when no API accounts have remaining credits."""


@dataclass
class AccountRecord:
    api_key: str
    label: str
    credit_limit: int
    used: int = 0

    @property
    def remaining(self) -> int:
        return max(self.credit_limit - self.used, 0)


@dataclass
class AccountState:
    provider: str
    accounts: List[AccountRecord] = field(default_factory=list)
    current_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "current_index": self.current_index,
            "accounts": [
                {
                    "api_key": acc.api_key,
                    "label": acc.label,
                    "credit_limit": acc.credit_limit,
                    "used": acc.used,
                }
                for acc in self.accounts
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccountState":
        accounts = [
            AccountRecord(
                api_key=a["api_key"],
                label=a.get("label", ""),
                credit_limit=int(a.get("credit_limit", 0)),
                used=int(a.get("used", 0)),
            )
            for a in data.get("accounts", [])
        ]
        return cls(
            provider=data.get("provider", ""),
            current_index=int(data.get("current_index", 0)),
            accounts=accounts,
        )


class AccountManager:
    """
    Rotate across multiple API accounts based on credit usage.

    Keys file: api_evaluation/keys/<provider>_keys.json
      {
        "accounts": [
          {"api_key": "...", "label": "exa_1", "credit_limit": 1000},
          ...
        ]
      }

    State file: api_evaluation/state/account_state.json
      - Tracks used credits per account and current_index.
    """

    BUFFER = 10  # keep at least this many credits unused per account

    def __init__(self, provider: str, keys_path: str, state_path: str) -> None:
        self.provider = provider
        self.keys_path = Path(keys_path)
        self.state_path = Path(state_path)
        self._state = self._load_state()
        self._client_cache: Optional[Any] = None

    # ---------- public API ----------

    def get_search_client(self):
        """Return a search client instance for the current account."""
        record = self._current_account()
        if self.provider == "exa":
            if ExaSearch is None:
                raise ModuleNotFoundError(
                    "Missing optional dependency `exa_py` required for Exa searches. "
                    "Install `exa-py` in the Python environment or run with provider='tavily'."
                )
            client_cls: Type[Any] = ExaSearch
        elif self.provider == "tavily":
            client_cls = TavilySearch
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

        # Recreate client each time to be safe; they are light wrappers.
        self._client_cache = client_cls(api_key=record.api_key)
        return self._client_cache

    def record_queries(self, n: int, *, successful: bool = True) -> None:
        """
        Increment credit usage and rotate account if needed.

        Only counts queries when `successful` is True. Callers should pass
        successful=False when the API returned a 401/invalid-key error or
        otherwise failed before consuming a billable request.
        """
        if n <= 0 or not successful:
            return
        record = self._current_account()
        record.used += n
        self._persist_state()
        if record.used >= max(record.credit_limit - self.BUFFER, 0):
            self._rotate_account()

    def get_status(self) -> Dict[str, Any]:
        """Return a structured view of credit usage."""
        return {
            "provider": self.provider,
            "current_index": self._state.current_index,
            "accounts": [
                {
                    "label": acc.label,
                    "credit_limit": acc.credit_limit,
                    "used": acc.used,
                    "remaining": acc.remaining,
                    "active": i == self._state.current_index,
                }
                for i, acc in enumerate(self._state.accounts)
            ],
        }

    def print_status(self) -> None:
        status = self.get_status()
        print("\n==== Account status ({}) ====".format(status["provider"]))
        for acc in status["accounts"]:
            marker = "*" if acc["active"] else " "
            print(
                f" {marker} {acc['label']}: "
                f"{acc['used']}/{acc['credit_limit']} used "
                f"({acc['remaining']} remaining)"
            )
        print("================================\n")

    # ---------- internal helpers ----------

    def _load_state(self) -> AccountState:
        # Load keys
        if not self.keys_path.exists():
            raise FileNotFoundError(f"Keys file not found: {self.keys_path}")
        with self.keys_path.open(encoding="utf-8") as f:
            data = json.load(f)
        key_accounts = data.get("accounts", [])
        if not key_accounts:
            raise ValueError(f"No accounts found in keys file: {self.keys_path}")

        # Load existing state if present
        if self.state_path.exists():
            with self.state_path.open(encoding="utf-8") as f:
                state_data = json.load(f)
            state = AccountState.from_dict(state_data)
        else:
            accounts = [
                AccountRecord(
                    api_key=a["api_key"],
                    label=a.get("label", f"{self.provider}_{i+1}"),
                    credit_limit=int(a.get("credit_limit", 0)),
                    used=0,
                )
                for i, a in enumerate(key_accounts)
            ]
            state = AccountState(provider=self.provider, accounts=accounts, current_index=0)

        # Ensure state matches keys file (in case of edits)
        if len(state.accounts) != len(key_accounts):
            accounts = []
            for i, a in enumerate(key_accounts):
                # Try to preserve used credits for matching label if possible
                label = a.get("label", f"{self.provider}_{i+1}")
                existing = next((x for x in state.accounts if x.label == label), None)
                used = existing.used if existing else 0
                accounts.append(
                    AccountRecord(
                        api_key=a["api_key"],
                        label=label,
                        credit_limit=int(a.get("credit_limit", 0)),
                        used=used,
                    )
                )
            state.accounts = accounts
            state.current_index = min(state.current_index, len(accounts) - 1)

        # Ensure current_index is valid
        if not state.accounts:
            raise ValueError("No accounts configured.")
        if state.current_index < 0 or state.current_index >= len(state.accounts):
            state.current_index = 0

        # Persist initial state
        self._state = state
        self._persist_state()
        return state

    def _persist_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with self.state_path.open("w", encoding="utf-8") as f:
            json.dump(self._state.to_dict(), f, indent=2)

    def _current_account(self) -> AccountRecord:
        # Skip exhausted accounts
        for _ in range(len(self._state.accounts)):
            acc = self._state.accounts[self._state.current_index]
            if acc.remaining > self.BUFFER:
                return acc
            self._advance_index()
        # If we reach here, all accounts are exhausted
        raise AllAccountsExhausted(f"All {self.provider} accounts exhausted.")

    def _advance_index(self) -> None:
        self._state.current_index = (self._state.current_index + 1) % len(self._state.accounts)
        self._persist_state()

    def _rotate_account(self) -> None:
        """Move to next account if available; raise if all exhausted."""
        # Check if any account has remaining credits
        if not any(acc.remaining > self.BUFFER for acc in self._state.accounts):
            raise AllAccountsExhausted(f"All {self.provider} accounts exhausted.")
        self._advance_index()

