const API_BASE_URL = "http://127.0.0.1:8000";

// Hardcoded log templates
const LOG_TEMPLATES = {
    database: `# ── DB INCIDENT ─────────────────────────────────────────────────────────
2025-05-10 02:14:31 INFO  payment-service    Connecting to postgres://db-primary:5432/payments
2025-05-10 02:14:31 WARN  payment-service    Connection pool at 95% capacity (19/20 connections used)
2025-05-10 02:14:33 ERROR payment-service    DB connection timeout after 30000ms
2025-05-10 02:14:33 ERROR payment-service    Retry 1/3 failed: connection refused
2025-05-10 02:14:39 ERROR payment-service    Retry 3/3 failed: connection refused
2025-05-10 02:14:40 ERROR payment-service    Unhandled exception: PSQLException: too many connections
2025-05-10 02:14:40 INFO  alertmanager       PagerDuty alert fired: payment-service-db-down SEV3`,

    network: `# ── NETWORK INCIDENT ─────────────────────────────────────────────────────
2025-05-10 03:41:02 INFO  api-gateway        Routing POST /api/auth/login to auth-service:8080
2025-05-10 03:41:02 WARN  api-gateway        DNS resolution for auth-service.internal: 2800ms (threshold: 500ms)
2025-05-10 03:41:07 ERROR api-gateway        DNS resolution failed: NXDOMAIN for auth-service.internal
2025-05-10 03:41:07 ERROR api-gateway        Circuit breaker OPEN for auth-service after 5 consecutive failures
2025-05-10 03:41:09 ERROR api-gateway        All auth backends unreachable. Returning 503 to client.
2025-05-10 03:41:10 INFO  alertmanager       PagerDuty alert fired: auth-service-unreachable SEV2`,

    application: `# ── APPLICATION INCIDENT ─────────────────────────────────────────────────
2025-05-10 05:22:10 INFO  order-service      Processing batch job: daily-reconciliation (12,450 orders)
2025-05-10 05:22:45 WARN  order-service      GC pause: 4200ms (Full GC triggered). Heap: 94% (7.5GB / 8GB)
2025-05-10 05:22:46 ERROR order-service      OutOfMemoryError: Java heap space
2025-05-10 05:22:46 ERROR order-service      Thread pool exhausted: 0/200 threads available
2025-05-10 05:22:46 ERROR order-service      FATAL: Application crash. Exit code 137 (OOM Kill)
2025-05-10 05:22:47 INFO  kubernetes         Pod order-service-7d8f9b-xk2p9 restarted (CrashLoopBackOff)
2025-05-10 05:22:48 INFO  alertmanager       PagerDuty alert fired: order-service-crash-loop SEV2`,

    ambiguous: `# ── AMBIGUOUS (tests graceful degradation later) ──────────────────────────
2025-05-10 06:55:01 WARN  data-pipeline      Checkpoint file missing: /data/checkpoints/etl-run-20250510.ckpt
2025-05-10 06:55:01 WARN  data-pipeline      Falling back to full reprocess (estimated 45 min delay)
2025-05-10 06:55:03 ERROR data-pipeline      Source schema mismatch: expected 24 columns, got 27
2025-05-10 06:55:03 ERROR data-pipeline      Pipeline halted. Manual intervention required.
2025-05-10 06:55:04 INFO  alertmanager       PagerDuty alert fired: etl-pipeline-halted SEV4`
};

// DOM References
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const sampleLogsSelect = document.getElementById("sampleLogs");
const logTextarea = document.getElementById("logText");
const runBtn = document.getElementById("runBtn");
const traceLogs = document.getElementById("traceLogs");

