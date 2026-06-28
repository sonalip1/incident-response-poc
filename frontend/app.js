const API_BASE_URL = "http://localhost:8000";

let INCIDENTS = [];

const STEPS = [
  {
    num: 1, id: "monitor",
    name: "Monitor agent", sub: "Log & alert ingestion",
    icon: "ti-activity",
    sourceType: "llm",
    sourceLabel: "Log parsing & anomaly detection",
    outputKeys: ["detected", "alerts", "first_seen"],
    pendingOutput: "scanning logs…"
  },
  {
    num: 2, id: "triage",
    name: "Triage agent", sub: "Classify & prioritize",
    icon: "ti-filter",
    sourceType: "llm",
    sourceLabel: "Severity scoring & routing decision",
    outputKeys: ["severity", "category", "confidence", "route_to"],
    pendingOutput: "classifying incident…"
  },
  {
    num: 3, id: "planning",
    name: "Planning agent", sub: "ReAct decomposition",
    icon: "ti-sitemap",
    sourceType: "llm",
    sourceLabel: "Task decomposition via ReAct",
    outputKeys: ["plan", "tools_needed"],
    pendingOutput: "creating investigation plan…"
  },
  {
    num: 4, id: "expert",
    name: "Expert agents", sub: "Domain investigation",
    icon: "ti-users",
    sourceType: "rag+llm",
    sourceLabel: "Past incidents + new reasoning",
    outputKeys: ["rag_hits", "match", "expert_reasoning"],
    pendingOutput: "retrieving from memory…"
  },
  {
    num: 5, id: "reflection",
    name: "Reflection agent", sub: "Validate & score",
    icon: "ti-shield-check",
    sourceType: "llm",
    sourceLabel: "Self-critique of proposed fix",
    outputKeys: ["score", "critique", "approved"],
    pendingOutput: "awaiting expert output"
  },
  {
    num: 6, id: "decision",
    name: "Decision", sub: "Remediate or escalate",
    icon: "ti-gavel",
    sourceType: "rag+llm",
    sourceLabel: "Final verdict + HITL gate",
    outputKeys: ["action", "hitl_required", "written_to_memory"],
    pendingOutput: "awaiting reflection score"
  }
];

let currentIncidentId = null;
let eventSource = null;
let isBackendConnected = false;
let timer = null;

// Populate dropdown on load
async function populateIncidentsDropdown() {
  const dd = document.getElementById('inc-dd');
  dd.innerHTML = '<option value="" disabled selected>-- Select an incident template --</option>';
  try {
    const r = await fetch(`${API_BASE_URL}/api/incidents/config`);
    if (!r.ok) throw new Error("Failed to load incidents config");
    INCIDENTS = await r.json();
    
    INCIDENTS.forEach((inc, idx) => {
      const opt = document.createElement('option');
      opt.value = idx;
      opt.textContent = inc.id + ' · ' + inc.svc + ' · ' + inc.label.split(' · ').slice(2).join(' · ');
      dd.appendChild(opt);
    });
  } catch (err) {
    console.error("Error loading incidents config:", err);
  }
}

function onSelectIncident() {
  const i = parseInt(document.getElementById('inc-dd').value);
  const inc = INCIDENTS[i];
  if (!inc) return;

  // Update Sev Chip
  const chip = document.getElementById('sev-chip');
  chip.style.display = 'inline-flex';
  chip.style.borderColor = inc.chipBdr;
  chip.style.backgroundColor = inc.chipBg;
  chip.style.color = inc.chipClr;
  chip.innerHTML = `<i class="ti ${inc.chipIco}"></i> ${inc.chip}`;

  // Update Meta Bar
  document.getElementById('meta-sev').textContent = inc.sev;
  document.getElementById('meta-sev').style.color = inc.sevClr;
  document.getElementById('meta-status').textContent = 'Open';
  document.getElementById('meta-status').style.color = 'var(--amber)';
  document.getElementById('meta-src').textContent = inc.src;
  document.getElementById('meta-svc').textContent = inc.svc;
  document.getElementById('meta-created').textContent = inc.ts;
  document.getElementById('meta-assigned').textContent = 'orchestrator_agent';

  // Enable Run Button
  document.getElementById('run-btn').removeAttribute('disabled');

  resetAllSteps();
}

