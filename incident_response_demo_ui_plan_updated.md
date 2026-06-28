# Incident Response POC — Live Demo UI Plan (Updated)

**Builds on:** `incident_response_poc_plan.md` (agent pipeline)
**Goal:** Polished browser-based demo — dropdown incident selector, enriched 6-step workflow with RAG/LLM source tags, confidence + remediation panels below
**Target IDE:** Google Antigravity (Plan mode)
**Time estimate:** +1.5–2 days on top of a working Phase 6 CLI pipeline
**Layout changes from previous version:** Removed agent activities table. Workflow stepper replaced with 3×2 card grid showing per-step RAG/LLM source tags and output snippets. Confidence + HITL + remediation moved to bottom two-column section.

---

## How to use this file in Antigravity

Paste into Antigravity Manager chat with:
> "Read this updated UI plan. My agent pipeline already works via CLI. Build frontend/index.html only — do not modify agents/, tools/, or backend/. Follow the exact section structure. Build one section at a time, pause and show me the browser result before continuing."

---

## Design tokens — paste as CSS :root at top of styles

```css
:root {
  --bg-base:    #0D1117;
  --bg-card:    #111827;
  --bg-sunken:  #070B14;
  --border:     #1E293B;
  --border-mid: #334155;
  --teal:       #2DD4BF;
  --teal-bg:    #0F3D36;
  --amber:      #F2A33D;
  --amber-bg:   #3D2A05;
  --red:        #EF4444;
  --red-bg:     #3D1212;
  --red-bdr:    #7B1010;
  --blue:       #2563EB;
  --blue-dark:  #164E96;
  --green:      #10B981;
  --text-1:     #E2E8F0;
  --text-2:     #94A3B8;
  --text-3:     #64748B;
  --text-4:     #475569;
  --r-md:       8px;
  --r-lg:       10px;
}
body { background:var(--bg-base); color:var(--text-1); font-family:Inter,system-ui,sans-serif; font-size:13px; padding:16px; }
* { box-sizing:border-box; margin:0; padding:0; }
```

---

