import csv
import json
import math
import random
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUTS = ROOT / "analysis" / "outputs"
SEED = 81742
random.seed(SEED)


VERTICALS = [
    ("Healthcare", 0.034, 185000),
    ("Financial services", 0.028, 240000),
    ("Higher education", 0.046, 132000),
    ("B2C retail", 0.071, 210000),
    ("High-tech", 0.039, 168000),
]

STAGES = [
    ("Awareness", "qualified_visit_rate", "bounce_rate"),
    ("Consideration", "lead_start_rate", "cost_per_lead"),
    ("Conversion", "application_submit_rate", "checkout_error_rate"),
    ("Retention", "repeat_engagement_rate", "unsubscribe_rate"),
]

LEVERS = [
    "audience qualification",
    "landing page sequencing",
    "offer framing",
    "email journey timing",
    "paid media routing",
    "Adobe Target personalization",
    "Customer Journey Analytics segment",
    "AEP audience activation",
]

AUDIENCES = [
    "new visitors",
    "returning prospects",
    "high intent visitors",
    "abandoned journey users",
    "existing customers",
    "lookalike paid audiences",
]


def norm(mean, sd, low, high):
    return max(low, min(high, random.gauss(mean, sd)))


def two_prop_p_value(control_n, control_x, variant_n, variant_x):
    p1 = control_x / control_n
    p2 = variant_x / variant_n
    pooled = (control_x + variant_x) / (control_n + variant_n)
    se = math.sqrt(max(1e-9, pooled * (1 - pooled) * (1 / control_n + 1 / variant_n)))
    z = (p2 - p1) / se
    return math.erfc(abs(z) / math.sqrt(2)), z


def ci_for_lift(control_n, control_x, variant_n, variant_x):
    p1 = control_x / control_n
    p2 = variant_x / variant_n
    se = math.sqrt(max(1e-9, p1 * (1 - p1) / control_n + p2 * (1 - p2) / variant_n))
    diff = p2 - p1
    return diff - 1.96 * se, diff + 1.96 * se


def mde_approx(baseline, n_per_variant):
    se = math.sqrt(2 * baseline * (1 - baseline) / n_per_variant)
    return 2.8 * se / baseline


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_hypotheses():
    rows = []
    for idx in range(1, 37):
        vertical, base_rate, value_anchor = random.choice(VERTICALS)
        stage, primary_kpi, guardrail = random.choice(STAGES)
        lever = random.choice(LEVERS)
        audience = random.choice(AUDIENCES)
        baseline = norm(base_rate, base_rate * 0.18, 0.012, 0.105)
        expected_lift = norm(0.105, 0.045, 0.025, 0.24)
        n_per_variant = int(round(norm(22500, 6500, 9000, 42000), -2))
        mde = mde_approx(baseline, n_per_variant)
        quality = norm(88, 7, 62, 99)
        measurement_risk = round(max(1, 100 - quality + norm(14, 7, 1, 32)), 1)
        confidence = norm(72, 11, 42, 94)
        effort = int(round(norm(6, 2.1, 2, 11)))
        value_pool = int(round(norm(value_anchor, value_anchor * 0.22, 65000, 360000), -3))
        upside = value_pool * expected_lift
        priority = (
            upside / 1000 * 0.48
            + confidence * 0.18
            + max(0, 100 - measurement_risk) * 0.16
            + quality * 0.12
            - effort * 2.4
            - max(0, mde - expected_lift) * 100
        )
        if quality < 74 or measurement_risk > 36:
            status = "Needs QA"
        elif priority > 38:
            status = "Ready for brief"
        elif expected_lift > mde:
            status = "Design review"
        else:
            status = "Research"
        rows.append(
            {
                "hypothesis_id": f"HYP-{idx:03d}",
                "client_vertical": vertical,
                "journey_stage": stage,
                "audience": audience,
                "lever": lever,
                "hypothesis_statement": f"If we change {lever} for {audience}, then {primary_kpi.replace('_', ' ')} will improve without harming {guardrail.replace('_', ' ')}.",
                "primary_kpi": primary_kpi,
                "guardrail_metric": guardrail,
                "baseline_rate": round(baseline, 4),
                "expected_lift_pct": round(expected_lift * 100, 1),
                "mde_pct": round(mde * 100, 1),
                "sample_size_per_variant": n_per_variant,
                "value_pool": value_pool,
                "confidence_score": round(confidence, 1),
                "effort_points": effort,
                "data_quality_score": round(quality, 1),
                "measurement_risk": measurement_risk,
                "priority_score": round(priority, 1),
                "backlog_status": status,
                "recommended_design": "A/B test with pre-period covariate adjustment" if measurement_risk < 32 else "Instrument first, then A/B test",
            }
        )
    return rows