function resetAllSteps() {
  STEPS.forEach(step => updateStepCard(step.id, 'wait', null));
  document.getElementById('progress-fill').style.width = '0%';
  document.getElementById('progress-pct').textContent = '0%';
  document.getElementById('elapsed-time').textContent = '00:00';
  if (timer) clearInterval(timer);

  // Reset confidence and remediation panel
  animateConfidenceRing(0);
  document.getElementById('conf-label').textContent = 'Awaiting analysis';
  document.getElementById('conf-label').style.color = 'var(--text-3)';
  document.getElementById('conf-risk').textContent = '—';
  document.getElementById('conf-rec').textContent = '—';
  document.getElementById('hitl-panel').style.display = 'none';

  document.getElementById('remediation-placeholder').style.display = 'block';
  document.getElementById('remediation-placeholder').innerHTML =
    '<i class="ti ti-dots" style="font-size:20px;display:block;margin-bottom:6px;"></i>Awaiting agent analysis';
  document.getElementById('root-cause-box').style.display = 'none';
  document.getElementById('actions-label').style.display = 'none';
  document.getElementById('actions-list').innerHTML = '';
  document.getElementById('btn-row').style.display = 'none';
  document.getElementById('auto-badge').style.display = 'none';
  document.getElementById('rag-source-note').style.display = 'none';
  
  const fallbackBanner = document.getElementById('fallback-banner');
  if (fallbackBanner) fallbackBanner.style.display = 'none';
}

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

function updateStepCard(stepId, state, outputData) {
  const card = document.getElementById(`step-card-${stepId}`);
  const icon = document.getElementById(`step-icon-${stepId}`);
  const numEl = document.getElementById(`step-num-${stepId}`);
  const badge = document.getElementById(`step-badge-${stepId}`);
  const output = document.getElementById(`step-output-${stepId}`);
  if (!card) return;

  card.className = `step-card ${state}`;
  icon.className = `step-icon ${state}`;
  if (numEl) numEl.className = `step-num ${state}`;

  const badgeMap = { done: 'badge-done', active: 'badge-active', wait: 'badge-wait' };
  const badgeTxt = { done: 'Done', active: 'Active', wait: 'Pending' };
  badge.className = `step-badge ${badgeMap[state]}`;
  badge.textContent = badgeTxt[state];

  if (outputData) {
    output.className = `step-output ${state === 'done' ? 'done-out' : 'active-out'}`;
    output.innerHTML = formatOutput(outputData);
  } else if (state === 'wait') {
    const stepDef = STEPS.find(s => s.id === stepId);
    output.className = 'step-output';
    output.innerHTML = `<span class="out-key">status: </span><span class="out-amber">${stepDef ? stepDef.pendingOutput : 'waiting…'}</span>`;
  }
}

function formatOutput(data) {
  return Object.entries(data).map(([k, v]) => {
    const clsMap = {
      severity: 'out-red', category: 'out-teal', confidence: 'out-teal',
      rag_hits: 'out-amber', match: 'out-amber', score: 'out-teal',
      action: 'out-teal'
    };
    const cls = clsMap[k] || 'out-white';
    return `<span class="out-key">${k}: </span><span class="${cls}">${typeof v === 'object' ? JSON.stringify(v) : v
      }</span>`;
  }).join('<br>');
}

