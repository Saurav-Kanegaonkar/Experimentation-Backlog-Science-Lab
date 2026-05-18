-- Experiment backlog readiness, written in warehouse-friendly SQL
select
  hypothesis_id,
  client_vertical,
  primary_kpi,
  guardrail_metric,
  expected_lift_pct,
  mde_pct,
  priority_score,
  backlog_status
from hypothesis_backlog
where data_quality_score >= 75
  and measurement_risk <= 35
order by priority_score desc;

-- Treatment-control readout QA
select
  experiment_id,
  hypothesis_id,
  relative_lift_pct,
  coefficient_lift_pp,
  p_value,
  decision
from experiment_results
where control_n >= 9000
  and variant_n >= 9000
order by p_value asc;

-- Source reliability gate before client reporting
select
  source_system,
  avg(completeness_rate) as avg_completeness_rate,
  avg(duplicate_rate) as avg_duplicate_rate,
  avg(late_event_rate) as avg_late_event_rate,
  avg(pipeline_readiness_score) as avg_pipeline_readiness_score
from pipeline_quality
group by 1
having avg(pipeline_readiness_score) >= 82;
