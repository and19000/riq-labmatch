# API Search Evaluation Pipeline

Compares **Exa**, **Tavily**, and **Brave** search APIs on website/email discovery for 80 Harvard professors.

## Data

- **Test_data_set_80.csv** – First 80 professors from the Harvard faculty eval sample (in `faculty_pipeline/data/`).
- **gold_standard_affiliation_only.csv** – Name + affiliation only (department blank). Use to test how well APIs do with minimal input.
- **gold_standard_affiliation_department.csv** – Name + affiliation + department. Use to test if adding department improves results.

Gold columns: `name`, `affiliation`, `department`, `gold_email`, `gold_website`.

## Setup

```bash
cd api_evaluation
pip install -r requirements.txt
# API keys are in config.py (or set EXA_API_KEY, TAVILY_API_KEY, BRAVE_API_KEY in .env)
```

## Run

```bash
# Quick test (5 professors)
python evaluate.py --input gold_standard_affiliation_only.csv --output results_affiliation_only --limit 5

# Full run: affiliation only (name + affiliation)
python evaluate.py --input gold_standard_affiliation_only.csv --output results_affiliation_only

# Full run: with department (name + affiliation + department)
python evaluate.py --input gold_standard_affiliation_department.csv --output results_affiliation_department
```

Or use the scripts:

```bash
./run_evaluation_affiliation_only.sh
./run_evaluation_with_department.sh
```

## Output

- `results_*/exa_results.json`, `tavily_results.json`, `brave_results.json` – per-API results.
- `results_*/comparison_report.md` – summary table and recommendation.

Compare `results_affiliation_only/comparison_report.md` vs `results_affiliation_department/comparison_report.md` to see whether adding the department field improves website/email discovery.

## Run Exa until credits exhausted (scaled 80-test)

Same Exa pipeline as the 80-professor test, with resume and a cap. See [../docs/exa_run.md](../docs/exa_run.md).

```bash
# Dry-run (2 professors, no API calls)
python exa/run_exa_until_credits.py --dry-run --output exa/results_exa_until_credits

# Full run until credits or cap (resume by re-running same command)
export EXA_API_KEY=your_key
python exa/run_exa_until_credits.py --output exa/results_exa_until_credits
python exa/run_exa_until_credits.py --output exa/results_exa_until_credits --max-professors 500
```
