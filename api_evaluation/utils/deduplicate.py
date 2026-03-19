import argparse
import csv
import unicodedata
from typing import Dict, List, Set


SUFFIXES = {"jr", "sr", "md", "phd", "ii", "iii", "iv"}


def _normalize_name(name: str) -> str:
    """
    Normalize professor names for deduplication:
      - lowercase
      - strip accents
      - remove periods/commas
      - drop suffixes (Jr, Sr, MD, PhD, II, III, IV)
    """
    if not name:
        return ""
    # Normalize accents and lowercase
    norm = unicodedata.normalize("NFKD", name)
    norm = norm.encode("ascii", "ignore").decode().lower()
    # Remove punctuation
    for ch in ".,":  # keep hyphens to preserve last names
        norm = norm.replace(ch, " ")
    tokens = [t for t in norm.split() if t]
    filtered = [t for t in tokens if t not in SUFFIXES]
    return " ".join(filtered)


def _load_names_from_csv(path: str) -> Set[str]:
    names: Set[str] = set()
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("name", "") or row.get("Name", "") or ""
            norm = _normalize_name(name)
            if norm:
                names.add(norm)
    return names


def find_new_professors(new_csv: str, existing_csv: str) -> List[Dict]:
    """
    Load new_csv and existing_csv.
    Return rows from new_csv whose normalized 'name' does not appear in existing_csv.
    """
    existing_names = _load_names_from_csv(existing_csv)
    new_rows: List[Dict] = []
    with open(new_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            norm = _normalize_name(row.get("name", "") or row.get("Name", "") or "")
            if not norm:
                continue
            if norm not in existing_names:
                new_rows.append(row)
    return new_rows


def _write_rows(path: str, rows: List[Dict]) -> None:
    if not rows:
        # nothing to write, but create empty file with header inferred from new_csv would need context.
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="Find new professors not already present in existing CSV.")
    parser.add_argument("--new", required=True, help="New faculty CSV (e.g. faculty_pipeline/output/harvard_affiliated_faculty.csv)")
    parser.add_argument("--existing", required=True, help="Existing Exa results CSV (e.g. Data/exa_harvard/exa_harvard_found.csv)")
    parser.add_argument("--output", required=True, help="Output CSV for remaining professors.")
    args = parser.parse_args()

    remaining = find_new_professors(args.new, args.existing)
    _write_rows(args.output, remaining)
    print(f"Wrote {len(remaining)} remaining professors to {args.output}")


if __name__ == "__main__":
    main()

