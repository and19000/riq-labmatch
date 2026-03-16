#!/usr/bin/env python3
"""
Run the same Exa pipeline as the 80-professor test, scaled until credits exhausted or MAX_PROFESSORS.

Uses the exact same logic as evaluate.py (ExaSearch.search_professor, extract_emails_from_results,
check_website_match, check_email_match, ProfessorResult). Outputs match the 80-test run.

Usage:
  python run_exa_until_credits.py --input gold_standard.csv --output results_exa_until_credits
  python run_exa_until_credits.py --input gold_standard.csv --output results_exa_until_credits --max-professors 500
  python run_exa_until_credits.py --dry-run --input gold_standard.csv --output results_exa_until_credits

Resume: re-run the same command; checkpoint in OUTPUT_DIR/checkpoint.json is used automatically.
"""
import argparse
import csv
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

# Reuse exact 80-test pipeline components
from config import EXA_API_KEY, REQUEST_DELAY
from evaluate import (
    ProfessorResult,
    check_email_match,
    check_website_match,
    load_gold_standard,
)
from extract_email import extract_emails_from_results
from search_apis import ExaSearch

SCRIPT_DIR = Path(__file__).resolve().parent
CHECKPOINT_FILENAME = "checkpoint.json"
FAILURES_FILENAME = "failures.csv"
EXA_RESULTS_FILENAME = "exa_results.json"
EXA_FOUND_CSV_FILENAME = "exa_found.csv"
RUN_LOG_FILENAME = "run.log"

# Exa quota/credit error patterns (stop run)
QUOTA_ERROR_PATTERNS = (
    "quota",
    "credit",
    "exhausted",
    "limit exceeded",
    "payment required",
    "insufficient",
    "429",
    "402",
)


def log(msg: str, log_path: Path) -> None:
    line = f"[{datetime.now().isoformat()}] {msg}"
    print(line)
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def is_quota_error(e: Exception) -> bool:
    text = (str(e) or "").lower()
    return any(p in text for p in QUOTA_ERROR_PATTERNS)


def load_checkpoint(output_dir: Path) -> tuple[int, list, list]:
    """Returns (last_processed_index, processed_indices, existing_results as ProfessorResult list)."""
    checkpoint_path = output_dir / CHECKPOINT_FILENAME
    if not checkpoint_path.exists():
        return 0, [], []

    try:
        with open(checkpoint_path, encoding="utf-8") as f:
            data = json.load(f)
        start_index = int(data.get("last_processed_index", 0))
        processed = list(data.get("processed_indices", []))
    except (json.JSONDecodeError, OSError):
        return 0, [], []

    existing = []
    json_path = output_dir / EXA_RESULTS_FILENAME
    if json_path.exists() and start_index > 0:
        try:
            with open(json_path, encoding="utf-8") as f:
                payload = json.load(f)
            for r in payload.get("results", []):
                existing.append(ProfessorResult(**r))
        except (json.JSONDecodeError, OSError, TypeError):
            pass
    return start_index, processed, existing


def save_checkpoint(output_dir: Path, last_index: int, processed_indices: list) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / CHECKPOINT_FILENAME
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "last_processed_index": last_index,
                "processed_indices": processed_indices,
                "updated_at": datetime.now().isoformat(),
            },
            f,
            indent=2,
        )


