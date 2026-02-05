"""
Faculty data update script.
Run periodically (e.g., monthly) to refresh data with backup.

Usage:
  python scripts/update_faculty_data.py [new_data.json]
  If no path given, uses output/nsf_all_faculty.json as source and overwrites
  the app's current faculty file (with backup).

Run from faculty_pipeline/:  python scripts/update_faculty_data.py output/nsf_all_faculty.json
"""
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Paths relative to faculty_pipeline (parent of scripts/)
BASE = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE / "output"
DEFAULT_SOURCE = OUTPUT_DIR / "nsf_all_faculty.json"
DEFAULT_TARGET = OUTPUT_DIR / "nsf_all_faculty.json"


def update_faculty_data(source_path: Path, target_path: Path) -> None:
    """Update faculty data with backup."""
    if not source_path.exists():
        print(f"ERROR: Source not found: {source_path}")
        sys.exit(1)

    # Backup current target if it exists
    if target_path.exists():
        backup_path = target_path.with_suffix(
            f".backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        )
        shutil.copy(target_path, backup_path)
        print(f"Backed up to: {backup_path}")

    with open(source_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    faculty = data.get("faculty", data) if isinstance(data, dict) else data
    if not isinstance(faculty, list):
        print("ERROR: Expected list of faculty or {metadata, faculty}.")
        sys.exit(1)

    required = ["name"]
    valid = sum(1 for f in faculty if isinstance(f, dict) and f.get("name"))
    if valid < len(faculty) * 0.5:
        print(f"WARNING: Only {valid}/{len(faculty)} have 'name'. Continue? [y/N]")
        if input().strip().lower() != "y":
            print("Aborted.")
            sys.exit(0)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Updated: {target_path}")
    print(f"Total faculty: {len(faculty)}")
    print("Restart the app (or wait for cache TTL) to load new data.")


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        source = Path(sys.argv[1]).expanduser().resolve()
    else:
        source = DEFAULT_SOURCE
    target = DEFAULT_TARGET
    update_faculty_data(source, target)
