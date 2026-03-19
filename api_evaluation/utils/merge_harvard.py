import csv
import sys
import unicodedata
from pathlib import Path

from api_evaluation.utils.deduplicate import _normalize_name


# Allow running as `python3 -m api_evaluation.utils.merge_harvard` from repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


STATUS_RANK = {
    "complete": 2,
    "partial": 1,
    "needs_review": 0,
}

WEBSITE_CONF_RANK = {
    "high": 3,
    "medium": 2,
    "low": 1,
    "none": 0,
}


def _status_rank(s: str) -> int:
    s = (s or "").strip().lower()
    return STATUS_RANK.get(s, -1)


def _website_conf_rank(s: str) -> int:
    s = (s or "").strip().lower()
    return WEBSITE_CONF_RANK.get(s, -1)


def _is_better(candidate: dict, incumbent: dict) -> bool:
    """
    Prefer:
      1) status=complete over partial over needs_review
      2) higher website_confidence (only when status ties)
    """

    c_sr = _status_rank(candidate.get("status", ""))
    i_sr = _status_rank(incumbent.get("status", ""))
    if c_sr != i_sr:
        return c_sr > i_sr

    c_wc = _website_conf_rank(candidate.get("website_confidence", ""))
    i_wc = _website_conf_rank(incumbent.get("website_confidence", ""))
    return c_wc > i_wc


def _load_rows(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _write_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    phase1_path = _REPO_ROOT / "Data/exa_harvard/harvard_canonicalized_full.csv"
    phase2_path = _REPO_ROOT / "Data/exa_harvard/harvard_phase2_canonicalized_full.csv"
    out_dir = _REPO_ROOT / "Data/Harvard"

    if not phase1_path.exists():
        raise FileNotFoundError(f"Phase 1 input not found: {phase1_path}")
    if not phase2_path.exists():
        raise FileNotFoundError(f"Phase 2 input not found: {phase2_path}")

    phase1_rows = _load_rows(phase1_path)
    phase2_rows = _load_rows(phase2_path)

    total_in = len(phase1_rows) + len(phase2_rows)

    best_by_norm: dict[str, dict] = {}
    for row in phase1_rows + phase2_rows:
        name = row.get("name", "") or ""
        norm = _normalize_name(name)
        if not norm:
            continue
        if norm not in best_by_norm:
            best_by_norm[norm] = row
        else:
            incumbent = best_by_norm[norm]
            if _is_better(row, incumbent):
                best_by_norm[norm] = row

    merged_rows = list(best_by_norm.values())
    z_total = len(merged_rows)
    d_duplicates_removed = total_in - z_total

    # Preserve existing CSV column ordering.
    if merged_rows:
        fieldnames = list(merged_rows[0].keys())
    else:
        # Fallback (shouldn't happen with real data).
        fieldnames = list(phase1_rows[0].keys()) if phase1_rows else []

    out_full = out_dir / "harvard_canonicalized_full.csv"
    out_canonicalized = out_dir / "harvard_canonicalized.csv"

    _write_rows(out_full, merged_rows, fieldnames=fieldnames)

    filtered = [r for r in merged_rows if (r.get("status", "") or "").strip().lower() != "needs_review"]
    _write_rows(out_canonicalized, filtered, fieldnames=fieldnames)

    print(
        f"Merged: {len(phase1_rows)} from Phase 1 + {len(phase2_rows)} from Phase 2 = {z_total} total "
        f"({d_duplicates_removed} duplicates removed)"
    )


if __name__ == "__main__":
    main()

