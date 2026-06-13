# Incident Response Agentic AI System — Implementation Plan

**Target IDE:** Google Antigravity (Plan mode)
**Audience:** Beginner in Agentic AI
**Goal:** Working prototype + demo in ~2 weeks (4 build days, evening pace)
**Architecture reference:** Monitor agent → Triage/Orchestrator → 3 Expert agents (DB/Network/App) → Graceful degradation → Reflection → HITL gate → Memory write-back

---

## How to use this file in Antigravity

1. Create a new project folder, e.g. `incident-response-poc/`.
2. Open Antigravity, point it at this folder.
3. Paste this entire file into the Antigravity **Manager/Agent chat** and say:
   > "Read this plan. Work through Phase 0 first. After each phase, pause, show me the output, and wait for my go-ahead before continuing."
4. Antigravity will generate a **Plan Artifact** — review it, then let the agent execute phase by phase.
5. Keep this file in the repo as `PLAN.md` — Antigravity's agents will refer back to it across sessions.

**Important for beginners:** Do NOT ask Antigravity to "build the whole thing" in one go. Go phase by phase. Each phase ends with something you can run and see working. If a phase fails, fix it before moving on — don't let errors compound.

---

## Phase 0 — Environment Setup (30–45 min)

### Goal
Get a Python environment running with one working LLM call, using whichever provider you choose.

### Tasks for Antigravity agent
- [ ] Create `incident-response-poc/` with subfolders: `agents/`, `data/`, `tools/`, `tests/`
- [ ] Create `requirements.txt` with: `python-dotenv`, `chromadb`, and ONE of the LLM SDKs below (pick based on your choice in step 2)
- [ ] Create `.env.example` with placeholder API key names
- [ ] Create `.gitignore` (must include `.env`, `__pycache__/`, `chroma_db/`)
- [ ] Create `config.py` — a single place that reads the LLM provider choice and API key from `.env`

### Choose your LLM provider (pick ONE to start)

| Provider | Free tier? | SDK package | Env var name | Model name to use |
|---|---|---|---|---|
| **Google Gemini Flash** (recommended — also native in Antigravity) | Yes, 1500 req/day | `google-generativeai` | `GEMINI_API_KEY` | `gemini-2.0-flash` |
| **Groq (Llama 3.3)** | Yes, generous | `groq` | `GROQ_API_KEY` | `llama-3.3-70b-versatile` |
| **Anthropic Claude** | No, ~$5 credit needed | `anthropic` | `ANTHROPIC_API_KEY` | `claude-sonnet-4-6` |

> **Tip:** Since Antigravity is built on Gemini, Gemini Flash is the smoothest path — you can get an API key directly from Google AI Studio in under 2 minutes. Start here, switch later if you want.

### `config.py` — provider-agnostic LLM wrapper

Ask Antigravity to generate this exact pattern (this is the most important file in the whole project — every agent calls through it):

```python
import os
from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.getenv("LLM_PROVIDER", "gemini")  # "gemini" | "groq" | "anthropic"

def call_llm(prompt: str, system: str = "", max_tokens: int = 1024) -> str:
    """Single entry point for all LLM calls. Swap provider via .env, nothing else changes."""

    if PROVIDER == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel("gemini-2.0-flash", system_instruction=system)
        response = model.generate_content(prompt)
        return response.text

    elif PROVIDER == "groq":
        from groq import Groq
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    elif PROVIDER == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {PROVIDER}")
```

### `.env` (you create this yourself, locally — never commit it)

```
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
```

### Phase 0 — Demo checkpoint
Run a tiny test script:
```python
from config import call_llm
print(call_llm("Say hello and confirm you are working.", system="You are a helpful assistant."))
```
**You should see a response printed.** If this works, you're ready for Phase 1. If it fails, fix the API key / provider before moving on — don't proceed with a broken foundation.

---

## Phase 1 — Single Agent: The Log Analyzer (Day 1, ~2–3 hrs)

### Goal
One agent that reads a log and returns structured JSON: severity, category, root cause, confidence.

### Concepts covered
`Single agent loop` · `Tool use (basic)` · `Structured output`