// Results Card DOM References
const resultPlaceholder = document.getElementById("resultPlaceholder");
const incidentCard = document.getElementById("incidentCard");
const cardSevBadge = document.getElementById("cardSevBadge");
const cardServiceTag = document.getElementById("cardServiceTag");
const cardHandlerTag = document.getElementById("cardHandlerTag");
const cardRootCause = document.getElementById("cardRootCause");
const confidenceRingBar = document.getElementById("confidenceRingBar");
const cardConfidenceText = document.getElementById("cardConfidenceText");
const cardFixSteps = document.getElementById("cardFixSteps");
const hitlPanel = document.getElementById("hitlPanel");
const approveBtn = document.getElementById("approveBtn");
const rejectBtn = document.getElementById("rejectBtn");
const toggleRawBtn = document.getElementById("toggleRawBtn");
const rawTraceLogs = document.getElementById("rawTraceLogs");
const historyStrip = document.getElementById("historyStrip");

let isBackendConnected = false;
let currentEventSource = null;
let activeIncidentId = null;
let currentTraceEvents = [];
let pastIncidents = [];

// 1. Connection check / health polling
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
    statusText.innerText = text;
    if (connected) {
        statusDot.classList.add("connected");
        if (runBtn.innerText === "Run Incident Response") {
            runBtn.removeAttribute("disabled");
        }
    } else {
        statusDot.classList.remove("connected");
        runBtn.setAttribute("disabled", "true");
    }
}

// 2. Select dropdown event listener
sampleLogsSelect.addEventListener("change", (e) => {
    const selectedTemplate = e.target.value;
    if (LOG_TEMPLATES[selectedTemplate]) {
        logTextarea.value = LOG_TEMPLATES[selectedTemplate];
    }
});

// Trace rendering helpers
function appendTraceLine(text, cssClass) {
    const lineEl = document.createElement("div");
    lineEl.className = `trace-line ${cssClass}`;
    lineEl.textContent = text;
    traceLogs.appendChild(lineEl);
    traceLogs.scrollTop = traceLogs.scrollHeight;
    return lineEl;
}

function typewriterTraceLine(text, cssClass, speed = 15) {
    const lineEl = document.createElement("div");
    lineEl.className = `trace-line ${cssClass}`;
    traceLogs.appendChild(lineEl);
    
    lineEl.style.animation = "none";
    lineEl.style.opacity = 1;
    lineEl.style.transform = "none";
    
    let charIdx = 0;
    return new Promise((resolve) => {
        function nextChar() {
            if (charIdx < text.length) {
                lineEl.textContent += text.charAt(charIdx);
                charIdx++;
                traceLogs.scrollTop = traceLogs.scrollHeight;
                setTimeout(nextChar, speed);
            } else {
                resolve(lineEl);
            }
        }
        nextChar();
    });
}

// Result Card Rendering helpers
function updateConfidenceRing(percent) {
    const r = 34;
    const circ = 2 * Math.PI * r;
    const offset = circ - (percent / 100) * circ;
    confidenceRingBar.style.strokeDashoffset = offset;
    cardConfidenceText.innerText = `${percent}%`;
}

function formatCodeSnippets(text) {
    return text.replace(/`([^`]+)`/g, '<code>$1</code>');
}

function parseServiceFromLog(logText) {
    const match = logText.match(/(?:INFO|WARN|ERROR)\s+([a-zA-Z0-9_-]+)/);
    return match ? match[1] : "system-service";
}

// Toggle Raw JSON panel
toggleRawBtn.addEventListener("click", () => {
    if (rawTraceLogs.classList.contains("hidden")) {
        rawTraceLogs.classList.remove("hidden");
        toggleRawBtn.innerText = "Hide raw agent trace";
    } else {
        rawTraceLogs.classList.add("hidden");
        toggleRawBtn.innerText = "View raw agent trace";
    }
});

// 3. HITL approval callback
async function handleHitlDecision(approved) {
    if (!activeIncidentId) return;
    
    approveBtn.setAttribute("disabled", "true");
    rejectBtn.setAttribute("disabled", "true");
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/incidents/${activeIncidentId}/approve`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ approved: approved })
        });
        
        if (!response.ok) {
            throw new Error(`Failed to send approval status: ${response.status}`);
        }
        
        hitlPanel.classList.add("hidden");
        incidentCard.classList.remove("awaiting-approval");
        
        if (approved) {
            appendTraceLine("👤 [HITL] Operator APPROVED the resolution plan. Resuming...", "trace-system-complete");
        } else {
            appendTraceLine("👤 [HITL] Operator REJECTED the resolution plan. Terminating pipeline.", "trace-error");
            cardHandlerTag.innerText += " (Rejected by operator)";
            resetUIControls();
        }
        
        // Refresh session history to show updated status
        await loadHistory();
    } catch (err) {
        console.error("Error sending HITL action:", err);
        alert(`Error: ${err.message}`);
        approveBtn.removeAttribute("disabled");
        rejectBtn.removeAttribute("disabled");
    }
}

