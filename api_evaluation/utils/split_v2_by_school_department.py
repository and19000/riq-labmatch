import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
V2_PATH = REPO_ROOT / "Data" / "v2" / "all_faculty.json"
DATA_DIR = REPO_ROOT / "Data"


def _slug(value: str) -> str:
    value = (value or "").strip()
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return value or "Unknown"


def _normalize_school_name(school: str) -> str:
    school = (school or "").strip()
    if school == "Massachusetts Institute of Technology":
        return "MIT"
    return school


def main() -> None:
    if not V2_PATH.exists():
        raise FileNotFoundError(f"Missing source file: {V2_PATH}")

    records = json.loads(V2_PATH.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("Expected Data/v2/all_faculty.json to be a JSON list")

    grouped = defaultdict(lambda: defaultdict(list))
    for rec in records:
        if not isinstance(rec, dict):
            continue
        aff = rec.get("affiliation") or {}
        school = _normalize_school_name((aff.get("school") or "").strip())
        department = (aff.get("department") or "").strip() or "Unknown Department"
        if not school:
            school = "Unknown School"
        grouped[school][department].append(rec)

    for school, dept_map in grouped.items():
        school_dir = DATA_DIR / school
        school_dir.mkdir(parents=True, exist_ok=True)
        for dept, recs in dept_map.items():
            filename = f"{_slug(dept)}.json"
            out_path = school_dir / filename
            out_path.write_text(json.dumps(recs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    total_dept_files = sum(len(d) for d in grouped.values())
    print(f"Split {len(records)} faculty records")
    print(f"Created/updated {total_dept_files} department JSON files across {len(grouped)} schools")


if __name__ == "__main__":
    main()

