#!/usr/bin/env python3
"""
Run search (Exa or Tavily) and filter for each university in universities.json
until credits are exhausted. Supports switching to the other API when one is exhausted.

Data preservation: writes [school]_found.csv (raw, READ-ONLY), [school]_results.json,
[school]_canonicalized.csv, [school]_canonicalized_full.csv, [school]_canonicalized_needs_review.csv,
plus reports/[school]_search_report.md and reports/[school]_filter_report.md.

Usage:
  python -m api_evaluation.run_all_universities --config api_evaluation/universities.json --report reports/final_combined_report.md
"""
import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

EXA_FOUND_CSV = "exa_found.csv"
EXA_RESULTS_JSON = "exa_results.json"
TAVILY_FOUND_CSV = "tavily_found.csv"
TAVILY_RESULTS_JSON = "tavily_results.json"


def count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with open(path, "r", encoding="utf-8") as f:
        return sum(1 for _ in csv.DictReader(f))


def parse_filter_report(report_path: Path) -> dict:
    """Extract total, complete, partial, needs_review, dept_pct, email_pct from filter report."""
    out = {"total": 0, "complete": 0, "partial": 0, "needs_review": 0, "dept_pct": "", "email_pct": ""}
    if not report_path.exists():
        return out
    text = report_path.read_text(encoding="utf-8")
    m = re.search(r"Total rows:\s*\*\*(\d+)\*\*", text)
    if m:
        out["total"] = int(m.group(1))
    m = re.search(r"COMPLETE:\s*\*\*(\d+)\*\*", text)
    if m:
        out["complete"] = int(m.group(1))
    m = re.search(r"PARTIAL:\s*\*\*(\d+)\*\*", text)
    if m:
        out["partial"] = int(m.group(1))
    m = re.search(r"NEEDS_REVIEW:\s*\*\*(\d+)\*\*", text)
    if m:
        out["needs_review"] = int(m.group(1))
    total = out["total"]
    if total:
        m = re.search(r"Dept inferred:\s*\*\*(\d+)\*\*", text)
        if m:
            out["dept_pct"] = f"{int(m.group(1)) / total * 100:.0f}%"
        m = re.search(r"Email present:\s*\*\*(\d+)\*\*", text)
        if m:
            out["email_pct"] = f"{int(m.group(1)) / total * 100:.0f}%"
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Run search + filter for all universities.")
    parser.add_argument(
        "--config",
        default=str(REPO_ROOT / "api_evaluation" / "universities.json"),
        help="Path to universities.json",
    )
    parser.add_argument(
        "--report",
        default=str(REPO_ROOT / "reports" / "final_combined_report.md"),
        help="Path for final combined report",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only check inputs and print plan; do not run search or filter.",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = REPO_ROOT / config_path
    if not config_path.exists():
        print(f"ERROR: Config not found: {config_path}")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        universities = json.load(f)

    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = REPO_ROOT / report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)

    # Resolve paths relative to repo root
    def resolve(p: str) -> Path:
        path = Path(p)
        if not path.is_absolute():
            path = REPO_ROOT / path
        return path

    exa_exhausted = False
    tavily_exhausted = False
    rows = []

    for u in universities:
        name = u["name"]
        school_lower = name.lower()
        input_path = resolve(u["input"])
        config_json = resolve(u["config"])
        output_dir = resolve(u["output_dir"])
        api = u.get("api", "exa")

        if exa_exhausted and api == "exa":
            api = "tavily"
        if tavily_exhausted and api == "tavily":
            api = "exa"

        if not input_path.exists():
            print(f"  SKIP {name}: input not found {input_path}")
            continue
        n_input = count_csv_rows(input_path)
        if n_input == 0:
            print(f"  SKIP {name}: input has 0 rows")
            continue

        if args.dry_run:
            print(f"  WOULD RUN {name}: api={api}, input={input_path} ({n_input} rows), output_dir={output_dir}")
            continue

        # Run search
        if api == "exa":
            search_cmd = [
                sys.executable, "-m", "api_evaluation.exa.run_exa_until_credits",
                "--input", str(input_path),
                "--output", str(output_dir),
                "--single-query", "--use-account-manager",
            ]
            raw_found_csv = output_dir / EXA_FOUND_CSV
            raw_results_json = output_dir / EXA_RESULTS_JSON
        else:
            search_cmd = [
                sys.executable, "-m", "api_evaluation.tavily.run_tavily_primary",
                "--input", str(input_path),
                "--output", str(output_dir),
                "--single-query", "--use-account-manager",
            ]
            raw_found_csv = output_dir / TAVILY_FOUND_CSV
            raw_results_json = output_dir / TAVILY_RESULTS_JSON

        print(f"\n--- {name} ({api}) ---")
        result = subprocess.run(search_cmd, cwd=str(REPO_ROOT))
        if result.returncode == 2:
            if api == "exa":
                exa_exhausted = True
            else:
                tavily_exhausted = True
            print(f"  {api} credits exhausted; remaining universities may use the other API.")
        elif result.returncode != 0:
            print(f"  Search failed with return code {result.returncode}")
            rows.append({
                "university": name,
                "input": n_input,
                "searched": count_csv_rows(raw_found_csv) if raw_found_csv.exists() else 0,
                "complete": 0,
                "partial": 0,
                "needs_review": 0,
                "dept_pct": "—",
                "email_pct": "—",
                "api": api,
                "credits": 0,
            })
            continue

        searched = count_csv_rows(raw_found_csv) if raw_found_csv.exists() else 0
        credits_used = searched  # 1 query per professor in single-query mode

        # Preserve raw outputs as [school]_found.csv and [school]_results.json (READ-ONLY)
        output_dir.mkdir(parents=True, exist_ok=True)
        school_found_csv = output_dir / f"{school_lower}_found.csv"
        school_results_json = output_dir / f"{school_lower}_results.json"
        if raw_found_csv.exists():
            shutil.copy2(raw_found_csv, school_found_csv)
        if raw_results_json.exists():
            shutil.copy2(raw_results_json, school_results_json)

        # Search report
        search_report_path = report_path.parent / f"{school_lower}_search_report.md"
        search_report_path.parent.mkdir(parents=True, exist_ok=True)
        search_report_path.write_text(
            f"# {name} Search Report\n\n"
            f"Generated: {datetime.now().isoformat(timespec='seconds')}\n\n"
            f"- Input rows: **{n_input}**\n"
            f"- Searched: **{searched}**\n"
            f"- API: **{api}**\n"
            f"- Credits used: **{credits_used}**\n",
            encoding="utf-8",
        )

        # Run filter (writes [school]_canonicalized.csv, _full, _needs_review)
        canonicalized_csv = output_dir / f"{school_lower}_canonicalized.csv"
        filter_report_path = report_path.parent / f"{school_lower}_filter_report.md"
        filter_cmd = [
            sys.executable, "-m", "api_evaluation.filter.filter_results",
            "--input", str(school_found_csv),
            "--config", str(config_json),
            "--output", str(canonicalized_csv),
            "--report", str(filter_report_path),
        ]
        subprocess.run(filter_cmd, cwd=str(REPO_ROOT))
        stats = parse_filter_report(filter_report_path)

        rows.append({
            "university": name,
            "input": n_input,
            "searched": searched,
            "complete": stats["complete"],
            "partial": stats["partial"],
            "needs_review": stats["needs_review"],
            "dept_pct": stats.get("dept_pct") or "—",
            "email_pct": stats.get("email_pct") or "—",
            "api": api,
            "credits": credits_used,
        })
        print(f"  Searched: {searched} | Complete: {stats['complete']} | Partial: {stats['partial']} | Needs Review: {stats['needs_review']}")

    if args.dry_run:
        print("\nDry-run done. No searches or filters executed.")
        return

    # Write combined report (Phase E format)
    total_input = sum(r["input"] for r in rows)
    total_searched = sum(r["searched"] for r in rows)
    total_complete = sum(r["complete"] for r in rows)
    total_partial = sum(r["partial"] for r in rows)
    total_needs_review = sum(r["needs_review"] for r in rows)
    total_credits = sum(r["credits"] for r in rows)

    lines = [
        "# Faculty Pipeline — Combined Report",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Summary Table",
        "",
        "| University | Input | Searched | Complete | Partial | Review | Dept% | Email% | API | Credits |",
        "|-------------|-------|----------|----------|---------|--------|-------|--------|-----|---------|",
    ]
    for r in rows:
        lines.append(
            f"| {r['university']} | {r['input']} | {r['searched']} | {r['complete']} | {r['partial']} | {r['needs_review']} | {r['dept_pct']} | {r['email_pct']} | {r['api']} | {r['credits']} |"
        )
    lines.append(f"| **TOTAL** | **{total_input}** | **{total_searched}** | **{total_complete}** | **{total_partial}** | **{total_needs_review}** | | | | **{total_credits}** |")
    lines.append("")
    lines.append("## Credit Usage")
    lines.append("(Per-account breakdown available in api_evaluation/state/ for Exa and Tavily.)")
    lines.append("")
    lines.append("## Per-University Details")
    for r in rows:
        sl = r["university"].lower()
        lines.append(f"- [{r['university']}]({sl}_filter_report.md) — filter report")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nCombined report written to {report_path}")


if __name__ == "__main__":
    main()