approveBtn.addEventListener("click", () => handleHitlDecision(true));
rejectBtn.addEventListener("click", () => handleHitlDecision(false));

// 4. Dispatch run request and connect to stream
async function runIncidentResponse() {
    const logContent = logTextarea.value.trim();
    if (!logContent) {
        alert("Please paste or select log data first.");
        return;
    }
    
    if (currentEventSource) {
        currentEventSource.close();
    }
    
    runBtn.setAttribute("disabled", "true");
    runBtn.innerText = "Triggering Pipeline...";
    sampleLogsSelect.setAttribute("disabled", "true");
    logTextarea.setAttribute("disabled", "true");
    
    traceLogs.innerHTML = "";
    appendTraceLine("⚡ Initializing incident response pipeline...", "trace-memory");
    
    resultPlaceholder.classList.remove("hidden");
    incidentCard.classList.add("hidden");
    incidentCard.classList.remove("pop-effect", "awaiting-approval");
    hitlPanel.classList.add("hidden");
    rawTraceLogs.classList.add("hidden");
    rawTraceLogs.textContent = "";
    toggleRawBtn.innerText = "View raw agent trace";
    
    approveBtn.removeAttribute("disabled");
    rejectBtn.removeAttribute("disabled");
    
    currentTraceEvents = [];
    activeIncidentId = null;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/incidents`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ log_text: logContent })
        });
        
        if (!response.ok) {
            throw new Error(`Server returned status: ${response.status}`);
        }
        
        const data = await response.json();
        activeIncidentId = data.incident_id;
        appendTraceLine(`🛰️ Session established: ${activeIncidentId}`, "trace-memory");
        
        currentEventSource = new EventSource(`${API_BASE_URL}/api/incidents/${activeIncidentId}/stream`);
        
        currentEventSource.onmessage = async (e) => {
            const eventData = JSON.parse(e.data);
            const { step, data: payload } = eventData;
            
            currentTraceEvents.push(eventData);
            rawTraceLogs.textContent = JSON.stringify(currentTraceEvents, null, 2);
            
            if (step === "classification") {
                const pct = Math.round(payload.confidence * 100);
                appendTraceLine(
                    `[CLASSIFIER] Severity: SEV-${payload.severity} | Category: ${payload.category.toUpperCase()} | Confidence: ${pct}%`,
                    "trace-classifier"
                );
                
                resultPlaceholder.classList.add("hidden");
                incidentCard.classList.remove("hidden");
                incidentCard.classList.add("pop-effect");
                
                cardSevBadge.className = "sev-badge";
                if (payload.severity <= 2) {
                    cardSevBadge.classList.add("sev-red");
                } else if (payload.severity === 3) {
                    cardSevBadge.classList.add("sev-amber");
                } else {
                    cardSevBadge.classList.add("sev-teal");
                }
                cardSevBadge.innerText = `SEV-${payload.severity}`;
                cardServiceTag.innerText = parseServiceFromLog(logContent);
                cardHandlerTag.innerText = "triage_classifier";
                cardRootCause.innerText = payload.root_cause;
                updateConfidenceRing(0);
                cardFixSteps.innerHTML = '<li class="placeholder-text">Analyzing logs, retrieving historical resolutions...</li>';
            } 
            else if (step === "rag_retrieval") {
                const count = payload.incidents ? payload.incidents.length : 0;
                appendTraceLine(
                    `[MEMORY] Found ${count} similar past incidents in history.`,
                    "trace-memory"
                );
                if (count > 0) {
                    payload.incidents.forEach(inc => {
                        appendTraceLine(`  👉 "${inc}"`, "trace-memory");
                    });
                }
            } 
            else if (step === "expert_analysis") {
                const expert = payload.expert_handler.toUpperCase();
                const attemptStr = payload.attempt ? ` (Attempt ${payload.attempt})` : "";
                
                const thoughtText = `[${expert}]${attemptStr} Thought: "Detected ${payload.analysis.root_cause || 'root cause'}"`;
                await typewriterTraceLine(thoughtText, "trace-expert-thought");
                
                appendTraceLine(`[${expert}] -> Proposed fix steps:`, "trace-expert-action");
                payload.analysis.suggested_fix.forEach((stepItem, sIdx) => {
                    appendTraceLine(`  ${sIdx + 1}. ${stepItem}`, "trace-expert-action");
                });
                
                cardHandlerTag.innerText = payload.expert_handler;
                cardRootCause.innerText = payload.analysis.root_cause || cardRootCause.innerText;
                cardFixSteps.innerHTML = "";
                payload.analysis.suggested_fix.forEach(stepItem => {
                    const li = document.createElement("li");
                    li.innerHTML = formatCodeSnippets(stepItem);
                    cardFixSteps.appendChild(li);
                });
                
                const pct = Math.round(payload.analysis.confidence * 100);
                updateConfidenceRing(pct);
            } 
            else if (step === "reflection") {
                const score = payload.attempt_1_score || payload.final_score || 0;
                const scoreStr = payload.final_score !== undefined ? `Attempt 1: ${payload.attempt_1_score}/10 -> Revised: ${payload.final_score}/10` : `${score}/10`;
                const critique = payload.final_critique || payload.critique || "";
                
                const reflectionText = `[REFLECTOR] Review score: ${scoreStr} — "${critique}"`;
                const cssClass = score < 6 ? "trace-reflector-bad" : "trace-reflector-good";
                appendTraceLine(reflectionText, cssClass);
            } 
            else if (step === "hitl_required") {
                const classificationInfo = payload.classification || {};
                appendTraceLine(
                    `[SYSTEM] Incident severity Sev-${classificationInfo.severity || 2} — Human approval gate REQUIRED to proceed.`,
                    "trace-system-hitl"
                );
                
                incidentCard.classList.add("awaiting-approval");
                hitlPanel.classList.remove("hidden");
            } 
            else if (step === "complete") {
                if (payload.status === "rejected_by_human") {
                    appendTraceLine(
                        `[SYSTEM] Incident closed. Resolution plan was rejected by operator. Memory write-back skipped.`,
                        "trace-error"
                    );
                    cardHandlerTag.innerText = `${payload.expert_handler} (rejected)`;
                } else {
                    appendTraceLine(
                        `[SYSTEM] Incident resolved successfully. Diagnosis and actions written back to database memory.`,
                        "trace-system-complete"
                    );
                    cardHandlerTag.innerText = `${payload.expert_handler} (resolved)`;
                }
                
                incidentCard.classList.remove("awaiting-approval");
                hitlPanel.classList.add("hidden");
                
                currentEventSource.close();
                currentEventSource = null;
                resetUIControls();
                
                // Refresh history list
                await loadHistory();
            }
            else if (step === "error") {
                appendTraceLine(`[ERROR] Pipeline run aborted: ${payload.message}`, "trace-error");
                incidentCard.classList.remove("awaiting-approval");
                hitlPanel.classList.add("hidden");
                currentEventSource.close();
                currentEventSource = null;
                resetUIControls();
            }
        };
        
        currentEventSource.onerror = (err) => {
            console.error("SSE Connection error:", err);
            appendTraceLine("⚠️ Connection closed or disconnected from streaming endpoint.", "trace-error");
            if (currentEventSource) {
                currentEventSource.close();
                currentEventSource = null;
            }
            resetUIControls();
        };
        
    } catch (err) {
        console.error("[API ERROR] Failed to dispatch incident:", err);
        appendTraceLine(`❌ Trigger Failed: ${err.message}`, "trace-error");
        resetUIControls();
    }
}

// 5. Load history of last 10 incidents from backend API
async function loadHistory() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/incidents`);
        if (!response.ok) return;
        
        const data = await response.json();
        pastIncidents = data;
        
        historyStrip.innerHTML = "";
        if (data.length === 0) {
            historyStrip.innerHTML = '<div class="placeholder-text">No incidents processed in this session yet.</div>';
            return;
        }
        
        data.forEach(inc => {
            const card = document.createElement("div");
            card.className = "history-card";
            
            // Dotted border if fallback resolved
            if (inc.status === "resolved_by_fallback") {
                card.classList.add("fallback-resolved");
            }
            
            const badgeClass = inc.classification.severity <= 2 ? "sev-red" : (inc.classification.severity === 3 ? "sev-amber" : "sev-teal");
            const handlerLabel = inc.expert_handler === "generic_handler" ? "Fallback (SRE)" : inc.expert_handler;
            
            card.innerHTML = `
                <div class="history-card-header">
                    <span class="history-sev ${badgeClass}">SEV-${inc.classification.severity}</span>
                    <span class="history-handler">${handlerLabel}</span>
                </div>
                <div class="history-cause">${inc.analysis.root_cause || "System Triage"}</div>
                <div class="history-meta">
                    <span class="history-service">${parseServiceFromLog(inc.log_text)}</span>
                    <span>Confidence: ${Math.round(inc.analysis.confidence * 100)}%</span>
                </div>
            `;
            
            card.addEventListener("click", () => showPastIncidentDetails(inc));
            historyStrip.appendChild(card);
        });
    } catch (err) {
        console.error("Error loading triage history:", err);
    }
}