## Required CDN links — add to `<head>`

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.31.0/dist/tabler-icons.min.css"/>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono&family=Inter:wght@400;500&display=swap" rel="stylesheet">
```

---

## Incident data array — define at top of `<script>`

```javascript
const INCIDENTS = [
  { id:"INC-2024-0517", label:"INC-2024-0517 · Payment service · DB connection timeout — pool exhausted (20/20)",
    chip:"CRITICAL", chipBdr:"#7B1010", chipBg:"#1A0808", chipClr:"#EF4444", chipIco:"ti-alert-triangle",
    sev:"Critical", sevClr:"#EF4444", src:"Datadog, PagerDuty", svc:"Payment service",
    ts:"May 17, 2024 · 10:24 AM", progress:57 },
  { id:"INC-2024-0518", label:"INC-2024-0518 · Auth service · DNS resolution failed — NXDOMAIN on auth-service.internal",
    chip:"SEV 2", chipBdr:"#5C3A05", chipBg:"#1A110A", chipClr:"#F2A33D", chipIco:"ti-network",
    sev:"Sev 2", sevClr:"#F2A33D", src:"PagerDuty", svc:"Auth service",
    ts:"May 17, 2024 · 03:41 AM", progress:40 },
  { id:"INC-2024-0519", label:"INC-2024-0519 · Order service · OOM crash — Java heap exhausted, CrashLoopBackOff",
    chip:"SEV 2", chipBdr:"#5C3A05", chipBg:"#1A110A", chipClr:"#F2A33D", chipIco:"ti-apps",
    sev:"Sev 2", sevClr:"#F2A33D", src:"Kubernetes", svc:"Order service",
    ts:"May 17, 2024 · 05:22 AM", progress:20 },
  { id:"INC-2024-0520", label:"INC-2024-0520 · Data pipeline · ETL halted — schema mismatch, expected 24 cols got 27",
    chip:"SEV 4", chipBdr:"#0F3D36", chipBg:"#071F1C", chipClr:"#2DD4BF", chipIco:"ti-transform",
    sev:"Sev 4", sevClr:"#2DD4BF", src:"Alert manager", svc:"Data pipeline",
    ts:"May 17, 2024 · 06:55 AM", progress:0 },
  { id:"INC-2024-0521", label:"INC-2024-0521 · API gateway · 503 cascade — upstream timeout on checkout flow",
    chip:"SEV 2", chipBdr:"#5C3A05", chipBg:"#1A110A", chipClr:"#F2A33D", chipIco:"ti-api",
    sev:"Sev 2", sevClr:"#F2A33D", src:"Datadog", svc:"API gateway",
    ts:"May 17, 2024 · 08:11 AM", progress:30 },
];
let currentIncidentId = null;
let eventSource       = null;
```

---

## Step definitions — what source tag each step shows

This is the most important data structure for the new layout. Each step card shows a RAG/LLM/RAG+LLM badge so the audience can see exactly where the intelligence comes from.

```javascript
const STEPS = [
  {
    num: 1, id: "monitor",
    name: "Monitor agent", sub: "Log & alert ingestion",
    icon: "ti-activity",
    sourceType: "llm",           // LLM only — no memory needed at ingestion
    sourceLabel: "Log parsing & anomaly detection",
    outputKeys: ["detected", "alerts", "first_seen"],
    pendingOutput: "scanning logs…"
  },
  {
    num: 2, id: "triage",
    name: "Triage agent", sub: "Classify & prioritize",
    icon: "ti-filter",
    sourceType: "llm",           // LLM classifies severity from log text
    sourceLabel: "Severity scoring & routing decision",
    outputKeys: ["severity", "category", "confidence", "route_to"],
    pendingOutput: "classifying incident…"
  },
  {
    num: 3, id: "planning",
    name: "Planning agent", sub: "ReAct decomposition",
    icon: "ti-sitemap",
    sourceType: "llm",           // LLM decomposes problem into sub-tasks
    sourceLabel: "Task decomposition via ReAct",
    outputKeys: ["plan", "sub_tasks", "tools_needed"],
    pendingOutput: "creating investigation plan…"
  },
  {
    num: 4, id: "expert",
    name: "Expert agents", sub: "Domain investigation",
    icon: "ti-users",
    sourceType: "rag+llm",       // RAG retrieves past incidents, LLM reasons
    sourceLabel: "Past incidents + new reasoning",
    outputKeys: ["rag_hits", "match", "expert_reasoning"],
    pendingOutput: "retrieving from memory…"
  },
  {
    num: 5, id: "reflection",
    name: "Reflection agent", sub: "Validate & score",
    icon: "ti-shield-check",
    sourceType: "llm",           // LLM critiques its own proposed fix
    sourceLabel: "Self-critique of proposed fix",
    outputKeys: ["score", "critique", "approved"],
    pendingOutput: "awaiting expert output"
  },
  {
    num: 6, id: "decision",
    name: "Decision", sub: "Remediate or escalate",
    icon: "ti-gavel",
    sourceType: "rag+llm",       // RAG for runbook lookup, LLM for final verdict
    sourceLabel: "Final verdict + HITL gate",
    outputKeys: ["action", "hitl_required", "written_to_memory"],
    pendingOutput: "awaiting reflection score"
  }
];
```

---

## Page structure overview

```
<header>                          ← title, status dot, bell, avatar
<section.sec-1>                   ← "1. Select incident"
  <div.select-zone>
    <div.select-row>              ← dropdown | severity chip | run button
    <div.meta-bar>                ← 6 metadata cells
<section.sec-2>                   ← "2. Incident triaging workflow"
  <div.workflow-wrap>
    <div.wf-header>               ← title + legend (RAG / LLM / RAG+LLM)
    <div.steps-grid>              ← 3×2 CSS grid of step cards
      <div.step-card × 6>         ← each card: icon + name + badge + source tag + output snippet
    <div.progress-row>            ← progress bar + elapsed time
<section.sec-3>                   ← "3. Confidence & recommended actions"
  <div.bottom-grid>               ← 2 columns: 1fr 1.5fr
    <div.confidence-panel>        ← SVG ring + 3 rows + HITL approve/reject
    <div.remediation-panel>       ← RAG source note + root cause + actions + buttons
<div.footer-note>
```

---

## Section 1 — Header + select incident

No changes from previous plan. Keep exact same HTML/CSS/JS for:
- Header (title, status pill, bell badge, avatar)
- Section label "1. Select incident"
- Select zone (dropdown + severity chip + run button)
- Meta bar (6 cells: Severity, Status, Source, Service, Created at, Assigned to)

```javascript
// onSelectIncident() — same as before, also reset all step cards to pending state
function onSelectIncident() {
  const i   = parseInt(document.getElementById('inc-dd').value);
  const inc = INCIDENTS[i];
  // ... update chip, meta bar, progress bar (same as before) ...
  resetAllSteps();   // NEW: reset step cards to pending when new incident selected
}