def append_failure(output_dir: Path, index: int, name: str, error: str, log_path: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / FAILURES_FILENAME
    write_header = not path.exists()
    with open(path, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["index", "name", "error"])
        w.writerow([index, name, error])


def save_exa_results(
    output_dir: Path,
    results: list,
    stats: dict,
    log_path: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    total = len(results)
    metrics = {
        "total_professors": total,
        "website": {
            "exact_match": sum(1 for r in results if r.website_exact_match),
            "domain_match": sum(1 for r in results if r.website_domain_match),
            "name_in_url": sum(1 for r in results if r.website_name_in_url),
            "found_any": sum(1 for r in results if r.found_website),
        },
        "email": {
            "exact_match": sum(1 for r in results if r.email_exact_match),
            "domain_match": sum(1 for r in results if r.email_domain_match),
            "found_any": sum(1 for r in results if r.found_email),
        },
        "avg_website_score": round(sum(r.website_score() for r in results) / total, 3) if total else 0,
        "avg_email_score": round(sum(r.email_score() for r in results) / total, 3) if total else 0,
    }
    for key in ("website", "email"):
        m = metrics[key]
        m["exact_rate"] = round(m["exact_match"] / total * 100, 1) if total else 0
        m["domain_rate"] = round(m["domain_match"] / total * 100, 1) if total else 0
        m["found_rate"] = round(m["found_any"] / total * 100, 1) if total else 0
    metrics["combined_score"] = round(
        (metrics["avg_website_score"] + metrics["avg_email_score"]) / 2, 3
    )

    payload = {
        "api": "Exa",
        "timestamp": datetime.now().isoformat(),
        "stats": stats,
        "metrics": metrics,
        "results": [asdict(r) for r in results],
    }
    json_path = output_dir / EXA_RESULTS_FILENAME
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    log(f"Saved {total} results to {json_path}", log_path)

    csv_path = output_dir / EXA_FOUND_CSV_FILENAME
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "name", "affiliation", "department", "gold_email", "gold_website",
            "found_website", "found_email", "all_urls", "all_emails",
        ])
        for r in results:
            w.writerow([
                r.name, r.affiliation, r.department,
                r.gold_email, r.gold_website,
                r.found_website, r.found_email,
                "; ".join(r.all_urls),
                "; ".join(r.all_emails),
            ])
    log(f"Saved {csv_path}", log_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Exa pipeline until credits exhausted or cap reached (same as 80-test)."
    )
    parser.add_argument(
        "--input",
        default=os.environ.get("INPUT_PATH", str(SCRIPT_DIR / "gold_standard_affiliation_only.csv")),
        help="Input CSV (name, affiliation, department, gold_email, gold_website). Default: INPUT_PATH or gold_standard_affiliation_only.csv",
    )
    parser.add_argument(
        "--output",
        default=os.environ.get("OUTPUT_DIR", str(SCRIPT_DIR / "results_exa_until_credits")),
        help="Output directory. Default: OUTPUT_DIR or results_exa_until_credits",
    )
    parser.add_argument(
        "--max-professors",
        type=int,
        default=int(os.environ.get("MAX_PROFESSORS", "10000")),
        help="Stop after this many professors. Default: MAX_PROFESSORS or 10000",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process 2 professors without calling Exa (mock results); validate IO and schema.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / RUN_LOG_FILENAME

    if not input_path.exists():
        log(f"ERROR: Input file not found: {input_path}", log_path)
        sys.exit(1)

    professors = load_gold_standard(str(input_path))
    log(f"Loaded {len(professors)} professors from {input_path}", log_path)

    if args.dry_run:
        start_index, processed_indices, results = 0, [], []
        log("Dry-run: processing 2 professors with mock Exa (no API calls)", log_path)
    else:
        start_index, processed_indices, results = load_checkpoint(output_dir)
        if start_index > 0 or processed_indices:
            log(f"Resuming from index {start_index} ({len(processed_indices)} already processed, {len(results)} in results)", log_path)
        if not results:
            results = []
    api = None
    if not args.dry_run:
        if not EXA_API_KEY:
            log("ERROR: EXA_API_KEY not set", log_path)
            sys.exit(1)
        api = ExaSearch(EXA_API_KEY, delay=REQUEST_DELAY)

    dry_run_cap = 2 if args.dry_run else None
    max_index = min(
        len(professors),
        start_index + args.max_professors,
        start_index + (dry_run_cap if dry_run_cap else len(professors)),
    )
    stop_reason = None

    try:
        stop_reason = _run_loop(
            args=args,
            professors=professors,
            start_index=start_index,
            max_index=max_index,
            results=results,
            processed_indices=processed_indices,
            api=api,
            output_dir=output_dir,
            log_path=log_path,
        )
    except KeyboardInterrupt:
        log("Keyboard interrupt - saving progress and exiting.", log_path)
        if results:
            next_index = processed_indices[-1] + 1 if processed_indices else start_index
            if not args.dry_run:
                save_checkpoint(output_dir, next_index, processed_indices)
            save_exa_results(
                output_dir,
                results,
                api.get_stats() if api else {"api": "Exa", "queries": 0, "estimated_cost": 0},
                log_path,
            )
            log(f"Saved {len(results)} results. Re-run the same command to resume from index {next_index}.", log_path)
        sys.exit(0)

    if not stop_reason and (start_index + len(results)) >= len(professors):
        stop_reason = "all_processed"
    elif not stop_reason and (start_index + len(results)) >= args.max_professors:
        stop_reason = "max_professors_reached"

    if args.dry_run and results:
        save_exa_results(
            output_dir,
            results,
            {"api": "Exa", "queries": 0, "estimated_cost": 0},
            log_path,
        )

    log(f"Done. Processed {len(results)} professors this run; total in results: {len(results)}", log_path)
    if stop_reason:
        log(f"Stop reason: {stop_reason}", log_path)
    if api:
        log(f"Exa stats: {api.get_stats()}", log_path)


def _run_loop(
    args,
    professors,
    start_index,
    max_index,
    results,
    processed_indices,
    api,
    output_dir,
    log_path,
):
    """Main processing loop (extracted so KeyboardInterrupt can be caught). Returns stop_reason or None."""
    stop_reason = None
    for i in range(start_index, max_index):
        prof = professors[i]
        name = prof.get("name", "")
        affiliation = prof.get("affiliation", "")
        department = prof.get("department", "")
        gold_email = prof.get("gold_email", "")
        gold_website = prof.get("gold_website", "")

        log(f"[{i+1}/{len(professors)}] {name} ({affiliation})", log_path)

        if args.dry_run:
            results.append(ProfessorResult(
                name=name,
                affiliation=affiliation,
                department=department,
                gold_email=gold_email,
                gold_website=gold_website,
                found_website="https://dry-run.example.edu/profile",
                found_email="dryrun@example.edu",
                all_urls=["https://dry-run.example.edu/profile"],
                all_emails=["dryrun@example.edu"],
                website_exact_match=False,
                website_domain_match=False,
                website_name_in_url=True,
                email_exact_match=False,
                email_domain_match=False,
                queries_used=0,
            ))
            continue

        try:
            search_results = api.search_professor(
                name=name,
                affiliation=affiliation,
                department=department,
            )
        except Exception as e:
            append_failure(output_dir, i, name, str(e), log_path)
            log(f"  Exa error: {e}", log_path)
            if is_quota_error(e):
                stop_reason = "credits_exhausted"
                log("Stopping: quota/credits error from Exa", log_path)
                break
            continue

        all_urls = [r.url for r in search_results if r.url]
        found_website = all_urls[0] if all_urls else ""
        all_emails = extract_emails_from_results(search_results, name)
        found_email = all_emails[0] if all_emails else ""

        website_match = check_website_match(found_website, gold_website, name)
        email_match = check_email_match(found_email, gold_email)

        result = ProfessorResult(
            name=name,
            affiliation=affiliation,
            department=department,
            gold_email=gold_email,
            gold_website=gold_website,
            found_website=found_website,
            found_email=found_email,
            all_urls=all_urls[:5],
            all_emails=all_emails[:3],
            website_exact_match=website_match["exact_match"],
            website_domain_match=website_match["domain_match"],
            website_name_in_url=website_match["name_in_url"],
            email_exact_match=email_match["exact_match"],
            email_domain_match=email_match["domain_match"],
            queries_used=api.query_count,
        )
        results.append(result)
        processed_indices.append(i)

        status = []
        if result.website_exact_match:
            status.append("Website EXACT")
        elif result.website_domain_match:
            status.append("Website domain")
        elif result.found_website:
            status.append("Website found")
        else:
            status.append("No website")
        if result.email_exact_match:
            status.append("Email EXACT")
        elif result.email_domain_match:
            status.append("Email domain")
        elif result.found_email:
            status.append("Email found")
        else:
            status.append("No email")
        log("  " + " | ".join(status), log_path)

        if not args.dry_run:
            save_checkpoint(output_dir, i + 1, processed_indices)
        save_exa_results(
            output_dir,
            results,
            api.get_stats() if api else {"api": "Exa", "queries": 0, "estimated_cost": 0},
            log_path,
        )
    return stop_reason


if __name__ == "__main__":
    main()