// Show details of a historical incident in read-only mode
function showPastIncidentDetails(inc) {
    resultPlaceholder.classList.add("hidden");
    incidentCard.classList.remove("hidden");
    incidentCard.classList.remove("pop-effect", "awaiting-approval");
    hitlPanel.classList.add("hidden");
    rawTraceLogs.classList.add("hidden");
    toggleRawBtn.innerText = "View raw agent trace";
    
    cardSevBadge.className = "sev-badge";
    if (inc.classification.severity <= 2) {
        cardSevBadge.classList.add("sev-red");
    } else if (inc.classification.severity === 3) {
        cardSevBadge.classList.add("sev-amber");
    } else {
        cardSevBadge.classList.add("sev-teal");
    }
    cardSevBadge.innerText = `SEV-${inc.classification.severity}`;
    cardServiceTag.innerText = parseServiceFromLog(inc.log_text);
    
    const handlerLabel = inc.status === "resolved_by_fallback" ? `${inc.expert_handler} (fallback resolved)` : `${inc.expert_handler} (resolved)`;
    cardHandlerTag.innerText = handlerLabel;
    
    cardRootCause.innerText = inc.analysis.root_cause || "Triage completed.";
    
    cardFixSteps.innerHTML = "";
    inc.analysis.suggested_fix.forEach(stepItem => {
        const li = document.createElement("li");
        li.innerHTML = formatCodeSnippets(stepItem);
        cardFixSteps.appendChild(li);
    });
    
    const pct = Math.round(inc.analysis.confidence * 100);
    updateConfidenceRing(pct);
    
    rawTraceLogs.textContent = JSON.stringify(inc, null, 2);
}

function resetUIControls() {
    if (isBackendConnected) {
        runBtn.removeAttribute("disabled");
    }
    runBtn.innerText = "Run Incident Response";
    sampleLogsSelect.removeAttribute("disabled");
    logTextarea.removeAttribute("disabled");
}

runBtn.addEventListener("click", runIncidentResponse);

// Start connection polling and history fetching immediately
checkBackendConnection();
loadHistory();
setInterval(checkBackendConnection, 20000);
