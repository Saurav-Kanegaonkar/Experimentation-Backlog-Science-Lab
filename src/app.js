const files = {
  backlog: "data/hypothesis_backlog.csv",
  results: "data/experiment_results.csv",
  quality: "analysis/outputs/data_quality_rollup.csv",
  briefs: "data/stakeholder_briefs.csv",
};

const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const number = new Intl.NumberFormat("en-US");

function parseCsv(text) {
  const rows = [];
  let row = [];
  let value = "";
  let quoted = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];

    if (char === "\"" && quoted && next === "\"") {
      value += "\"";
      i += 1;
    } else if (char === "\"") {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      row.push(value);
      value = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && next === "\n") i += 1;
      row.push(value);
      if (row.some((cell) => cell.length)) rows.push(row);
      row = [];
      value = "";
    } else {
      value += char;
    }
  }

  if (value.length || row.length) {
    row.push(value);
    rows.push(row);
  }

  const [headers, ...records] = rows;
  return records.map((record) =>
    headers.reduce((item, header, index) => {
      item[header] = record[index] ?? "";
      return item;
    }, {})
  );
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\"", "&quot;")
    .replaceAll("'", "&#039;");
}

function pct(value, digits = 1) {
  return `${Number(value).toFixed(digits)}%`;
}

function statusClass(value) {
  return String(value).toLowerCase().replaceAll(" ", "-").replace("needs-qa", "qa");
}

function renderTable(target, headers, rows) {
  target.innerHTML = `
    <thead>
      <tr>${headers.map((header) => `<th>${escapeHtml(header.label)}</th>`).join("")}</tr>
    </thead>
    <tbody>
      ${rows
        .map(
          (row, rowIndex) => `
            <tr>
              ${headers.map((header) => `<td>${header.render(row, rowIndex)}</td>`).join("")}
            </tr>
          `
        )
        .join("")}
    </tbody>
  `;
}

function renderMetrics(backlog, results, quality) {
  const ready = backlog.filter((row) => row.backlog_status === "Ready for brief").length;
  const scale = results.filter((row) => row.decision === "Scale").length;
  const avgQuality = quality.reduce((sum, row) => sum + Number(row.avg_pipeline_readiness_score), 0) / quality.length;
  const value = backlog.reduce((sum, row) => sum + Number(row.value_pool), 0);

  document.querySelector("#summaryMetrics").innerHTML = [
    ["Hypotheses scored", number.format(backlog.length)],
    ["Ready for brief", number.format(ready)],
    ["Scale decisions", number.format(scale)],
    ["Pipeline readiness", pct(avgQuality, 1)],
  ]
    .map(([label, metric]) => `<article class="metric-card"><span>${label}</span><strong>${metric}</strong></article>`)
    .join("");

  document.querySelector("#heroDecision").textContent = `${scale} scale decisions from ${results.length} readouts`;
  document.querySelector("#heroSupport").textContent = `${money.format(value)} in modeled value pools, gated by statistical confidence and source quality.`;
  document.querySelector("#readyCount").textContent = `${ready} ready`;
  document.querySelector("#scaleCount").textContent = `${scale} scale`;
  document.querySelector("#qualityScore").textContent = `${pct(avgQuality, 1)} avg`;
}

function renderBacklog(backlog, briefs) {
  const rows = [...backlog]
    .sort((a, b) => Number(b.priority_score) - Number(a.priority_score))
    .slice(0, 8);

  renderTable(document.querySelector("#backlogTable"), [
    { label: "Rank", render: (_row, index) => index + 1 },
    { label: "Hypothesis", render: (row) => `<strong>${escapeHtml(row.hypothesis_id)}</strong><br>${escapeHtml(row.lever)}` },
    { label: "KPI", render: (row) => escapeHtml(row.primary_kpi.replaceAll("_", " ")) },
    { label: "Lift vs MDE", render: (row) => `${pct(row.expected_lift_pct)} expected<br>${pct(row.mde_pct)} MDE` },
    { label: "Value", render: (row) => money.format(Number(row.value_pool)) },
    { label: "Score", render: (row) => `<span class="score">${escapeHtml(row.priority_score)}</span>` },
    { label: "Status", render: (row) => `<span class="status-pill ${statusClass(row.backlog_status)}">${escapeHtml(row.backlog_status)}</span>` },
  ], rows);

  document.querySelector("#backlogNotes").innerHTML = briefs
    .map(
      (brief) => `
        <article class="note">
          <strong>${escapeHtml(brief.audience)}</strong>
          <p>${escapeHtml(brief.headline)}</p>
        </article>
      `
    )
    .join("");
}

