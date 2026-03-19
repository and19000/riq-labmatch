"""
Merge scraped directory names with existing JSON-converted CSVs.

Usage:
  python3 -m api_evaluation.utils.merge_inputs \\
    --json-csv api_evaluation/inputs/mit_faculty.csv \\
    --scraped-csv api_evaluation/inputs/mit_scraped.csv \\
    --output api_evaluation/inputs/mit_faculty.csv

- Reads both CSVs
- Deduplicates by normalized name (lowercase, strip accents, remove periods/commas, strip suffixes)
- Prefers the JSON version if duplicate (it may have more fields)
- Writes merged result to --output
- Prints: "MIT: 600 from JSON + X from scrape = Y total (Z new from scrape)"
"""
import argparse
import csv
import sys
from pathlib import Path

# Allow running as python -m api_evaluation.utils.merge_inputs from repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from api_evaluation.utils.deduplicate import _normalize_name

FIELDS = ["name", "affiliation", "department", "gold_email", "gold_website"]


def load_rows(path: Path) -> list:
    if not path.exists():
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            r = {k: row.get(k, "").strip() for k in FIELDS}
            rows.append(r)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge JSON faculty CSV with scraped CSV.")
    parser.add_argument("--json-csv", required=True, help="Existing JSON-converted faculty CSV")
    parser.add_argument("--scraped-csv", required=True, help="Scraped directory CSV")
    parser.add_argument("--output", required=True, help="Output merged CSV path")
    parser.add_argument("--label", default=None, help="Label for print (e.g. MIT); inferred from output filename if omitted")
    args = parser.parse_args()

    json_path = Path(args.json_csv)
    if not json_path.is_absolute():
        json_path = _REPO_ROOT / json_path
    scraped_path = Path(args.scraped_csv)
    if not scraped_path.is_absolute():
        scraped_path = _REPO_ROOT / scraped_path
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = _REPO_ROOT / output_path

    label = args.label
    if not label:
        # e.g. mit_faculty.csv -> MIT
        stem = output_path.stem.lower()
        if "mit" in stem:
            label = "MIT"
        elif "tufts" in stem:
            label = "Tufts"
        elif "bu" in stem or "boston" in stem:
            label = "BU"
        elif "northeastern" in stem:
            label = "Northeastern"
        else:
            label = output_path.stem.replace("_", " ").title()

    json_rows = load_rows(json_path)
    scraped_rows = load_rows(scraped_path)

    by_norm = {}
    for r in json_rows:
        n = _normalize_name(r.get("name", ""))
        if n:
            by_norm[n] = r  # JSON wins

    new_from_scrape = 0
    for r in scraped_rows:
        n = _normalize_name(r.get("name", ""))
        if not n:
            continue
        if n not in by_norm:
            by_norm[n] = r
            new_from_scrape += 1

    merged = list(by_norm.values())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(merged)

    from_json = len(json_rows)
    total = len(merged)
    print(f"{label}: {from_json} from JSON + {new_from_scrape} new from scrape = {total} total")


if __name__ == "__main__":
    main()
