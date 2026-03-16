# Exa Run Until Credits

Same pipeline as the 80-professor test, scaled to run until Exa credits are exhausted or a cap is reached. Supports resume and dry-run.

## Command

From repo root (using venv):

```bash
cd api_evaluation
../.venv/bin/python exa/run_exa_until_credits.py --input <INPUT_PATH> --output exa/results_exa_until_credits [--max-professors N] [--dry-run]
```

Or with env vars:

```bash
cd api_evaluation
export EXA_API_KEY=your_exa_key
export INPUT_PATH=gold_standard_affiliation_only.csv   # or path to full Harvard CSV
export OUTPUT_DIR=exa/results_exa_until_credits
export MAX_PROFESSORS=10000   # optional cap
../.venv/bin/python exa/run_exa_until_credits.py
```

## Required env vars

| Variable | Description |
|----------|-------------|
| `EXA_API_KEY` | Exa API key (or set in `config.py`). |

## Optional env vars

| Variable | Description |
|----------|-------------|
| `INPUT_PATH` | CSV path (default: `api_evaluation/gold_standard_harvard_full.csv`). |
| `OUTPUT_DIR` | Output directory (default: `api_evaluation/exa/results_exa_until_credits`). |
| `MAX_PROFESSORS` | Stop after this many professors (default: 10000). |

## Input CSV format

Same as the 80-test gold standard. Columns (any casing): `name`, `affiliation`, `department`, `gold_email`, `gold_website`. Rows must have at least `name` and `affiliation`.

## Outputs (same as 80-test)

- `OUTPUT_DIR/exa_results.json` – Same structure as `evaluate.py` (api, timestamp, stats, metrics, results).
- `OUTPUT_DIR/exa_found.csv` – Same columns as `exa_found_80.csv`: name, affiliation, department, gold_email, gold_website, found_website, found_email, all_urls, all_emails.

Additional:

- `OUTPUT_DIR/checkpoint.json` – Resume state (last index, processed indices).
- `OUTPUT_DIR/failures.csv` – Rows that failed (index, name, error).
- `OUTPUT_DIR/run.log` – Progress and errors.

## Resume after interruption

Re-run the same command. The script reads `OUTPUT_DIR/checkpoint.json` and continues from the last processed index. No need to delete anything.

## Cap professors

```bash
../.venv/bin/python exa/run_exa_until_credits.py --input gold_standard_harvard_full.csv --output exa/results_exa_until_credits --max-professors 500
```

## Dry-run (no Exa calls)

Validates paths and output schema by processing 2 professors with mock results:

```bash
cd api_evaluation
../.venv/bin/python exa/run_exa_until_credits.py --dry-run --output exa/results_exa_until_credits
```

Check `exa/results_exa_until_credits/exa_results.json` and `exa_found.csv` for the expected format.

## Stop conditions

1. Exa returns a quota/credits/limit/429/402 error → stop and save.
2. `--max-professors` reached.
3. All input rows processed.