### Tasks for Antigravity agent
- [ ] Create `data/sample_logs.txt` with 4 log blocks (DB, Network, App, Ambiguous) — use the sample logs below
- [ ] Create `agents/classifier.py` with a function `classify_log(log_text: str) -> dict`
- [ ] The function calls `call_llm()` with a prompt that returns ONLY valid JSON: `{"severity": 1-5, "category": "database|network|application|unknown", "root_cause": "...", "confidence": 0.0-1.0}`
- [ ] Add JSON parsing with error handling (LLMs sometimes wrap JSON in markdown — strip ```json fences)
- [ ] Create `tests/test_classifier.py` — runs `classify_log()` on all 4 sample logs and prints results

### Sample log data (`data/sample_logs.txt`)

```
# ── DB INCIDENT ─────────────────────────────────────────────────────────
2025-05-10 02:14:31 INFO  payment-service    Connecting to postgres://db-primary:5432/payments
2025-05-10 02:14:31 WARN  payment-service    Connection pool at 95% capacity (19/20 connections used)
2025-05-10 02:14:33 ERROR payment-service    DB connection timeout after 30000ms
2025-05-10 02:14:33 ERROR payment-service    Retry 1/3 failed: connection refused
2025-05-10 02:14:39 ERROR payment-service    Retry 3/3 failed: connection refused
2025-05-10 02:14:40 ERROR payment-service    Unhandled exception: PSQLException: too many connections
2025-05-10 02:14:40 INFO  alertmanager       PagerDuty alert fired: payment-service-db-down SEV3

# ── NETWORK INCIDENT ─────────────────────────────────────────────────────
2025-05-10 03:41:02 INFO  api-gateway        Routing POST /api/auth/login to auth-service:8080
2025-05-10 03:41:02 WARN  api-gateway        DNS resolution for auth-service.internal: 2800ms (threshold: 500ms)
2025-05-10 03:41:07 ERROR api-gateway        DNS resolution failed: NXDOMAIN for auth-service.internal
2025-05-10 03:41:07 ERROR api-gateway        Circuit breaker OPEN for auth-service after 5 consecutive failures
2025-05-10 03:41:09 ERROR api-gateway        All auth backends unreachable. Returning 503 to client.
2025-05-10 03:41:10 INFO  alertmanager       PagerDuty alert fired: auth-service-unreachable SEV2

# ── APPLICATION INCIDENT ─────────────────────────────────────────────────
2025-05-10 05:22:10 INFO  order-service      Processing batch job: daily-reconciliation (12,450 orders)
2025-05-10 05:22:45 WARN  order-service      GC pause: 4200ms (Full GC triggered). Heap: 94% (7.5GB / 8GB)
2025-05-10 05:22:46 ERROR order-service      OutOfMemoryError: Java heap space
2025-05-10 05:22:46 ERROR order-service      Thread pool exhausted: 0/200 threads available
2025-05-10 05:22:46 ERROR order-service      FATAL: Application crash. Exit code 137 (OOM Kill)
2025-05-10 05:22:47 INFO  kubernetes         Pod order-service-7d8f9b-xk2p9 restarted (CrashLoopBackOff)
2025-05-10 05:22:48 INFO  alertmanager       PagerDuty alert fired: order-service-crash-loop SEV2

# ── AMBIGUOUS (tests graceful degradation later) ──────────────────────────
2025-05-10 06:55:01 WARN  data-pipeline      Checkpoint file missing: /data/checkpoints/etl-run-20250510.ckpt
2025-05-10 06:55:01 WARN  data-pipeline      Falling back to full reprocess (estimated 45 min delay)
2025-05-10 06:55:03 ERROR data-pipeline      Source schema mismatch: expected 24 columns, got 27
2025-05-10 06:55:03 ERROR data-pipeline      Pipeline halted. Manual intervention required.
2025-05-10 06:55:04 INFO  alertmanager       PagerDuty alert fired: etl-pipeline-halted SEV4
```

### Phase 1 — Demo checkpoint
Run `tests/test_classifier.py`. You should see 4 JSON outputs printed — one per log block, each with a severity, category, root cause, and confidence score. The ambiguous block should have a lower confidence score than the others (this matters for Phase 4).

---

## Phase 2 — Orchestrator + Dynamic Routing (Day 1–2, ~2–3 hrs)

### Goal
A triage agent that takes the classifier's output and routes the log to one of three expert agents.

### Concepts covered
`Orchestrator pattern` · `Dynamic routing` · `Multi-agent system`

### Tasks for Antigravity agent
- [ ] Create `agents/db_expert.py`, `agents/network_expert.py`, `agents/app_expert.py` — each has one function `analyze(log_text: str, classification: dict) -> dict`
- [ ] Each expert's prompt is role-locked (e.g. DB expert system prompt: "You are a senior database engineer. Focus on connection pools, locks, replication, queries.")
- [ ] Each expert returns: `{"severity": int, "owner_team": str, "suggested_fix": [list of steps], "confidence": float}`
- [ ] Create `agents/orchestrator.py` with function `route_incident(log_text: str) -> dict`:
  - Calls `classify_log()` first
  - Based on `category`, calls the matching expert
  - If category is `"unknown"`, calls a `generic_handler()` (build this now — it's also your Phase 4 fallback)
- [ ] Create `agents/generic_handler.py` — a simple fallback agent with NO role-lock, just "analyze this log and suggest next steps generically"
- [ ] Update `tests/test_orchestrator.py` to run all 4 sample logs through `route_incident()`

### Phase 2 — Demo checkpoint
Run `tests/test_orchestrator.py`. The DB log should route to `db_expert`, the network log to `network_expert`, the app log to `app_expert`, and the ambiguous pipeline log to `generic_handler`. Print which expert handled each log — this routing decision is your first real "agentic" behavior.

---

## Phase 3 — RAG Memory with ChromaDB (Day 2–3, ~3–4 hrs)

### Goal
Each expert agent retrieves similar past incidents before suggesting a fix.

### Concepts covered
`RAG memory` · `Episodic memory` · `Vector search`

### Tasks for Antigravity agent
- [ ] Create `data/seed_incidents.json` — 6–8 fake past incidents with `text` and `metadata.category` fields (use the examples below)
- [ ] Create `tools/memory.py` with:
  - `init_memory()` — creates a persistent ChromaDB collection at `./chroma_db/`
  - `seed_memory()` — loads `seed_incidents.json` into the collection (run once)
  - `get_similar_incidents(log_text: str, n: int = 3) -> list[str]`
  - `save_resolution(log_text: str, resolution: dict)` — writes a new resolved incident back (used in Phase 5)
- [ ] Update each expert agent (`db_expert.py`, `network_expert.py`, `app_expert.py`) to call `get_similar_incidents()` BEFORE calling the LLM, and inject the results into the prompt as: `"Here are similar past incidents and how they were resolved: {results}"`
- [ ] Create `scripts/seed_db.py` — a one-time script to populate ChromaDB

### `data/seed_incidents.json` — starter content

```json
[
  {"id": "inc_001", "category": "database", "text": "payment-service DB connection timeout. Cause: PgBouncer pool exhausted (20/20). Fix: restarted PgBouncer pool, resolved in 8 min. Root cause was a batch job leaking connections."},
  {"id": "inc_002", "category": "database", "text": "order-service slow queries during peak hours. Cause: missing index on orders.created_at. Fix: added composite index, query time dropped from 4s to 80ms."},
  {"id": "inc_003", "category": "network", "text": "auth-service DNS resolution failures. Cause: Route53 health check misconfigured, marked healthy targets as unhealthy. Fix: corrected health check path from /health to /healthz."},
  {"id": "inc_004", "category": "network", "text": "Intermittent 503s from api-gateway to user-service. Cause: connection pool to upstream too small under load. Fix: increased keepalive connections from 10 to 50."},
  {"id": "inc_005", "category": "application", "text": "order-service OOM crash during batch job. Cause: large result set loaded fully into memory instead of streaming. Fix: switched to cursor-based pagination, memory usage dropped 90%."},
  {"id": "inc_006", "category": "application", "text": "notification-service CrashLoopBackOff after deploy. Cause: missing environment variable for SMTP config introduced in new release. Fix: added env var to deployment manifest, rolled forward."}
]
```

### Phase 3 — Demo checkpoint
Run `scripts/seed_db.py` once. Then re-run `tests/test_orchestrator.py`. The DB expert's output for the payment-service log should now reference `inc_001` (PgBouncer fix) in its suggested fix — because it's semantically similar. **This is the moment the system starts feeling "smart."**

---

## Phase 4 — Graceful Degradation + Circuit Breaker (Day 3, ~2 hrs)

### Goal
The system never crashes outright — if an expert agent fails or returns low confidence, it falls back gracefully.

### Concepts covered
`Graceful degradation` · `Circuit breaker pattern` · `Error handling`

### Tasks for Antigravity agent
- [ ] Wrap each expert call in `orchestrator.py` with `try/except`
- [ ] If an expert call raises an exception OR returns `confidence < 0.5`, fall back to `generic_handler()`
- [ ] Add a `status` field to every output: `"resolved_by_expert"`, `"resolved_by_fallback"`, or `"failed"`
- [ ] Add basic retry logic (max 2 retries) using the `tenacity` library for transient LLM API errors
- [ ] Create `tests/test_degradation.py` — deliberately pass a malformed/empty log to test the fallback path

### Phase 4 — Demo checkpoint
Run `tests/test_degradation.py` with an empty string and with a nonsense log. Both should return a valid `dict` with `status: "resolved_by_fallback"` — NOT crash with an unhandled exception. This proves the system degrades gracefully under bad input.

---

## Phase 5 — Reflection + HITL Gate + Memory Write-back (Day 4, ~2–3 hrs)

### Goal
A reflection agent reviews the proposed fix; a human-in-the-loop gate pauses for Sev-1/2; resolved incidents are written back to memory.

### Concepts covered
`Reflection pattern` · `Human-in-the-loop (HITL)` · `Episodic memory write-back`

### Tasks for Antigravity agent
- [ ] Create `agents/reflector.py` with `review_plan(incident_result: dict) -> dict` — a second LLM call that critiques the proposed fix: "Is this fix specific enough? Does it address the root cause or just symptoms? Rate 1-10."
- [ ] If reflection score < 6, loop back to the expert agent ONE more time with the critique as additional context (max 1 retry — this is a mini Ralph Wiggum loop)
- [ ] Create `agents/hitl_gate.py` with `human_approval_gate(incident_result: dict) -> dict`:
  - If `severity <= 2` (Sev-1 or Sev-2): print the proposed fix and use `input("Approve? (y/n): ")` to pause for human input
  - If rejected, mark `status: "rejected_by_human"` and do NOT write to memory
  - If approved or `severity > 2`: proceed to memory write-back
- [ ] On approval, call `save_resolution()` from Phase 3 to write the new incident + fix back into ChromaDB
- [ ] Wire all of this into `orchestrator.py` as the final steps of `route_incident()`

### Phase 5 — Demo checkpoint
Run the full pipeline on the network log (Sev-2). The terminal should:
1. Show the classification
2. Show the expert's proposed fix
3. Show the reflection agent's review
4. **Pause and ask for your approval** (this is the HITL moment — make sure this is visible and dramatic in the demo)
5. On `y`, confirm the incident was written to memory

---

## Phase 6 — Demo Script + CLI Runner (Day 4, ~1 hr)

### Goal
A single command that runs the full pipeline on all 4 sample logs, suitable for a live demo.

### Tasks for Antigravity agent
- [ ] Create `main.py` — reads `data/sample_logs.txt`, splits into 4 blocks, runs `route_incident()` on each
- [ ] Add clear console output with separators between each incident (use simple `print("="*60)` dividers — no need for fancy libraries)
- [ ] Print a final summary table: log type → severity → category → status → confidence
- [ ] Add a `--seed` flag to `main.py` that runs `seed_memory()` first (so a fresh clone can self-initialize)

### Phase 6 — Demo checkpoint (Final Demo)
Run:
```bash
python main.py --seed
```

**Expected demo flow (this is what you show in your session):**
1. DB incident → routes to DB expert → retrieves `inc_001` from memory → proposes PgBouncer restart → reflection approves → Sev-3, auto-approved → written to memory
2. Network incident → routes to Network expert → retrieves `inc_003`/`inc_004` → proposes fix → reflection approves → **Sev-2, pauses for YOUR approval** → you type `y` → written to memory
3. App incident → routes to App expert → retrieves `inc_005` → proposes fix → reflection approves → **Sev-2, pauses for approval** → you type `y`
4. Ambiguous pipeline log → low confidence → falls back to generic handler → `status: "resolved_by_fallback"` → Sev-4, auto-approved

---

## Optional Phase 7 — Stretch Goals (if time permits)

Only attempt these AFTER Phase 6 is fully working and demoable. Pick ONE:

- [ ] **Scope debate loop (Ralph Wiggum):** Add two agents (`strict_scope_agent`, `lenient_scope_agent`) that argue about which services are affected before triage, with a `moderator()` producing a final scope verdict. 2 rounds max.
- [ ] **Context graph:** Use a simple Python dict-of-dicts (no Neo4j needed for POC) to map `service → depends_on → [other services]`, and have the orchestrator check this graph to identify "other potentially affected services."
- [ ] **Cost tracking:** Add a token counter to `call_llm()` and print total estimated cost at the end of `main.py`.

---

## File structure summary (for Antigravity to scaffold)

```
incident-response-poc/
├── .env                    (you create, never commit)
├── .env.example
├── .gitignore
├── requirements.txt
├── config.py               # LLM provider wrapper
├── main.py                 # CLI demo runner
├── PLAN.md                 # this file
├── agents/
│   ├── classifier.py        # Phase 1
│   ├── orchestrator.py       # Phase 2, 4, 5
│   ├── db_expert.py          # Phase 2
│   ├── network_expert.py      # Phase 2
│   ├── app_expert.py         # Phase 2
│   ├── generic_handler.py     # Phase 2, 4
│   ├── reflector.py          # Phase 5
│   └── hitl_gate.py          # Phase 5
├── tools/
│   └── memory.py             # Phase 3
├── data/
│   ├── sample_logs.txt       # Phase 1
│   └── seed_incidents.json    # Phase 3
├── scripts/
│   └── seed_db.py             # Phase 3
└── tests/
    ├── test_classifier.py
    ├── test_orchestrator.py
    └── test_degradation.py
```

---

## Working with Antigravity — tips for beginners

- **Use Plan mode for every phase.** Before letting the agent write code, ask it to generate a Plan Artifact for that phase only. Review the plan — does it match what's described above? If yes, approve. If it's doing too much at once, ask it to scope down to just this phase.
- **One phase = one commit.** After each phase's demo checkpoint passes, commit your code. This gives you rollback points if a later phase breaks something.
- **Let the agent write tests, but YOU run them.** Antigravity can execute terminal commands automatically — but for learning, run `python tests/test_classifier.py` yourself the first time so you see the raw output and understand what's happening.
- **If the agent gets stuck in a loop:** stop it, and manually inspect the last file it edited. Agentic IDEs can sometimes "fix" the same bug repeatedly without realizing it didn't work — this is exactly the context rot problem the Ralph Wiggum loop solves, and it's good to recognize it when it happens to you.
- **Switching LLM providers mid-project:** just change `LLM_PROVIDER` in `.env`. Nothing else should need to change — if it does, that's a sign `config.py` wasn't built correctly as the single abstraction point.

---

## Quick reference — what each phase teaches (curriculum mapping)

| Phase | Curriculum week | Pattern |
|---|---|---|
| 0 | Week 1 | Environment setup, basic LLM API integration |
| 1 | Week 1 / 3 | Single agent loop, structured output |
| 2 | Week 4 | Orchestrator, dynamic routing, multi-agent |
| 3 | Week 5 | RAG memory, vector search |
| 4 | Week 4 | Graceful degradation, circuit breaker |
| 5 | Week 3 | Reflection, human-in-the-loop |
| 6 | Week 9 | Demo packaging |
| 7 (optional) | Week 4 / 5 | Ralph Wiggum loop, context graph |
