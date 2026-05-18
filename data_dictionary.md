# Data Dictionary

| File | Grain | Purpose |
|---|---|---|
| `data/hypothesis_backlog.csv` | Hypothesis | Structured test ideas with KPI alignment, guardrails, expected lift, MDE, value, confidence, effort, data quality, risk, score, status, and recommended design. |
| `data/experiment_results.csv` | Completed experiment | Treatment-control readout with counts, conversion rates, relative lift, coefficient-style lift, confidence interval, z-score, p-value, decision, and business interpretation. |
| `data/pipeline_quality.csv` | Source system by day | Daily quality checks for completeness, duplicates, late events, schema pass status, issue count, and readiness score. |
| `data/stakeholder_briefs.csv` | Brief | Non-technical recommendation snippets by stakeholder audience. |
| `analysis/outputs/experiment_priority_queue.csv` | Hypothesis | Backlog sorted by priority score for optimization planning. |
| `analysis/outputs/statistical_readouts.csv` | Completed experiment | Experiments sorted by statistical signal strength. |
| `analysis/outputs/data_quality_rollup.csv` | Source system | Average quality metrics used by the frontend quality surface. |
| `analysis/outputs/model_summary.json` | Run | Reproducibility metadata for the synthetic generator and analysis approach. |