function resetAllSteps() {
  STEPS.forEach(step => updateStepCard(step.id, 'wait', null));
  document.getElementById('progress-fill').style.width = '0%';
  document.getElementById('progress-pct').textContent  = '0%';
}
```

---

## Section 2 — Enriched workflow stepper (KEY NEW SECTION)

### HTML — workflow wrapper

```html
<div class="sec-label"><span class="sec-num">2.</span> Incident triaging workflow</div>

<div class="workflow-wrap">

  <!-- Header row: title + legend -->
  <div class="wf-header">
    <span class="wf-title">Agent pipeline — step by step execution trace</span>
    <div class="legend">
      <div class="legend-item">
        <span class="src-tag rag">RAG</span> retrieved from memory
      </div>
      <div class="legend-item">
        <span class="src-tag llm">LLM</span> generated by model
      </div>
      <div class="legend-item">
        <span class="src-tag both">RAG + LLM</span> memory-augmented
      </div>
    </div>
  </div>

  <!-- 3×2 grid of step cards — generated by JS renderSteps() -->
  <div class="steps-grid" id="steps-grid"></div>

  <!-- Progress bar -->
  <div class="progress-row">
    <span class="prog-label">Overall progress</span>
    <div class="prog-track">
      <div class="prog-fill" id="progress-fill" style="width:0%;"></div>
    </div>
    <span class="prog-pct" id="progress-pct">0%</span>
    <span class="elapsed"><i class="ti ti-clock"></i><span id="elapsed-time">00:00</span></span>
  </div>

