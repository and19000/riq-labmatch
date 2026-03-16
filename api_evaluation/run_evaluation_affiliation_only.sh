#!/usr/bin/env bash
# Run evaluation with NAME + AFFILIATION only (department blank).
# Results in results_affiliation_only/
cd "$(dirname "$0")"
python evaluate.py \
  --input gold_standard_affiliation_only.csv \
  --output results_affiliation_only \
  --apis exa tavily brave