function renderResults(results) {
  const rows = [...results].sort((a, b) => Number(a.p_value) - Number(b.p_value)).slice(0, 9);
  renderTable(document.querySelector("#resultsTable"), [
    { label: "Experiment", render: (row) => `<strong>${escapeHtml(row.experiment_id)}</strong><br>${escapeHtml(row.journey_stage)}` },
    { label: "KPI", render: (row) => escapeHtml(row.primary_kpi.replaceAll("_", " ")) },
    { label: "Lift", render: (row) => `${pct(row.relative_lift_pct)} relative<br>${Number(row.coefficient_lift_pp).toFixed(2)} pts` },
    { label: "95% CI", render: (row) => `${Number(row.ci_low_pp).toFixed(2)} to ${Number(row.ci_high_pp).toFixed(2)} pts` },
    { label: "p-value", render: (row) => Number(row.p_value).toFixed(4) },
    { label: "Decision", render: (row) => `<span class="status-pill ${statusClass(row.decision)}">${escapeHtml(row.decision)}</span>` },
  ], rows);

  const best = rows[0];
  document.querySelector("#coefficientStory").innerHTML = `
    <article class="stat-callout">
      <b>${escapeHtml(best.experiment_id)}: ${pct(best.relative_lift_pct)} lift</b>
      <p>${escapeHtml(best.business_interpretation)}</p>
    </article>
    <article class="note">
      <strong>Statistical translation</strong>
      <p>The coefficient-style lift is ${Number(best.coefficient_lift_pp).toFixed(2)} percentage points with a p-value of ${Number(best.p_value).toFixed(4)}. That gives a non-technical stakeholder both the effect size and the confidence signal.</p>
    </article>
    <article class="note">
      <strong>Decision rule</strong>
      <p>Scale when lift is positive and p-value is below 0.05. Validate when the signal is directional but not yet strong enough for full rollout.</p>
    </article>
  `;
}

function renderQuality(quality, briefs) {
  document.querySelector("#qualityGrid").innerHTML = quality
    .map(
      (row) => `
        <article class="quality-card">
          <strong>${escapeHtml(row.source_system)}</strong>
          <dl>
            <dt>Completeness</dt><dd>${pct(Number(row.avg_completeness_rate) * 100, 1)}</dd>
            <dt>Duplicate rate</dt><dd>${pct(Number(row.avg_duplicate_rate) * 100, 2)}</dd>
            <dt>Late events</dt><dd>${pct(Number(row.avg_late_event_rate) * 100, 2)}</dd>
            <dt>Readiness</dt><dd>${pct(row.avg_pipeline_readiness_score, 1)}</dd>
            <dt>Schema fail days</dt><dd>${escapeHtml(row.schema_fail_days)}</dd>
          </dl>
        </article>
      `
    )
    .join("");

  document.querySelector("#briefs").innerHTML = briefs
    .map(
      (brief) => `
        <article class="note">
          <strong>${escapeHtml(brief.headline)}</strong>
          <p>${escapeHtml(brief.recommendation)} ${escapeHtml(brief.supporting_metric)}.</p>
        </article>
      `
    )
    .join("");
}

function activateTab(tabName) {
  const button = document.querySelector(`[data-tab="${tabName}"]`);
  const surface = document.querySelector(`#${tabName}`);
  if (!button || !surface) return;

  document.querySelectorAll("[data-tab]").forEach((item) => item.classList.remove("active"));
  document.querySelectorAll(".surface").forEach((item) => item.classList.remove("active"));
  button.classList.add("active");
  surface.classList.add("active");
}

function wireTabs() {
  document.querySelectorAll("[data-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      activateTab(button.dataset.tab);
    });
  });
}

async function load() {
  const entries = await Promise.all(
    Object.entries(files).map(async ([key, path]) => {
      const response = await fetch(path);
      if (!response.ok) throw new Error(`Could not load ${path}`);
      return [key, parseCsv(await response.text())];
    })
  );

  const data = Object.fromEntries(entries);
  renderMetrics(data.backlog, data.results, data.quality);
  renderBacklog(data.backlog, data.briefs);
  renderResults(data.results);
  renderQuality(data.quality, data.briefs);
  wireTabs();
  activateTab(new URLSearchParams(window.location.search).get("surface") || "backlog");
}

load().catch((error) => {
  document.querySelector(".shell").insertAdjacentHTML(
    "beforeend",
    `<section class="panel"><h2>Data load failed</h2><p>${escapeHtml(error.message)}</p></section>`
  );
});
