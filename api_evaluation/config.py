"""
API Configuration - Store your API keys here or use environment variables.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# API Keys (use env vars in production; defaults for evaluation)
EXA_API_KEY = os.environ.get("EXA_API_KEY", "b442efdf-f0e9-4be2-9d5c-e9f8f38a934c")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "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")
BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "BSA3m39xjv0LIasTrGrfR71hG00rWwQ")

# Search settings
MAX_RESULTS_PER_QUERY = 5
REQUEST_DELAY = 0.5  # Seconds between requests

# File paths (relative to api_evaluation dir)
BASE_DIR = Path(__file__).resolve().parent
GOLD_STANDARD_FILE = str(BASE_DIR / "gold_standard.csv")
RESULTS_DIR = str(BASE_DIR / "results")

# Evaluation settings
DOMAIN_MATCH_WEIGHT = 0.5  # Partial credit for domain match
NAME_IN_URL_WEIGHT = 0.3   # Partial credit for name in URL