def build_results(hypotheses):
    rows = []
    completed = sorted(hypotheses, key=lambda r: float(r["priority_score"]), reverse=True)[:18]
    for idx, hyp in enumerate(completed, start=1):
        baseline = float(hyp["baseline_rate"])
        expected_lift = float(hyp["expected_lift_pct"]) / 100
        true_lift = norm(expected_lift * 0.72, 0.045, -0.04, 0.22)
        control_n = int(hyp["sample_size_per_variant"]) + random.randint(-900, 900)
        variant_n = int(hyp["sample_size_per_variant"]) + random.randint(-900, 900)
        control_rate = norm(baseline, baseline * 0.045, 0.006, 0.13)
        variant_rate = max(0.004, min(0.16, control_rate * (1 + true_lift)))
        control_x = round(control_n * control_rate)
        variant_x = round(variant_n * variant_rate)
        p_value, z_score = two_prop_p_value(control_n, control_x, variant_n, variant_x)
        low, high = ci_for_lift(control_n, control_x, variant_n, variant_x)
        lift = (variant_x / variant_n) / (control_x / control_n) - 1
        coefficient_pp = (variant_x / variant_n - control_x / control_n) * 100
        if p_value < 0.05 and lift > 0:
            decision = "Scale"
        elif p_value < 0.1 and lift > 0:
            decision = "Validate"
        elif lift < 0:
            decision = "Stop"
        else:
            decision = "Learn"
        rows.append(
            {
                "experiment_id": f"EXP-{idx:03d}",
                "hypothesis_id": hyp["hypothesis_id"],
                "client_vertical": hyp["client_vertical"],
                "journey_stage": hyp["journey_stage"],
                "primary_kpi": hyp["primary_kpi"],
                "control_n": control_n,
                "variant_n": variant_n,
                "control_conversions": control_x,
                "variant_conversions": variant_x,
                "control_rate": round(control_x / control_n, 4),
                "variant_rate": round(variant_x / variant_n, 4),
                "relative_lift_pct": round(lift * 100, 1),
                "coefficient_lift_pp": round(coefficient_pp, 2),
                "ci_low_pp": round(low * 100, 2),
                "ci_high_pp": round(high * 100, 2),
                "z_score": round(z_score, 2),
                "p_value": round(p_value, 4),
                "decision": decision,
                "business_interpretation": story_for(decision, coefficient_pp, hyp),
            }
        )
    return rows


def story_for(decision, coefficient_pp, hyp):
    kpi = hyp["primary_kpi"].replace("_", " ")
    if decision == "Scale":
        return f"Variant improves {kpi} by {coefficient_pp:.2f} points with enough evidence to brief stakeholders on rollout."
    if decision == "Validate":
        return f"Directional lift in {kpi}, but the confidence band is still wide. Extend or retest before scaling."
    if decision == "Stop":
        return f"Variant underperforms on {kpi}. Use the learning to refine the next hypothesis instead of scaling."
    return f"Result is inconclusive. Convert the readout into a learning and prioritize a sharper follow-up test."


def build_quality():
    rows = []
    start = date(2026, 1, 1)
    sources = [
        ("Adobe Analytics", 0.985, 0.006),
        ("Adobe Target", 0.978, 0.009),
        ("Customer Journey Analytics", 0.982, 0.007),
        ("Cloud warehouse mart", 0.991, 0.004),
    ]
    for day in range(42):
        for source, base_complete, dup_base in sources:
            completeness = norm(base_complete, 0.012, 0.91, 1.0)
            duplicate_rate = norm(dup_base, 0.004, 0, 0.032)
            late_event_rate = norm(0.018, 0.012, 0, 0.07)
            schema_pass = 1 if random.random() > 0.08 else 0
            issue_count = int((1 - completeness) * 80 + duplicate_rate * 120 + late_event_rate * 70 + (1 - schema_pass) * 12)
            readiness = 100 - issue_count * 2.2 - (1 - schema_pass) * 12
            rows.append(
                {
                    "date": (start + timedelta(days=day)).isoformat(),
                    "source_system": source,
                    "completeness_rate": round(completeness, 4),
                    "duplicate_rate": round(duplicate_rate, 4),
                    "late_event_rate": round(late_event_rate, 4),
                    "schema_pass": schema_pass,
                    "issue_count": issue_count,
                    "pipeline_readiness_score": round(max(48, min(100, readiness)), 1),
                }
            )
    return rows


