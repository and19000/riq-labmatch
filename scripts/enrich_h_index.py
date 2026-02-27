#!/usr/bin/env python3
"""Batch H-index enrichment using Google Scholar via the scholarly library.

Loads the v2 combined faculty JSON and updates h_index, citations, and i10_index
from Google Scholar. Includes checkpointing for resume after interruption.

Usage:
    python scripts/enrich_h_index.py
    python scripts/enrich_h_index.py --limit 50    # Process only 50 PIs
    python scripts/enrich_h_index.py --resume       # Resume from checkpoint
"""

import argparse
import json
import os
import sys
import time
from datetime import date

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V2_PATH = os.path.join(BASE_DIR, "Data", "v2", "all_faculty.json")
CHECKPOINT_PATH = os.path.join(BASE_DIR, "scripts", ".scholarly_checkpoint.json")

DELAY_BETWEEN_QUERIES = 3  # seconds
CHECKPOINT_INTERVAL = 10   # save every N PIs


def load_checkpoint():
    """Load checkpoint of already-processed PI IDs."""
    if os.path.exists(CHECKPOINT_PATH):
        with open(CHECKPOINT_PATH, "r") as f:
            return json.load(f)
    return {"processed_ids": [], "updated_count": 0, "not_found_count": 0}


def save_checkpoint(checkpoint):
    """Save checkpoint."""
    with open(CHECKPOINT_PATH, "w") as f:
        json.dump(checkpoint, f)


def search_scholar(name, school):
    """Search Google Scholar for a researcher and return metrics."""
    from scholarly import scholarly

    try:
        query = f"{name} {school}"
        search = scholarly.search_author(query)
        author = next(search, None)
        if not author:
            return None

        # Fill in the author details (gets h-index, etc.)
        author_filled = scholarly.fill(author, sections=["basics", "indices"])

        # Verify the match by checking affiliation
        affiliation = (author_filled.get("affiliation") or "").lower()
        school_lower = school.lower()

        # Check if school name or key words match affiliation
        school_words = school_lower.replace("university", "").strip().split()
        match = any(w in affiliation for w in school_words if len(w) > 2)
        if not match and school_lower not in affiliation:
            return None

        h_index = author_filled.get("hindex")
        if h_index is None:
            return None

        return {
            "h_index": int(h_index),
            "citations_total": author_filled.get("citedby"),
            "i10_index": author_filled.get("i10index"),
            "google_scholar_id": author_filled.get("scholar_id", ""),
            "h_index_source": "google_scholar",
            "h_index_updated": date.today().isoformat(),
        }
    except StopIteration:
        return None
    except Exception as e:
        print(f"  Error for {name}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Enrich H-indices from Google Scholar")
    parser.add_argument("--limit", type=int, default=0, help="Max PIs to process (0=all)")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--dry-run", action="store_true", help="Don't write changes")
    args = parser.parse_args()

    # Load v2 data
    print(f"Loading faculty data from {V2_PATH}...")
    with open(V2_PATH, "r", encoding="utf-8") as f:
        faculty = json.load(f)
    print(f"  Loaded {len(faculty)} PIs")

    # Load checkpoint
    checkpoint = load_checkpoint() if args.resume else {"processed_ids": [], "updated_count": 0, "not_found_count": 0}
    processed_set = set(checkpoint["processed_ids"])

    # Filter to PIs that need enrichment
    to_process = []
    for pi in faculty:
        pi_id = pi.get("id", "")
        if pi_id in processed_set:
            continue
        to_process.append(pi)

    if args.limit > 0:
        to_process = to_process[:args.limit]

    total = len(to_process)
    print(f"  PIs to process: {total}")
    if args.resume:
        print(f"  Already processed: {len(processed_set)}")
        print(f"  Previously updated: {checkpoint['updated_count']}")

    # Build index for fast lookup
    id_to_idx = {pi.get("id", ""): i for i, pi in enumerate(faculty)}

    updated = checkpoint["updated_count"]
    not_found = checkpoint["not_found_count"]
    errors = 0

    for i, pi in enumerate(to_process):
        pi_id = pi.get("id", "")
        name = pi.get("name", "")
        school = pi.get("affiliation", {}).get("school", "")

        if not name or not school:
            continue

        progress = f"[{i+1}/{total}]"
        print(f"{progress} Searching: {name} ({school})...", end=" ", flush=True)

        result = search_scholar(name, school)

        if result:
            # Update the faculty entry in-place
            idx = id_to_idx.get(pi_id)
            if idx is not None:
                metrics = faculty[idx].get("metrics", {})
                metrics["h_index"] = result["h_index"]
                metrics["h_index_source"] = "google_scholar"
                metrics["h_index_updated"] = result["h_index_updated"]
                if result.get("citations_total"):
                    metrics["citations_total"] = result["citations_total"]
                if result.get("i10_index"):
                    metrics["i10_index"] = result["i10_index"]
                faculty[idx]["metrics"] = metrics

                # Update Google Scholar ID if found
                if result.get("google_scholar_id"):
                    contact = faculty[idx].get("contact", {})
                    contact["google_scholar_id"] = result["google_scholar_id"]
                    contact["google_scholar_url"] = f"https://scholar.google.com/citations?user={result['google_scholar_id']}"
                    faculty[idx]["contact"] = contact

                updated += 1
                print(f"h={result['h_index']}, citations={result.get('citations_total', '?')}")
            else:
                print("ID not found in index")
                errors += 1
        else:
            not_found += 1
            print("not found")

        # Track processed
        checkpoint["processed_ids"].append(pi_id)
        checkpoint["updated_count"] = updated
        checkpoint["not_found_count"] = not_found

        # Checkpoint every N PIs
        if (i + 1) % CHECKPOINT_INTERVAL == 0:
            save_checkpoint(checkpoint)
            print(f"  [Checkpoint saved: {updated} updated, {not_found} not found]")

        # Rate limiting
        time.sleep(DELAY_BETWEEN_QUERIES)

    # Final save
    save_checkpoint(checkpoint)

    if not args.dry_run:
        print(f"\nWriting updated data to {V2_PATH}...")
        with open(V2_PATH, "w", encoding="utf-8") as f:
            json.dump(faculty, f, indent=2, ensure_ascii=False)
        print("Done!")
    else:
        print("\n[DRY RUN - no files written]")

    print(f"\nSummary:")
    print(f"  Processed: {len(to_process)}")
    print(f"  Updated with Scholar data: {updated}")
    print(f"  Not found on Scholar: {not_found}")
    print(f"  Errors: {errors}")


if __name__ == "__main__":
    main()
