import csv
import sys
from pathlib import Path

from api_evaluation.utils.deduplicate import _normalize_name


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


UNIVERSITIES = [
    ("Harvard University", "Data/Harvard/harvard_canonicalized.csv", "Harvard"),
    ("Massachusetts Institute of Technology", "Data/MIT/mit_canonicalized.csv", "MIT"),
    ("Northeastern University", "Data/Northeastern/northeastern_canonicalized.csv", "Northeastern"),
    ("Tufts University", "Data/Tufts/tufts_canonicalized.csv", "Tufts"),
    ("Boston University", "Data/BU/bu_canonicalized.csv", "Boston University"),
    ("Stanford University", "Data/Stanford/stanford_canonicalized.csv", "Stanford"),
    ("Yale University", "Data/Yale/yale_canonicalized.csv", "Yale"),
    ("Princeton University", "Data/Princeton/princeton_canonicalized.csv", "Princeton"),
]


OUTPUT_COLUMNS = [
    "name",
    "university",
    "affiliation",
    "department",
    "canonical_website",
    "website_confidence",
    "canonical_email",
    "email_confidence",
    "phone",
    "status",
]


def _load_canonicalized_rows(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _as_int_status(s: str) -> str:
    return (s or "").strip().lower()


def main() -> None:
    seen: dict[tuple[str, str], dict] = {}  # (university, normalized_name) -> row

    for university_full, rel_path, _label in UNIVERSITIES:
        csv_path = _REPO_ROOT / rel_path
        if not csv_path.exists():
            raise FileNotFoundError(f"Missing canonicalized input: {csv_path}")

        rows = _load_canonicalized_rows(csv_path)
        for row in rows:
            name = (row.get("name", "") or "").strip()
            norm_name = _normalize_name(name)
            key = (university_full, norm_name or name.strip().lower())
            if key not in seen:
                seen[key] = row

    # Build output rows in required column order.
    out_rows: list[dict] = []
    for (university_full, _norm), row in seen.items():
        out_rows.append(
            {
                "name": row.get("name", ""),
                "university": university_full,
                "affiliation": row.get("affiliation", ""),
                "department": row.get("department", ""),
                "canonical_website": row.get("canonical_website", ""),
                "website_confidence": row.get("website_confidence", ""),
                "canonical_email": row.get("canonical_email", ""),
                "email_confidence": row.get("email_confidence", ""),
                "phone": row.get("phone", ""),
                "status": row.get("status", ""),
            }
        )

    # Sort by: university alphabetically, then name alphabetically.
    out_rows.sort(key=lambda r: (r["university"].lower(), (r.get("name", "") or "").lower()))

    out_path = _REPO_ROOT / "Data/master_faculty_database.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(out_rows)

    # Summary
    total = len(out_rows)
    print(f"Master database: {total} total professors")

    # Build breakdown by the short school label requested.
    label_by_university = {full: label for full, _path, label in UNIVERSITIES}
    totals_by_label = {label: {"total": 0, "complete": 0, "partial": 0} for _u, _p, label in UNIVERSITIES}

    for r in out_rows:
        label = label_by_university.get(r["university"], r["university"])
        st = _as_int_status(r.get("status", ""))
        totals_by_label[label]["total"] += 1
        if st == "complete":
            totals_by_label[label]["complete"] += 1
        elif st == "partial":
            totals_by_label[label]["partial"] += 1

    for label in [label for _u, _p, label in UNIVERSITIES]:
        t = totals_by_label[label]["total"]
        c = totals_by_label[label]["complete"]
        p = totals_by_label[label]["partial"]
        print(f"  {label}: {t} ({c} complete, {p} partial)")


if __name__ == "__main__":
    main()