def build_briefs(results, backlog, quality):
    scale_count = sum(1 for r in results if r["decision"] == "Scale")
    validate_count = sum(1 for r in results if r["decision"] == "Validate")
    qa_hold = sum(1 for h in backlog if h["backlog_status"] == "Needs QA")
    avg_quality = sum(float(q["pipeline_readiness_score"]) for q in quality) / len(quality)
    top = max(backlog, key=lambda r: float(r["priority_score"]))
    return [
        {
            "brief_id": "BRF-001",
            "audience": "Client executive sponsor",
            "headline": f"{scale_count} experiments are ready to scale, with {validate_count} needing one more readout before investment.",
            "recommendation": "Approve rollout for statistically clear winners and keep directional tests in the next sprint until confidence improves.",
            "supporting_metric": f"{scale_count} scale decisions, {validate_count} validate decisions",
        },
        {
            "brief_id": "BRF-002",
            "audience": "Marketing analytics lead",
            "headline": f"{qa_hold} backlog items should stay out of reporting until instrumentation is repaired.",
            "recommendation": "Partner with engineering on schema, duplicate event, and late event checks before using these hypotheses in recurring reporting.",
            "supporting_metric": f"{avg_quality:.1f} average pipeline readiness score",
        },
        {
            "brief_id": "BRF-003",
            "audience": "Experimentation program owner",
            "headline": f"{top['hypothesis_id']} is the strongest next test because value, confidence, and measurable effect size line up.",
            "recommendation": "Move the top ranked hypothesis into an optimization brief with KPI, guardrail, sample size, and launch criteria already attached.",
            "supporting_metric": f"{top['priority_score']} priority score",
        },
    ]


def write_markdown(backlog, results, quality, briefs):
    top = sorted(backlog, key=lambda r: float(r["priority_score"]), reverse=True)[:5]
    scale = [r for r in results if r["decision"] == "Scale"]
    avg_quality = sum(float(q["pipeline_readiness_score"]) for q in quality) / len(quality)
    best = top[0]
    best_result = min(results, key=lambda r: float(r["p_value"]))

    (ROOT / "analysis" / "analysis_plan.md").write_text(
        "\n".join(
            [
                "# Analysis Plan",
                "",
                "1. Translate client discovery themes into testable marketing hypotheses with primary KPIs and guardrails.",
                "2. Score each hypothesis by value pool, expected lift, confidence, effort, measurement risk, data quality, and minimum detectable effect.",
                "3. Read completed experiments with treatment-control conversion rates, relative lift, confidence intervals, p-values, and coefficient-style lift.",
                "4. Use pipeline quality checks to decide whether the result is ready for reporting, needs engineering remediation, or should remain a learning.",
                "5. Convert the statistical readout into stakeholder recommendations that explain the so what behind the result.",
                "",
            ]
        )
    )

    (ROOT / "analysis" / "executive_findings.md").write_text(
        "\n".join(
            [
                "# Executive Findings",
                "",
                "## What I analyzed",
                "",
                f"I generated {len(backlog)} structured marketing hypotheses, {len(results)} completed experiment readouts, {len(quality)} source quality checks, and {len(briefs)} stakeholder briefs.",
                "",
                "## Findings",
                "",
                f"- The strongest next hypothesis is {best['hypothesis_id']} with a priority score of {best['priority_score']}, a {best['expected_lift_pct']} percent expected lift, and a {best['mde_pct']} percent minimum detectable effect.",
                f"- {len(scale)} completed experiments meet the scale threshold using p-value, lift direction, and confidence interval checks.",
                f"- The clearest statistical readout is {best_result['experiment_id']} with a {best_result['relative_lift_pct']} percent relative lift and p-value of {best_result['p_value']}.",
                f"- Average pipeline readiness is {avg_quality:.1f}, which means the data is usable for most readouts but still needs source-level QA before executive reporting.",
                "",
                "## Recommendation",
                "",
                "Use the backlog score to choose the next tests, use the statistical readout to separate signal from noise, and use the quality surface to decide when engineering remediation is required before a client presentation.",
                "",
            ]
        )
    )

    (ROOT / "analysis" / "methodology.md").write_text(
        "\n".join(
            [
                "# Methodology",
                "",
                "## Backlog scoring",
                "",
                "Each hypothesis is scored from value pool, expected lift, confidence, effort, measurement risk, data quality, and minimum detectable effect. The score intentionally penalizes hypotheses that look attractive but cannot be measured cleanly.",
                "",
                "## Statistical readout",
                "",
                "Completed experiments use a two-proportion z-test over control and variant conversion counts. The output includes relative lift, coefficient-style percentage point lift, a 95 percent confidence interval, z-score, p-value, and a business interpretation.",
                "",
                "## Causal inference framing",
                "",
                "The modeled design assumes randomized A/B tests with pre-period covariate adjustment. In a real client setting, the same surface could be extended to difference-in-differences or matched-market tests when randomization is not available.",
                "",
                "## Data quality gate",
                "",
                "Source readiness combines completeness, duplicate event rate, late event rate, schema pass status, and issue counts. Low readiness should block stakeholder reporting even when a statistical result looks promising.",
                "",
            ]
        )
    )