function runTriaging() {
  const val = document.getElementById('inc-dd').value;
  if (val === "") {
    alert("Please select an incident first.");
    return;
  }
  const i = parseInt(val);
  const inc = INCIDENTS[i];

  document.getElementById('run-btn-text').textContent = 'Running...';
  document.getElementById('run-btn').setAttribute('disabled', 'true');
  resetAllSteps();

  fetch(`${API_BASE_URL}/api/incidents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ log_text: inc.label, incident_id: inc.id })
  })
    .then(r => r.json())
    .then(data => {
      currentIncidentId = data.incident_id;
      openSSE(currentIncidentId);
    })
    .catch(err => {
      console.error(err);
      alert("Failed to start incident response session.");
      resetUIControls();
    });
}

function openSSE(id) {
  if (eventSource) eventSource.close();
  eventSource = new EventSource(`${API_BASE_URL}/api/incidents/${id}/stream`);
  let elapsed = 0;
  timer = setInterval(() => {
    elapsed++;
    const m = String(Math.floor(elapsed / 60)).padStart(2, '0');
    const s = String(elapsed % 60).padStart(2, '0');
    document.getElementById('elapsed-time').textContent = `${m}:${s}`;
  }, 1000);

  eventSource.onmessage = (evt) => {
    const payload = JSON.parse(evt.data);

    switch (payload.step) {

      case 'classification':
        updateStepCard('monitor', 'done', {
          detected: payload.data.alert_type,
          alerts: payload.data.alert_count,
          first_seen: payload.data.timestamp
        });
        updateStepCard('triage', 'active', null);
        updateProgressBar(17);
        break;

      case 'rag_retrieval':
        updateStepCard('triage', 'done', {
          severity: payload.data.severity,
          category: payload.data.category,
          confidence: payload.data.confidence,
          route_to: payload.data.expert
        });
        updateStepCard('planning', 'active', null);
        updateProgressBar(34);
        break;

      case 'expert_analysis':
        updateStepCard('planning', 'done', {
          plan: `${payload.data.sub_tasks?.length || 4} sub-tasks`,
          tools: 'search_logs, query_chromadb',
        });
        updateStepCard('expert', 'active', {
          rag_hits: `${payload.data.rag_count} similar incidents found`,
          match: payload.data.rag_top_match || 'retrieving…',
          expert: `${payload.data.expert_name} reasoning…`
        });
        updateProgressBar(57);
        break;

      case 'reflection':
        updateStepCard('expert', 'done', {
          rag_hits: `${payload.data.rag_count} matched`,
          root_cause: payload.data.root_cause,
          proposed: payload.data.proposed_fix_summary,
          past_incidents: payload.data.past_incidents_matched ? payload.data.past_incidents_matched.join('; ') : 'None',
          expert_reasoning: payload.data.expert_reasoning ? payload.data.expert_reasoning.join('; ') : 'None'
        });
        updateStepCard('reflection', 'active', {
          score: `${payload.data.score}/10`,
          critique: payload.data.critique
        });
        updateProgressBar(75);
        animateConfidenceRing(Math.round(payload.data.confidence * 100));
        break;

      case 'hitl_required':
        updateStepCard('reflection', 'done', {
          score: `${payload.data.score}/10`,
          approved: 'awaiting human'
        });
        updateStepCard('decision', 'active', {
          action: 'paused — human approval needed',
          hitl_required: 'true'
        });
        updateProgressBar(90);
        document.getElementById('hitl-panel').style.display = 'block';
        break;

      case 'complete':
        const isRejected = payload.data.status === 'rejected_by_human';
        updateStepCard('reflection', 'done', {
          score: `${payload.data.reflection_score}/10`,
          approved: isRejected ? 'no' : 'yes'
        });
        updateStepCard('decision', 'done', {
          action: isRejected ? 'rejected_by_human' : payload.data.status,
          written_to_memory: isRejected ? 'false' : 'true'
        });
        updateProgressBar(100);
        animateConfidenceRing(Math.round(payload.data.confidence * 100));

        if (isRejected) {
          document.getElementById('remediation-placeholder').style.display = 'block';
          document.getElementById('remediation-placeholder').innerHTML =
            '<i class="ti ti-x" style="font-size:20px;color:var(--red);display:block;margin-bottom:6px;"></i>Rejected — not written to memory';
          document.getElementById('root-cause-box').style.display = 'none';
          document.getElementById('actions-label').style.display = 'none';
          document.getElementById('actions-list').innerHTML = '';
          document.getElementById('btn-row').style.display = 'none';
          document.getElementById('auto-badge').style.display = 'none';
          document.getElementById('rag-source-note').style.display = 'none';
        } else {
          showRemediationCard(payload.data);
        }

        resetUIControls();
        clearInterval(timer);
        eventSource.close();
        loadHistory();
        break;

      case 'error':
        alert(`Pipeline Error: ${payload.data.message}`);
        resetUIControls();
        clearInterval(timer);
        eventSource.close();
        break;
    }
  };
}

function updateProgressBar(pct) {
  document.getElementById('progress-fill').style.width = pct + '%';
  document.getElementById('progress-pct').textContent = pct + '%';
}

function animateConfidenceRing(score) {
  const circ = 2 * Math.PI * 36;
  const fill = (score / 100) * circ;
  const arc = document.getElementById('conf-arc');
  arc.setAttribute('stroke-dasharray', `${fill.toFixed(1)} ${circ.toFixed(1)}`);
  document.getElementById('conf-pct').textContent = score > 0 ? score + '%' : '—';

  if (score === 0) {
    document.getElementById('conf-label').textContent = 'Awaiting analysis';
    document.getElementById('conf-label').style.color = 'var(--text-3)';
    return;
  }

  document.getElementById('conf-label').textContent = score >= 70 ? 'High confidence' : score >= 50 ? 'Moderate confidence' : 'Low confidence';
  document.getElementById('conf-label').style.color = score >= 70 ? 'var(--teal)' : score >= 50 ? 'var(--amber)' : 'var(--red)';
  document.getElementById('conf-risk').textContent = score >= 70 ? 'Low' : score >= 50 ? 'Medium' : 'High';
  document.getElementById('conf-rec').textContent = score >= 70 ? 'Auto Remediate' : 'Human Review Required';
}

function showRemediationCard(data) {
  document.getElementById('remediation-placeholder').style.display = 'none';
  document.getElementById('root-cause-box').style.display = 'block';
  document.getElementById('root-cause-text').textContent = data.root_cause;
  document.getElementById('actions-label').style.display = 'block';
  document.getElementById('btn-row').style.display = 'grid';
  
  const fallbackBanner = document.getElementById('fallback-banner');
  if (data.status === 'resolved_by_fallback') {
    if (fallbackBanner) fallbackBanner.style.display = 'flex';
    document.getElementById('auto-badge').style.display = 'none';
  } else {
    if (fallbackBanner) fallbackBanner.style.display = 'none';
    document.getElementById('auto-badge').style.display = 'inline';
  }
  
  if (data.rag_count > 0) {
    document.getElementById('rag-source-note').style.display = 'flex';
    document.getElementById('rag-source-text').textContent =
      `Fix derived from ${data.rag_count} similar past incident${data.rag_count > 1 ? 's' : ''} in memory`;
  } else {
    document.getElementById('rag-source-note').style.display = 'none';
  }
  const list = document.getElementById('actions-list');
  list.innerHTML = '';
  data.suggested_fix.forEach((step, i) => {
    list.innerHTML += `<div class="action-item"><span class="action-num">${i + 1}.</span>${step}</div>`;
  });
}

function approveHITL(approved) {
  fetch(`${API_BASE_URL}/api/incidents/${currentIncidentId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ approved })
  })
    .then(() => {
      document.getElementById('hitl-panel').style.display = 'none';
      if (!approved) {
        document.getElementById('remediation-placeholder').style.display = 'block';
        document.getElementById('remediation-placeholder').innerHTML =
          '<i class="ti ti-x" style="font-size:20px;color:var(--red);display:block;margin-bottom:6px;"></i>Rejected — not written to memory';
      }
    })
    .catch(err => {
      console.error(err);
      alert("Failed to send HITL approval response.");
    });
}

