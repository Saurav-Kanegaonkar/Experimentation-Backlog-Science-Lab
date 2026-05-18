# Methodology

## Backlog scoring

Each hypothesis is scored from value pool, expected lift, confidence, effort, measurement risk, data quality, and minimum detectable effect. The score intentionally penalizes hypotheses that look attractive but cannot be measured cleanly.

## Statistical readout

Completed experiments use a two-proportion z-test over control and variant conversion counts. The output includes relative lift, coefficient-style percentage point lift, a 95 percent confidence interval, z-score, p-value, and a business interpretation.

## Causal inference framing

The modeled design assumes randomized A/B tests with pre-period covariate adjustment. In a real client setting, the same surface could be extended to difference-in-differences or matched-market tests when randomization is not available.

## Data quality gate

Source readiness combines completeness, duplicate event rate, late event rate, schema pass status, and issue counts. Low readiness should block stakeholder reporting even when a statistical result looks promising.