def write_sql():
    (ROOT / "analysis" / "sql_checks.sql").write_text(
        "\n".join(
            [
                "-- Experiment backlog readiness, written in warehouse-friendly SQL",
                "select",
                "  hypothesis_id,",
                "  client_vertical,",
                "  primary_kpi,",
                "  guardrail_metric,",
                "  expected_lift_pct,",
                "  mde_pct,",
                "  priority_score,",
                "  backlog_status",
                "from hypothesis_backlog",
                "where data_quality_score >= 75",
                "  and measurement_risk <= 35",
                "order by priority_score desc;",
                "",
                "-- Treatment-control readout QA",
                "select",
                "  experiment_id,",
                "  hypothesis_id,",
                "  relative_lift_pct,",
                "  coefficient_lift_pp,",
                "  p_value,",
                "  decision",
                "from experiment_results",
                "where control_n >= 9000",
                "  and variant_n >= 9000",
                "order by p_value asc;",
                "",
                "-- Source reliability gate before client reporting",
                "select",
                "  source_system,",
                "  avg(completeness_rate) as avg_completeness_rate,",
                "  avg(duplicate_rate) as avg_duplicate_rate,",
                "  avg(late_event_rate) as avg_late_event_rate,",
                "  avg(pipeline_readiness_score) as avg_pipeline_readiness_score",
                "from pipeline_quality",
                "group by 1",
                "having avg(pipeline_readiness_score) >= 82;",
                "",
            ]
        )
    )


def main():
    DATA.mkdir(exist_ok=True)
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    backlog = build_hypotheses()
    results = build_results(backlog)
    quality = build_quality()
    briefs = build_briefs(results, backlog, quality)

    write_csv(DATA / "hypothesis_backlog.csv", backlog, list(backlog[0].keys()))
    write_csv(DATA / "experiment_results.csv", results, list(results[0].keys()))
    write_csv(DATA / "pipeline_quality.csv", quality, list(quality[0].keys()))
    write_csv(DATA / "stakeholder_briefs.csv", briefs, list(briefs[0].keys()))

    priority = sorted(backlog, key=lambda r: float(r["priority_score"]), reverse=True)
    write_csv(OUTPUTS / "experiment_priority_queue.csv", priority, list(priority[0].keys()))
    write_csv(OUTPUTS / "statistical_readouts.csv", sorted(results, key=lambda r: float(r["p_value"])), list(results[0].keys()))

    rollup = []
    for source in sorted({q["source_system"] for q in quality}):
        records = [q for q in quality if q["source_system"] == source]
        rollup.append(
            {
                "source_system": source,
                "avg_completeness_rate": round(sum(float(r["completeness_rate"]) for r in records) / len(records), 4),
                "avg_duplicate_rate": round(sum(float(r["duplicate_rate"]) for r in records) / len(records), 4),
                "avg_late_event_rate": round(sum(float(r["late_event_rate"]) for r in records) / len(records), 4),
                "avg_pipeline_readiness_score": round(sum(float(r["pipeline_readiness_score"]) for r in records) / len(records), 1),
                "schema_fail_days": sum(1 for r in records if int(r["schema_pass"]) == 0),
            }
        )
    write_csv(OUTPUTS / "data_quality_rollup.csv", rollup, list(rollup[0].keys()))

    scale_count = sum(1 for r in results if r["decision"] == "Scale")
    model_summary = {
        "seed": SEED,
        "hypotheses_scored": len(backlog),
        "completed_experiments": len(results),
        "pipeline_quality_checks": len(quality),
        "scale_recommendations": scale_count,
        "statistical_method": "two-proportion z-test with coefficient-style percentage point lift",
        "causal_design": "randomized A/B test with pre-period covariate adjustment framing",
    }
    (ROOT / "analysis" / "outputs" / "model_summary.json").write_text(json.dumps(model_summary, indent=2) + "\n")

    write_markdown(backlog, results, quality, briefs)
    write_sql()

    print(json.dumps(model_summary, indent=2))


if __name__ == "__main__":
    main()