function resetUIControls() {
  document.getElementById('run-btn-text').textContent = 'Run incident triaging';
  document.getElementById('run-btn').removeAttribute('disabled');
}

async function loadHistory() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/incidents`);
    if (!response.ok) return;

    const data = await response.json();
    const historyStrip = document.getElementById("historyStrip");
    historyStrip.innerHTML = "";
    if (data.length === 0) {
      historyStrip.innerHTML = '<div style="color:var(--text-3); font-style:italic;">No incidents processed in this session yet.</div>';
      return;
    }

    data.forEach(inc => {
      const card = document.createElement("div");
      card.className = "history-card";

      const badgeClass = inc.status === "resolved_by_expert" ? "sev-teal" : (inc.status === "resolved_by_fallback" ? "sev-amber" : "sev-red");
      const handlerLabel = inc.status === "resolved_by_fallback" ? "Fallback (SRE)" : (inc.status === "rejected_by_human" ? "Rejected" : "Expert Agent");

      card.innerHTML = `
        <div class="history-card-header">
          <span class="history-sev ${badgeClass}">${inc.status.replace(/_/g, ' ').toUpperCase()}</span>
          <span class="history-handler">${handlerLabel}</span>
        </div>
        <div class="history-cause">${inc.root_cause || "System Triage"}</div>
        <div class="history-meta">
          <span>Confidence: ${Math.round(inc.confidence * 100)}%</span>
        </div>
      `;

      historyStrip.appendChild(card);
    });
  } catch (err) {
    console.error("Error loading triage history:", err);
  }
}

// Health Check
async function checkBackendConnection() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/incidents`);
    if (response.ok) {
      setConnectionState(true, "System Online");
    } else {
      setConnectionState(false, "System Offline (Server Error)");
    }
  } catch (error) {
    setConnectionState(false, "System Offline (Unable to Connect)");
  }
}

function setConnectionState(connected, text) {
  isBackendConnected = connected;
  const statusText = document.getElementById("statusText");
  const statusDot = document.getElementById("statusDot");
  statusText.innerText = text;
  if (connected) {
    statusDot.classList.add("connected");
  } else {
    statusDot.classList.remove("connected");
  }
}

window.addEventListener('DOMContentLoaded', () => {
  renderSteps();
  populateIncidentsDropdown();
  checkBackendConnection();
  loadHistory();
  setInterval(checkBackendConnection, 15000);
});
