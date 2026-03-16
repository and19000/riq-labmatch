"""
Main evaluation script.
Compares Exa, Tavily, and Brave search APIs against gold standard.

Usage:
  python evaluate.py --input gold_standard.csv --output results/
"""
import os
import json
import csv
import argparse
from datetime import datetime
from typing import Dict, List
from urllib.parse import urlparse
from dataclasses import dataclass, asdict

from config import (
    EXA_API_KEY,
    TAVILY_API_KEY,
    BRAVE_API_KEY,
    GOLD_STANDARD_FILE,
    RESULTS_DIR,
    REQUEST_DELAY,
)
from search_apis import ExaSearch, TavilySearch, BraveSearch
from extract_email import extract_emails_from_results


@dataclass
class ProfessorResult:
    name: str
    affiliation: str
    department: str
    gold_email: str
    gold_website: str
    found_website: str
    found_email: str
    all_urls: List[str]
    all_emails: List[str]
    website_exact_match: bool
    website_domain_match: bool
    website_name_in_url: bool
    email_exact_match: bool
    email_domain_match: bool
    queries_used: int

    def website_score(self) -> float:
        if self.website_exact_match:
            return 1.0
        if self.website_domain_match:
            return 0.7
        if self.website_name_in_url:
            return 0.5
        if self.found_website:
            return 0.2
        return 0.0

    def email_score(self) -> float:
        if self.email_exact_match:
            return 1.0
        if self.email_domain_match:
            return 0.5
        if self.found_email:
            return 0.2
        return 0.0


def load_gold_standard(filepath: str) -> List[Dict]:
    professors = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            prof = {
                "name": row.get("name", row.get("Name", row.get("professor_name", ""))).strip(),
                "affiliation": row.get("affiliation", row.get("Affiliation", row.get("institution", ""))).strip(),
                "department": row.get("department", row.get("Department", "")).strip(),
                "gold_email": row.get("gold_email", row.get("email", row.get("Email", ""))).strip().lower(),
                "gold_website": row.get("gold_website", row.get("website", row.get("Website", ""))).strip().lower(),
            }
            if prof["name"] and prof["affiliation"]:
                professors.append(prof)
    return professors


def normalize_url(url: str) -> str:
    if not url:
        return ""
    url = url.lower().strip()
    url = url.replace("https://", "").replace("http://", "")
    url = url.replace("www.", "")
    return url.rstrip("/")


def check_website_match(found_url: str, gold_url: str, professor_name: str) -> Dict:
    found_norm = normalize_url(found_url)
    gold_norm = normalize_url(gold_url)
    result = {"exact_match": False, "domain_match": False, "name_in_url": False}
    if not found_norm or not gold_norm:
        return result
    if found_norm == gold_norm:
        result["exact_match"] = result["domain_match"] = result["name_in_url"] = True
        return result
    found_domain = urlparse("http://" + found_norm).netloc
    gold_domain = urlparse("http://" + gold_norm).netloc
    if found_domain == gold_domain:
        result["domain_match"] = True
    name_parts = professor_name.lower().split()
    last_name = name_parts[-1] if name_parts else ""
    if last_name and last_name in found_norm:
        result["name_in_url"] = True
    return result


def check_email_match(found_email: str, gold_email: str) -> Dict:
    found = (found_email or "").lower().strip()
    gold = (gold_email or "").lower().strip()
    result = {"exact_match": False, "domain_match": False}
    if not found or not gold:
        return result
    if found == gold:
        result["exact_match"] = result["domain_match"] = True
        return result
    if "@" in found and "@" in gold and found.split("@")[1] == gold.split("@")[1]:
        result["domain_match"] = True
    return result


