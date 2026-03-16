#!/usr/bin/env bash
# Run evaluation with NAME + AFFILIATION + DEPARTMENT.
# Results in results_affiliation_department/
cd "$(dirname "$0")"
python evaluate.py \
  --input gold_standard_affiliation_department.csv \
  --output results_affiliation_department \
  --apis exa tavily brave
