"""
Filter faculty to MVP set: those with email OR website (1,500 for ship).
Output: output/harvard_mvp_1500.json
"""
import json
import os
from datetime import datetime

# Paths relative to faculty_pipeline (parent of scripts/)
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
input_file = os.path.join(base, "output", "harvard_university_20260131_041256_v533.json")
output_file = os.path.join(base, "output", "harvard_mvp_1500.json")

with open(input_file) as f:
    data = json.load(f)

faculty = data["faculty"]

usable = [f for f in faculty if f.get("primary_email") or f.get("website")]

usable.sort(key=lambda x: x.get("h_index", 0), reverse=True)

output = {
    "metadata": {
        "source": "Harvard University",
        "version": "5.3.3-mvp",
        "generated": datetime.now().isoformat(),
        "total_faculty": len(usable),
        "with_email": sum(1 for f in usable if f.get("primary_email")),
        "with_website": sum(1 for f in usable if f.get("website")),
        "with_both": sum(1 for f in usable if f.get("primary_email") and f.get("website")),
        "verified_emails": sum(1 for f in usable if f.get("primary_email_quality") == "verified"),
    },
    "faculty": usable
}

with open(output_file, "w") as f:
    json.dump(output, f, indent=2)

print(f"Exported {len(usable)} faculty to {output_file}")
print(f"  With email: {output['metadata']['with_email']}")
print(f"  With website: {output['metadata']['with_website']}")
print(f"  With both: {output['metadata']['with_both']}")
print(f"  Verified emails: {output['metadata']['verified_emails']}")