def evaluate_api(api, professors: List[Dict], api_name: str) -> List[ProfessorResult]:
    print("\n" + "=" * 60)
    print("Evaluating:", api_name)
    print("=" * 60)
    results = []
    for i, prof in enumerate(professors):
        print(f"\n[{i+1}/{len(professors)}] {prof['name']} ({prof['affiliation']})")
        search_results = api.search_professor(
            name=prof["name"],
            affiliation=prof["affiliation"],
            department=prof.get("department", ""),
        )
        all_urls = [r.url for r in search_results if r.url]
        found_website = all_urls[0] if all_urls else ""
        all_emails = extract_emails_from_results(search_results, prof["name"])
        found_email = all_emails[0] if all_emails else ""
        website_match = check_website_match(found_website, prof["gold_website"], prof["name"])
        email_match = check_email_match(found_email, prof["gold_email"])
        result = ProfessorResult(
            name=prof["name"],
            affiliation=prof["affiliation"],
            department=prof.get("department", ""),
            gold_email=prof["gold_email"],
            gold_website=prof["gold_website"],
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
        print("  " + " | ".join(status))
    return results


def calculate_metrics(results: List[ProfessorResult]) -> Dict:
    total = len(results)
    if total == 0:
        return {}
    return {
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
        "avg_website_score": round(sum(r.website_score() for r in results) / total, 3),
        "avg_email_score": round(sum(r.email_score() for r in results) / total, 3),
    }


def save_results(results: List[ProfessorResult], metrics: Dict, api_stats: Dict, output_dir: str, api_name: str):
    os.makedirs(output_dir, exist_ok=True)
    for key in ("website", "email"):
        m = metrics[key]
        total = metrics["total_professors"]
        m["exact_rate"] = round(m["exact_match"] / total * 100, 1) if total else 0
        m["domain_rate"] = round(m["domain_match"] / total * 100, 1) if total else 0
        m["found_rate"] = round(m["found_any"] / total * 100, 1) if total else 0
    metrics["combined_score"] = round((metrics["avg_website_score"] + metrics["avg_email_score"]) / 2, 3)
    output = {
        "api": api_name,
        "timestamp": datetime.now().isoformat(),
        "stats": api_stats,
        "metrics": metrics,
        "results": [asdict(r) for r in results],
    }
    filepath = os.path.join(output_dir, f"{api_name.lower()}_results.json")
    with open(filepath, "w") as f:
        json.dump(output, f, indent=2)
    print("\nSaved:", filepath)


def generate_comparison_report(all_results: Dict, output_dir: str):
    report = []
    report.append("# API Search Evaluation Report")
    report.append("\n**Generated:** " + datetime.now().strftime("%Y-%m-%d %H:%M"))
    n = list(all_results.values())[0]["metrics"]["total_professors"]
    report.append(f"\n**Professors Tested:** {n}")
    report.append("\n## Summary Comparison")
    apis = list(all_results.keys())
    report.append("\n| Metric | " + " | ".join(apis) + " |")
    report.append("|--------|" + "|".join(["--------"] * len(apis)) + "|")
    for metric_name, key in [
        ("Website Exact Match %", ("website", "exact_rate")),
        ("Website Domain Match %", ("website", "domain_rate")),
        ("Website Found Any %", ("website", "found_rate")),
        ("Email Exact Match %", ("email", "exact_rate")),
        ("Email Domain Match %", ("email", "domain_rate")),
        ("Email Found Any %", ("email", "found_rate")),
        ("Combined Score", ("combined_score", None)),
    ]:
        row = f"| {metric_name} |"
        for api_name, data in all_results.items():
            m = data["metrics"]
            if key[1] is None:
                row += f" {m.get(key[0], 'N/A')} |"
            else:
                val = m[key[0]][key[1]]
                row += f" {val}% |" if "%" in metric_name else f" {val} |"
        report.append(row)
    report.append("\n## Recommendation")
    best = max(all_results.items(), key=lambda x: x[1]["metrics"]["combined_score"])
    report.append(f"\n**Best Overall:** {best[0]} (Score: {best[1]['metrics']['combined_score']})")
    filepath = os.path.join(output_dir, "comparison_report.md")
    with open(filepath, "w") as f:
        f.write("\n".join(report))
    print("\nReport saved:", filepath)
    print("\n" + "\n".join(report[4:14]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=GOLD_STANDARD_FILE, help="Gold standard CSV")
    parser.add_argument("--output", default=RESULTS_DIR, help="Output directory")
    parser.add_argument("--apis", nargs="+", default=["exa", "tavily", "brave"], help="APIs to test")
    parser.add_argument("--limit", type=int, default=None, help="Limit professors (for testing)")
    args = parser.parse_args()

    print("Loading gold standard from:", args.input)
    professors = load_gold_standard(args.input)
    print("Loaded", len(professors), "professors")

    if args.limit:
        professors = professors[: args.limit]
        print("Limited to", len(professors))

    apis = {}
    if "exa" in args.apis and EXA_API_KEY:
        apis["Exa"] = ExaSearch(EXA_API_KEY, delay=REQUEST_DELAY)
    if "tavily" in args.apis and TAVILY_API_KEY:
        apis["Tavily"] = TavilySearch(TAVILY_API_KEY, delay=REQUEST_DELAY)
    if "brave" in args.apis and BRAVE_API_KEY:
        apis["Brave"] = BraveSearch(BRAVE_API_KEY, delay=REQUEST_DELAY)

    if not apis:
        print("ERROR: No API keys configured!")
        return

    print("\nTesting APIs:", ", ".join(apis.keys()))
    all_results = {}

    for api_name, api in apis.items():
        results = evaluate_api(api, professors, api_name)
        metrics = calculate_metrics(results)
        stats = api.get_stats()
        save_results(results, metrics, stats, args.output, api_name)
        all_results[api_name] = {"results": results, "metrics": metrics, "stats": stats}

    generate_comparison_report(all_results, args.output)
    print("\nEvaluation complete!")


if __name__ == "__main__":
    main()