</div>
```

### CSS — source tags

```css
.src-tag { font-size:8px; font-weight:500; padding:1px 7px; border-radius:4px; border:0.5px solid; display:inline-flex; align-items:center; gap:3px; }
.src-tag.rag   { background:#1A110A; border-color:var(--amber); color:var(--amber); }
.src-tag.llm   { background:#071F1C; border-color:var(--teal);  color:var(--teal);  }
.src-tag.both  { background:#0F1F3D; border-color:#60A5FA;       color:#60A5FA;       }
```

### CSS — step cards (3×2 grid)

```css
.steps-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
  margin-bottom: 12px;
}
.step-card {
  background: var(--bg-sunken);
  border: 0.5px solid var(--border);
  border-radius: var(--r-md);
  padding: 10px 12px;
}
.step-card.done   { border-color: #1E3A2A; }
.step-card.active { border-color: var(--amber-bg); border-left: 2px solid var(--amber); }
.step-card.wait   { opacity: 0.55; }

/* top row: icon circle + step name + badge */
.step-top   { display:flex; align-items:center; gap:8px; margin-bottom:6px; }
.step-icon  { width:32px; height:32px; border-radius:50%; display:flex; align-items:center; justify-content:center; border:1.5px solid var(--border-mid); background:#1E293B; flex-shrink:0; }
.step-icon i { font-size:15px; color:var(--border-mid); }
.step-icon.done   { border-color:var(--teal);  background:var(--teal-bg); }
.step-icon.done i { color:var(--teal); }
.step-icon.active { border-color:var(--amber); background:var(--amber-bg); }
.step-icon.active i { color:var(--amber); }
.step-meta  { flex:1; }
.step-num   { font-size:9px; font-weight:500; color:var(--text-4); }
.step-num.done   { color:var(--teal); }
.step-num.active { color:var(--amber); }
.step-name  { font-size:11px; font-weight:500; color:var(--text-1); }
.step-badge { font-size:8px; padding:2px 7px; border-radius:20px; font-weight:500; border:0.5px solid; align-self:flex-start; flex-shrink:0; }
.badge-done   { background:var(--teal-bg);  color:var(--teal);  border-color:var(--teal);  }
.badge-active { background:var(--amber-bg); color:var(--amber); border-color:var(--amber); }
.badge-wait   { background:#1E293B; color:var(--text-4); border-color:var(--border-mid); }

/* source row: tag + label */
.source-row { display:flex; align-items:center; gap:5px; margin-bottom:6px; }
.source-label { font-size:9px; color:var(--text-3); }

/* output snippet */
.step-output {
  background: #070B14;
  border-radius: 5px;
  padding: 6px 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  color: var(--text-2);
  line-height: 1.6;
  border-left: 2px solid var(--border);
}
.step-output.done-out   { border-left-color: var(--teal); }
.step-output.active-out { border-left-color: var(--amber); }

/* output value colors */
.out-key   { color: var(--text-4); }
.out-teal  { color: var(--teal); }
.out-amber { color: var(--amber); }
.out-red   { color: var(--red); }
.out-white { color: var(--text-1); }
```

### JS — renderSteps() — called once on page load

```javascript
function renderSteps() {
  const grid = document.getElementById('steps-grid');
  grid.innerHTML = '';
  STEPS.forEach(step => {
    const card = document.createElement('div');
    card.className = 'step-card wait';
    card.id = `step-card-${step.id}`;
    card.innerHTML = `
      <div class="step-top">
        <div class="step-icon" id="step-icon-${step.id}">
          <i class="ti ${step.icon}"></i>
        </div>
        <div class="step-meta">
          <div class="step-num" id="step-num-${step.id}">Step ${step.num} · ${step.name}</div>
          <div class="step-name">${step.sub}</div>
        </div>
        <span class="step-badge badge-wait" id="step-badge-${step.id}">Pending</span>
      </div>
      <div class="source-row">
        <span class="src-tag ${step.sourceType}" id="step-src-${step.id}">
          ${step.sourceType === 'rag+llm' ? 'RAG + LLM' : step.sourceType.toUpperCase()}
        </span>
        <span class="source-label">${step.sourceLabel}</span>
      </div>
      <div class="step-output" id="step-output-${step.id}">
        <span class="out-key">status: </span><span class="out-amber">${step.pendingOutput}</span>
      </div>
    `;
    grid.appendChild(card);
  });
}
window.addEventListener('DOMContentLoaded', renderSteps);
```

### JS — updateStepCard() — called from SSE handler

```javascript
function updateStepCard(stepId, state, outputData) {
  // state: 'done' | 'active' | 'wait'
  const card    = document.getElementById(`step-card-${stepId}`);
  const icon    = document.getElementById(`step-icon-${stepId}`);
  const numEl   = document.getElementById(`step-num-${stepId}`);
  const badge   = document.getElementById(`step-badge-${stepId}`);
  const output  = document.getElementById(`step-output-${stepId}`);
  if (!card) return;

  // Update card class
  card.className = `step-card ${state}`;

  // Update icon
  icon.className = `step-icon ${state}`;

  // Update num color
  numEl.className = `step-num ${state}`;

  // Update badge
  const badgeMap = { done:'badge-done', active:'badge-active', wait:'badge-wait' };
  const badgeTxt = { done:'Done', active:'Active', wait:'Pending' };
  badge.className = `step-badge ${badgeMap[state]}`;
  badge.textContent = badgeTxt[state];

  // Update output snippet
  if (outputData) {
    output.className = `step-output ${state === 'done' ? 'done-out' : 'active-out'}`;
    output.innerHTML = formatOutput(outputData);
  }
}

function formatOutput(data) {
  // data is an object — render as key: value pairs
  return Object.entries(data).map(([k, v]) => {
    const clsMap = {
      severity: 'out-red', category: 'out-teal', confidence: 'out-teal',
      rag_hits: 'out-amber', match: 'out-amber', score: 'out-teal',
      action: 'out-teal'
    };
    const cls = clsMap[k] || 'out-white';
    return `<span class="out-key">${k}: </span><span class="${cls}">${
      typeof v === 'object' ? JSON.stringify(v) : v
    }</span>`;
  }).join('<br>');
}
```

---

## Section 3 — Confidence + recommended actions

### HTML structure

```html
<div class="sec-label"><span class="sec-num">3.</span> Confidence &amp; recommended actions</div>

<div class="bottom-grid">

  <!-- LEFT: Confidence + HITL -->
  <div class="panel">
    <div class="panel-title"><span class="sec-num">4.</span> Confidence &amp; decision</div>

    <div class="ring-area">
      <svg width="90" height="90" viewBox="0 0 90 90" id="conf-svg">
        <circle cx="45" cy="45" r="36" fill="none" stroke="#1E293B" stroke-width="8"/>
        <circle cx="45" cy="45" r="36" fill="none" stroke="#2DD4BF" stroke-width="8"
          stroke-dasharray="0 226" stroke-dashoffset="56" stroke-linecap="round"
          id="conf-arc"/>
        <text x="45" y="48" text-anchor="middle" font-size="18" fill="#E2E8F0"
          font-family="Inter,sans-serif" font-weight="500" id="conf-pct">—</text>
        <text x="45" y="62" text-anchor="middle" font-size="8" fill="#64748B"
          font-family="Inter,sans-serif">Confidence</text>
      </svg>
      <div class="conf-label" id="conf-label">Awaiting analysis</div>
    </div>

    <div class="conf-rows">
      <div class="conf-row"><span class="ck">Threshold</span><span style="color:var(--teal);" id="conf-threshold">70%</span></div>
      <div class="conf-row"><span class="ck">Risk level</span><span style="color:var(--amber);" id="conf-risk">—</span></div>
      <div class="conf-row"><span class="ck">Recommendation</span><span style="color:var(--green);font-weight:500;" id="conf-rec">—</span></div>
    </div>

    <!-- HITL panel — hidden until hitl_required event -->
    <div class="hitl-panel" id="hitl-panel" style="display:none;">
      <div class="hitl-header">
        <span>Human escalation</span>
        <span class="hitl-badge">Pending approval</span>
      </div>
      <p class="hitl-desc">Critical — SRE on-call approval required before remediation executes.</p>
      <div class="hitl-buttons">
        <button class="btn-approve" onclick="approveHITL(true)">
          <i class="ti ti-check"></i> Approve
        </button>
        <button class="btn-reject" onclick="approveHITL(false)">
          <i class="ti ti-x"></i> Reject
        </button>
      </div>
    </div>

  </div>

  <!-- RIGHT: Remediation -->
  <div class="panel" id="remediation-panel">
    <div class="panel-title">
      <span><span class="sec-num">5.</span> Recommended actions</span>
      <span class="auto-badge" id="auto-badge" style="display:none;">Auto-remediable</span>
    </div>

    <!-- RAG source note — shown when fix came from memory -->
    <div class="rag-source-note" id="rag-source-note" style="display:none;">
      <span class="src-tag rag"><i class="ti ti-database"></i>RAG</span>
      <span class="source-label" id="rag-source-text">Fix derived from similar past incidents in memory</span>
    </div>

    <div class="root-cause-box" id="root-cause-box" style="display:none;">
      <div class="root-label">Root cause (predicted)</div>
      <div class="root-text" id="root-cause-text">—</div>
    </div>

    <div class="actions-label" id="actions-label" style="display:none;">Recommended actions</div>
    <div id="actions-list"></div>

    <div class="btn-row" id="btn-row" style="display:none;">
      <button class="btn-execute"><i class="ti ti-bolt"></i>Execute remediation</button>
      <button class="btn-runbook"><i class="ti ti-external-link"></i>View runbook</button>
    </div>

    <!-- Placeholder before result -->
    <div id="remediation-placeholder" style="text-align:center;padding:24px 0;color:var(--text-3);font-size:12px;">
      <i class="ti ti-dots" style="font-size:20px;display:block;margin-bottom:6px;"></i>
      Awaiting agent analysis
    </div>
  </div>

</div>
```

### CSS — bottom grid

```css
.bottom-grid {
  display: grid;
  grid-template-columns: 1fr 1.5fr;
  gap: 10px;
}
.panel {
  background: var(--bg-card);
  border: 0.5px solid var(--border);
  border-radius: var(--r-lg);
  padding: 11px 13px;
}
.panel-title {
  font-size:11px; font-weight:500; color:var(--text-3);
  margin-bottom:10px; display:flex; align-items:center; justify-content:space-between;
}
.ring-area {
  display: flex; gap:14px; align-items:center; margin-bottom:10px;
}
.conf-label { font-size:11px; font-weight:500; color:var(--teal); }
.conf-rows  { display:flex; flex-direction:column; }
.conf-row   { display:flex; justify-content:space-between; font-size:11px; padding:4px 0; border-bottom:0.5px solid var(--border); }
.conf-row:last-child { border:none; }
.ck { color:var(--text-3); }

/* HITL */
.hitl-panel  { background:var(--bg-sunken); border:0.5px solid var(--red-bdr); border-radius:var(--r-md); padding:9px 11px; margin-top:10px; }
.hitl-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:4px; font-size:10px; font-weight:500; }
.hitl-badge  { font-size:8px; background:var(--red-bg); color:var(--red); padding:2px 8px; border-radius:20px; }
.hitl-desc   { font-size:9px; color:var(--text-2); margin-bottom:7px; line-height:1.4; }
.hitl-buttons { display:grid; grid-template-columns:1fr 1fr; gap:6px; }
.btn-approve { background:var(--teal-bg); border:0.5px solid var(--teal); border-radius:var(--r-md); padding:7px; font-size:10px; color:var(--teal); font-weight:500; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:4px; font-family:inherit; }
.btn-reject  { background:var(--red-bg);  border:0.5px solid var(--red);  border-radius:var(--r-md); padding:7px; font-size:10px; color:var(--red);  font-weight:500; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:4px; font-family:inherit; }

/* REMEDIATION */
.auto-badge     { font-size:8px; background:var(--teal-bg); color:var(--teal); padding:2px 8px; border-radius:20px; border:0.5px solid var(--teal); }
.rag-source-note { display:flex; align-items:center; gap:6px; margin-bottom:8px; }
.root-cause-box { background:var(--bg-sunken); border-radius:6px; padding:7px 9px; margin-bottom:8px; }
.root-label     { font-size:8px; color:var(--text-3); margin-bottom:2px; }
.root-text      { font-size:10px; color:var(--text-1); line-height:1.5; }
.actions-label  { font-size:9px; color:var(--text-3); margin-bottom:5px; }
.action-item    { display:flex; gap:5px; font-size:10px; color:#CBD5E1; margin-bottom:4px; line-height:1.4; }
.action-num     { color:var(--teal); font-weight:500; flex-shrink:0; }
.btn-row        { display:grid; grid-template-columns:1fr 1fr; gap:7px; margin-top:10px; }
.btn-execute    { background:var(--blue); border:none; border-radius:var(--r-md); padding:8px; font-size:10px; color:#fff; font-weight:500; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:4px; font-family:inherit; width:100%; }
.btn-runbook    { background:transparent; border:0.5px solid var(--border-mid); border-radius:var(--r-md); padding:8px; font-size:10px; color:var(--text-2); cursor:pointer; display:flex; align-items:center; justify-content:center; gap:4px; font-family:inherit; width:100%; }
```

---

## SSE event → UI mapping

```javascript
function runTriaging() {
  const i   = parseInt(document.getElementById('inc-dd').value);
  const inc = INCIDENTS[i];
  document.getElementById('run-btn-text').textContent = 'Running...';
  document.getElementById('run-btn').style.background = 'var(--blue-dark)';
  resetAllSteps();

  fetch('http://localhost:8000/api/incidents', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ log_text: inc.label, incident_id: inc.id })
  })
  .then(r => r.json())
  .then(data => {
    currentIncidentId = data.incident_id;
    openSSE(currentIncidentId);
  });
}

function openSSE(id) {
  if (eventSource) eventSource.close();
  eventSource = new EventSource(`http://localhost:8000/api/incidents/${id}/stream`);
  let elapsed = 0;
  const timer = setInterval(() => {
    elapsed++;
    const m = String(Math.floor(elapsed/60)).padStart(2,'0');
    const s = String(elapsed%60).padStart(2,'0');
    document.getElementById('elapsed-time').textContent = `${m}:${s}`;
  }, 1000);

  eventSource.onmessage = (evt) => {
    const payload = JSON.parse(evt.data);

    switch (payload.step) {

      case 'classification':
        // Monitor done, Triage active
        updateStepCard('monitor', 'done', {
          detected: payload.data.alert_type,
          alerts:   payload.data.alert_count,
          first_seen: payload.data.timestamp
        });
        updateStepCard('triage', 'active', null);
        updateProgressBar(17);
        break;

      case 'rag_retrieval':
        // Triage done, Planning active
        updateStepCard('triage', 'done', {
          severity:   payload.data.severity,
          category:   payload.data.category,
          confidence: payload.data.confidence,
          route_to:   payload.data.expert
        });
        updateStepCard('planning', 'active', null);
        updateProgressBar(34);
        break;

      case 'expert_analysis':
        // Planning done, Expert active — show RAG hits
        updateStepCard('planning', 'done', {
          plan:      `${payload.data.sub_tasks?.length || 4} sub-tasks`,
          tools:     'search_logs, query_chromadb',
        });
        updateStepCard('expert', 'active', {
          rag_hits: `${payload.data.rag_count} similar incidents found`,
          match:    payload.data.rag_top_match || 'retrieving…',
          expert:   `${payload.data.expert_name} reasoning…`
        });
        updateProgressBar(57);
        break;

      case 'reflection':
        // Expert done, Reflection active
        updateStepCard('expert', 'done', {
          rag_hits:  `${payload.data.rag_count} matched`,
          root_cause: payload.data.root_cause,
          proposed:  payload.data.proposed_fix_summary
        });
        updateStepCard('reflection', 'active', {
          score:    `${payload.data.score}/10`,
          critique: payload.data.critique
        });
        updateProgressBar(75);
        // Show partial confidence ring
        animateConfidenceRing(Math.round(payload.data.confidence * 100));
        break;

      case 'hitl_required':
        // Reflection done, Decision active — show HITL panel
        updateStepCard('reflection', 'done', {
          score:    `${payload.data.score}/10`,
          approved: 'awaiting human'
        });
        updateStepCard('decision', 'active', {
          action:       'paused — human approval needed',
          hitl_required: 'true'
        });
        updateProgressBar(90);
        document.getElementById('hitl-panel').style.display = 'block';
        break;

      case 'complete':
        // All done
        updateStepCard('reflection', 'done', {
          score:    `${payload.data.reflection_score}/10`,
          approved: 'yes'
        });
        updateStepCard('decision', 'done', {
          action:          payload.data.status,
          written_to_memory: 'true'
        });
        updateProgressBar(100);
        animateConfidenceRing(Math.round(payload.data.confidence * 100));
        showRemediationCard(payload.data);
        document.getElementById('run-btn-text').textContent = 'Run incident triaging';
        document.getElementById('run-btn').style.background = 'var(--blue)';
        clearInterval(timer);
        eventSource.close();
        break;
    }
  };
}

function updateProgressBar(pct) {
  document.getElementById('progress-fill').style.width = pct + '%';
  document.getElementById('progress-pct').textContent  = pct + '%';
}

function animateConfidenceRing(score) {
  const circ = 2 * Math.PI * 36;         // 226.2
  const fill = (score / 100) * circ;
  const arc  = document.getElementById('conf-arc');
  arc.setAttribute('stroke-dasharray', `${fill.toFixed(1)} ${circ.toFixed(1)}`);
  document.getElementById('conf-pct').textContent    = score + '%';
  document.getElementById('conf-label').textContent  = score >= 70 ? 'High confidence' : score >= 50 ? 'Moderate confidence' : 'Low confidence';
  document.getElementById('conf-label').style.color  = score >= 70 ? 'var(--teal)' : score >= 50 ? 'var(--amber)' : 'var(--red)';
  document.getElementById('conf-risk').textContent   = score >= 70 ? 'High' : score >= 50 ? 'Medium' : 'Low';
  document.getElementById('conf-rec').textContent    = score >= 70 ? 'Auto Remediate' : 'Human Review Required';
}

function showRemediationCard(data) {
  document.getElementById('remediation-placeholder').style.display = 'none';
  document.getElementById('root-cause-box').style.display  = 'block';
  document.getElementById('root-cause-text').textContent   = data.root_cause;
  document.getElementById('actions-label').style.display   = 'block';
  document.getElementById('btn-row').style.display         = 'grid';
  if (data.status !== 'resolved_by_fallback') {
    document.getElementById('auto-badge').style.display    = 'inline';
  }
  // Show RAG source note if fix came from memory
  if (data.rag_count > 0) {
    document.getElementById('rag-source-note').style.display = 'flex';
    document.getElementById('rag-source-text').textContent   =
      `Fix derived from ${data.rag_count} similar past incident${data.rag_count > 1 ? 's' : ''} in memory`;
  }
  // Render actions list
  const list = document.getElementById('actions-list');
  list.innerHTML = '';
  data.suggested_fix.forEach((step, i) => {
    list.innerHTML += `<div class="action-item"><span class="action-num">${i+1}.</span>${step}</div>`;
  });
}

function approveHITL(approved) {
  fetch(`http://localhost:8000/api/incidents/${currentIncidentId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ approved })
  });
  document.getElementById('hitl-panel').style.display = 'none';
  if (!approved) {
    document.getElementById('remediation-placeholder').style.display  = 'block';
    document.getElementById('remediation-placeholder').innerHTML       =
      '<i class="ti ti-x" style="font-size:20px;color:var(--red);display:block;margin-bottom:6px;"></i>Rejected — not written to memory';
  }
}
```

---

## Backend SSE events to emit (update backend/main.py)

The backend must emit these specific step names so the frontend JS switch statement above works:

| SSE step name | When to emit | Key data fields |
|---|---|---|
| `classification` | After monitor agent reads log | `alert_type`, `alert_count`, `timestamp` |
| `rag_retrieval` | After triage agent classifies | `severity`, `category`, `confidence`, `expert` |
| `expert_analysis` | After RAG query + expert starts | `sub_tasks`, `rag_count`, `rag_top_match`, `expert_name` |
| `reflection` | After reflection agent scores | `score`, `critique`, `confidence`, `root_cause`, `proposed_fix_summary` |
| `hitl_required` | If severity <= 2, before executing | `score`, `confidence` |
| `complete` | After full resolution | `root_cause`, `suggested_fix[]`, `confidence`, `status`, `rag_count`, `reflection_score` |

Update `route_incident_streaming()` in `agents/orchestrator.py` to yield dicts with these exact key names.

---

## Phase 8.1 — Backend (unchanged from original plan)

All Phase 8.1 tasks from the original plan remain the same:
- FastAPI app in `backend/main.py`
- Pydantic models in `backend/models.py`
- `POST /api/incidents`, `GET /api/incidents/{id}/stream`, `POST /api/incidents/{id}/approve`, `GET /api/incidents`
- CORS middleware, SSE streaming, asyncio.Event for HITL pause/resume

**Only change:** ensure `route_incident_streaming()` yields dicts with the exact step names and data fields listed in the table above.

---

## Build order for Antigravity

| Step | Build | Checkpoint |
|---|---|---|
| 1 | CSS tokens + body + CDN links | Dark page renders |
| 2 | Header | Title, bell, avatar visible |
| 3 | Section 1 — dropdown + meta bar | Dropdown updates chip and meta bar on change |
| 4 | Section 2 — `renderSteps()` + CSS | 6 step cards in 3×2 grid, all pending/greyed |
| 5 | Section 2 — source tags + output snippets CSS | Tags styled (amber=RAG, teal=LLM, blue=both) |
| 6 | Section 3 — confidence ring + HITL panel | Ring renders at 0%, HITL panel hidden |
| 7 | Section 3 — remediation panel | Placeholder shows, root cause + actions hidden |
| 8 | `runTriaging()` + SSE handler + `updateStepCard()` | Full live flow with step cards animating |
| 9 | `animateConfidenceRing()` + `showRemediationCard()` | Ring fills, remediation card populates |
| 10 | `approveHITL()` | Approve/Reject buttons work for Sev-1/2 |

---

## Running the demo

```bash
# Terminal 1 (from root folder)
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000

# Terminal 2 (from root folder)
python3 -m http.server --directory frontend 5500
# Open: http://localhost:5500
```

### Live demo narration — 5 minutes

1. **Open dashboard** — "This is our incident command center. Six stages, each one an AI agent."
2. **Point at legend** — "See the three tags — RAG means it pulled from memory, LLM means fresh reasoning, RAG+LLM means both."
3. **Select INC-0517, click Run** — "Payment service DB timeout just fired."
4. **Step 1 turns teal** — "Monitor agent read the logs — 32 alerts in 5 minutes, DB timeout detected."
5. **Step 2 turns teal** — "Triage agent scored it Critical, routed to the DB expert."
6. **Step 4 goes amber** — "Now watch Step 4 — it says RAG+LLM. It searched memory first, found 2 similar incidents from April, and now the DB expert is reasoning using that context."
7. **Step 5 goes active** — "Reflection agent checks the proposed fix independently."
8. **Bottom panels populate** — "78% confidence, auto-remediable, four specific steps — and notice the RAG badge on the remediation card, it tells you exactly which past incident the fix came from."
9. **Run Sev-2 incident** — "This one pauses here — HITL gate." Click Approve live.
10. **Close** — "Every step tells you what the agent did and where the intelligence came from."

---

## File structure

```
incident-response-poc/
+-- agents/, tools/, data/, scripts/, tests/  (unchanged)
+-- backend/
|   +-- main.py        (update: emit correct SSE step names)
|   +-- models.py
|   +-- requirements.txt
+-- frontend/
    +-- index.html     (this entire plan builds this file)
    +-- styles.css     (optional: extract CSS here)
```

---

## Quick reference — curriculum mapping

| Section | Week | Pattern |
|---|---|---|
| Step 1 Monitor | Week 1 | Single agent loop |
| Step 2 Triage | Week 1, 3 | Structured output, dynamic routing |
| Step 3 Planning | Week 4 | ReAct / task decomposition |
| Step 4 Expert agents | Week 4, 5 | Multi-agent, RAG memory |
| Step 5 Reflection | Week 3 | Reflection pattern |
| Step 6 Decision | Week 3 | HITL gate |
| RAG source tags | Week 5 | RAG vs LLM transparency |
| Confidence ring | Week 3 | Confidence-gated output |
| Backend SSE | Week 6, 9 | Streaming, API gateway |
