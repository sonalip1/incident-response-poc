# Incident Response POC — Live Demo UI Plan

**Builds on:** `incident_response_poc_plan.md` (the agent pipeline)
**Goal:** A polished, browser-based demo where you paste/feed a log and watch the agent crew work in real time, ending in a clean "incident card" output
**Target IDE:** Google Antigravity (Plan mode)
**Time estimate:** +1.5–2 days on top of the existing plan (best done AFTER Phase 6 of the original plan)

---

## How to use this file in Antigravity

1. This is **Phase 8** of your project — only start this after Phases 0–6 of `incident_response_poc_plan.md` are working and demoable via CLI.
2. Paste this file into Antigravity's Manager chat with:
   > "Read this UI plan. My agent pipeline from PLAN.md already works via CLI. Build this as a new layer on top — do not modify the existing `agents/` folder logic, only wrap it. Work phase by phase, pause after each checkpoint."
3. Antigravity should generate a Plan Artifact that adds a `backend/` and `frontend/` folder alongside your existing `agents/`, `tools/`, `data/` folders.

---

## Design direction (give this to Antigravity verbatim — it shapes the whole UI)

> Build this as an **"Incident Command Center"** — the visual language of a calm, professional SRE war-room at 2 AM, not a flashy SaaS marketing page. Dark background (`#0B1120` near-black navy), with three accent colors used purposefully: amber (`#F2A33D`) for in-progress/warning states, teal (`#2DD4BF`) for resolved/healthy states, and red (`#EF4444`) reserved ONLY for Sev-1/Sev-2 active incidents. Body text in soft slate (`#CBD5E1`).
>
> Typography: use a monospace font (`JetBrains Mono` or `Roboto Mono`) for anything that represents raw data — logs, JSON, agent reasoning traces. Use a clean geometric sans (`Inter` or `IBM Plex Sans`) for UI labels, buttons, and headers. This contrast is intentional — it signals "raw machine output" vs "human-readable summary."
>
> The signature element of this UI is the **live agent trace panel** — a terminal-style scrolling feed that shows each agent's Thought → Action → Observation as it happens, with a typing/streaming effect. This is what makes the demo feel alive. Don't skip or simplify this.
>
> Motion: keep it minimal and purposeful. The trace panel streams text. The severity badge on the final incident card does one subtle pulse when it first appears. The confidence ring animates from 0 to its final value over ~800ms. No bouncing, no excessive transitions elsewhere.
>
> Layout: two-column split on desktop (stacks on mobile). Left column = input + live trace. Right column = final incident card output. A persisted "Incident History" strip below shows past resolved incidents from this session as small cards.

---

## Architecture overview

```
+-----------------------------------------------------------------+
|                     Browser (Frontend)                            |
|  +-------------------+         +------------------------------+  |
|  |  Log Input Panel  |         |   Incident Card (output)      |  |
|  |  - paste/select   |         |   - severity badge            |  |
|  |  - "Run Agent" btn|         |   - confidence ring           |  |
|  +-------------------+         |   - root cause + fix steps    |  |
|  +-------------------+         |   - HITL approve/reject UI    |  |
|  | Live Agent Trace  |         +------------------------------+  |
|  | (streaming SSE)   |                                            |
|  | Thought->Action->Obs |       +------------------------------+  |
|  +-------------------+         |   Incident History strip      |  |
|                                  +------------------------------+  |
+----------------------+--------------------------------------------+
                        | HTTP + Server-Sent Events (SSE)
+-----------------------v-------------------------------------------+
|              FastAPI Backend (backend/main.py)                      |
|  POST /api/incidents  -> starts pipeline, returns incident_id       |
|  GET  /api/incidents/{id}/stream  -> SSE stream of agent steps       |
|  POST /api/incidents/{id}/approve -> HITL approval endpoint          |
|  GET  /api/incidents  -> list of past incidents (history)            |
|                                                                       |
|  Wraps existing: agents/orchestrator.py, tools/memory.py             |
+-----------------------------------------------------------------------+
```

---

## Phase 8.1 — Backend: FastAPI wrapper (Day 1, ~3 hrs)

### Goal
Expose the existing `route_incident()` pipeline as a streaming HTTP API, without rewriting agent logic.

### Concepts covered
`API gateway pattern (Week 9)` * `Streaming responses (Week 6)` * `Queue-based task tracking`

### Tasks for Antigravity agent
- [ ] Create `backend/main.py` with FastAPI app
- [ ] Create `backend/models.py` — Pydantic models for `IncidentRequest`, `IncidentStep`, `IncidentResult`
- [ ] Refactor `agents/orchestrator.py`'s `route_incident()` into a **generator function** `route_incident_streaming(log_text)` that `yield`s a dict after each agent step (classification done, expert called, RAG results retrieved, reflection done, etc.) instead of just returning the final result. This is the key change — everything else can stay the same.
- [ ] `POST /api/incidents` — accepts `{"log_text": "..."}`, generates a UUID `incident_id`, starts processing in the background (use `asyncio` task or simple thread), returns `{"incident_id": "..."}`
- [ ] `GET /api/incidents/{incident_id}/stream` — Server-Sent Events (SSE) endpoint. Streams each step from `route_incident_streaming()` as a JSON event: `{"step": "classification", "data": {...}}`, `{"step": "rag_retrieval", "data": {...}}`, `{"step": "expert_analysis", "data": {...}}`, `{"step": "reflection", "data": {...}}`, `{"step": "hitl_required", "data": {...}}` or `{"step": "complete", "data": {...}}`
- [ ] `POST /api/incidents/{incident_id}/approve` — accepts `{"approved": true/false}`, resumes the paused pipeline (for Sev-1/2), triggers `save_resolution()` if approved
- [ ] `GET /api/incidents` — returns a list of the last 10 incidents (in-memory list is fine for POC — no DB needed)
- [ ] Add CORS middleware (`allow_origins=["*"]` is fine for local demo)
- [ ] Add `backend/requirements.txt`: `fastapi`, `uvicorn`, `sse-starlette`

### Important note on streaming + HITL
The HITL gate (Phase 5 of the original plan) used `input()` for CLI. In the API version, this becomes: the SSE stream sends a `hitl_required` event and **pauses** (the generator yields and waits). The frontend shows an Approve/Reject UI. When the user clicks, `POST /approve` is called, which signals the paused generator to continue. The simplest implementation: store pipeline state in a dict keyed by `incident_id`, with an `asyncio.Event` that the approve endpoint sets.

### Phase 8.1 — Demo checkpoint
Run `uvicorn backend.main:app --reload`. Use `curl` or a browser to:
1. `POST /api/incidents` with a sample log -> get back an `incident_id`
2. `GET /api/incidents/{id}/stream` -> watch JSON events stream in real time in the terminal (use `curl -N` to see streaming)
3. Confirm the Sev-2 log pauses at `hitl_required` and only completes after `POST /approve`

---

## Phase 8.2 — Frontend: Scaffold + Log Input Panel (Day 1–2, ~2–3 hrs)

### Goal
A clean app (single HTML file or React) with the input panel and "Run Agent" button.

### Tasks for Antigravity agent
- [ ] Ask Antigravity: "Should this be a React app (Vite) or a single HTML file with vanilla JS?" — **for a beginner doing a quick demo, recommend the single HTML file approach** (no npm install, no build step, just open in browser). Only choose React/Vite if you're comfortable with `npm run dev`.
- [ ] Create `frontend/index.html` (or `frontend/src/App.jsx` if React) with:
  - Page header: "Incident Command Center" with a small live-status dot (green = backend connected)
  - **Log Input Panel** (left column, top):
    - A `<select>` dropdown: "Sample Logs" with 4 options (DB / Network / App / Ambiguous) — pre-fills the textarea from `data/sample_logs.txt`
    - A large `<textarea>` for the log text (monospace font)
    - A primary button: "Run Incident Response" — amber background, dark text
  - Apply the design direction from above: dark navy background, JetBrains Mono for the textarea, Inter for labels/buttons
- [ ] Add a `frontend/styles.css` with CSS custom properties for the color tokens (`--bg`, `--amber`, `--teal`, `--red`, `--text`, `--text-muted`)
- [ ] Wire the button to `POST /api/incidents` and store the returned `incident_id`

### Phase 8.2 — Demo checkpoint
Open `frontend/index.html` in a browser (with backend running). Select a sample log, click "Run Incident Response." Open browser dev tools — confirm the `POST` request fires and an `incident_id` comes back. Nothing visual happens yet beyond this — that's Phase 8.3.

---

## Phase 8.3 — Live Agent Trace Panel (Day 2, ~3–4 hrs) — THE SIGNATURE FEATURE

### Goal
A scrolling, terminal-style panel that streams each agent's Thought -> Action -> Observation as the SSE events arrive.

### Concepts covered
`ReAct trace visualization` * `Streaming UI` * `Real-time agent observability`

### Tasks for Antigravity agent
- [ ] Below the Log Input Panel, add a **Live Agent Trace** panel — fixed height (~400px), scrollable, dark background (`#070B14`, slightly darker than page bg), monospace font, terminal aesthetic (subtle scanline or border-glow optional but keep restrained per design direction)
- [ ] On button click, open an `EventSource` connection to `/api/incidents/{id}/stream`
- [ ] For each SSE event received, append a new "trace line" to the panel:
  - `classification` step -> render as: `[CLASSIFIER] Severity: {n} | Category: {cat} | Confidence: {pct}%` in teal
  - `rag_retrieval` step -> render as: `[MEMORY] Found {n} similar past incidents: "{summary}"` in slate
  - `expert_analysis` step -> render as: `[{EXPERT_NAME}] Thought: "{reasoning}"` then `[{EXPERT_NAME}] -> Proposed fix: {steps}` — use a typing/reveal animation (CSS or simple `setTimeout` char-by-char) for the "Thought" line specifically — this sells the "agent is thinking" feeling
  - `reflection` step -> render as: `[REFLECTOR] Review score: {n}/10 — "{critique}"` in amber if score < 6, teal if >= 6
  - `hitl_required` step -> render as: `[SYSTEM] Severity {n} — human approval required` in red, AND trigger the Approve/Reject UI (Phase 8.4)
  - `complete` step -> render as: `[SYSTEM] Incident resolved — written to memory` in teal, AND trigger the Incident Card render (Phase 8.4)
- [ ] Auto-scroll the panel to the bottom as new lines arrive
- [ ] Each trace line should fade/slide in (simple CSS `@keyframes`, ~200ms) — this is the "purposeful motion" the design direction calls for

### Phase 8.3 — Demo checkpoint
Click "Run Incident Response" on the DB sample log. Watch the trace panel populate live, line by line, ending with either the HITL prompt (Sev-1/2) or the completion line (Sev-3+). **This is the moment that will make your audience say "oh, that's cool"** — spend extra polish time here if you have it.

---

## Phase 8.4 — Incident Card Output + HITL UI (Day 2–3, ~2–3 hrs)

### Goal
A polished "result card" that appears once the pipeline completes, plus an inline approve/reject UI for HITL.

### Tasks for Antigravity agent
- [ ] Create the **Incident Card** component (right column) — hidden until first `complete` or `hitl_required` event arrives. Contains:
  - **Severity badge** — large rounded badge, color-coded (Sev 1-2 = red, Sev 3 = amber, Sev 4-5 = teal), with a single subtle "pop" animation on first appearance (scale 0.9 -> 1.0, ~250ms)
  - **Confidence ring** — an SVG circular progress ring (use `stroke-dasharray` trick) that animates from 0% to the final confidence value over ~800ms. Label in the center: "{pct}% confidence"
  - **Root cause** — one sentence, larger text, Inter font
  - **Affected service** — small label/tag
  - **Suggested fix steps** — numbered list, monospace for any code/command-like text within steps
  - **"Resolved via"** tag — shows whether this came from `db_expert`, `network_expert`, `app_expert`, or `generic_handler` (fallback) — use a small icon or colored dot to distinguish fallback vs expert-resolved
- [ ] **HITL Approve/Reject UI**: when `hitl_required` event arrives, show two buttons inside the (still-populating) Incident Card: "Approve Fix" (teal) and "Reject" (outline/ghost style). Card shows "Awaiting approval..." state with a subtle pulsing border in red until a decision is made.
  - On click, `POST /api/incidents/{id}/approve` with `{"approved": true/false}`
  - On approve: card transitions to normal "resolved" state, trace panel shows the completion line
  - On reject: card shows "Rejected — not written to memory" in muted text, trace panel logs this
- [ ] Add a small **"View raw agent trace"** toggle/link on the card that expands to show the full JSON of all SSE events received (useful for Q&A during your demo — "here's exactly what each agent returned")

### Phase 8.4 — Demo checkpoint
Run the full flow on the Network sample log (Sev-2). Confirm:
1. Trace panel populates
2. Incident card appears in "awaiting approval" state with pulsing red border
3. Clicking "Approve" completes the flow, card shows final resolved state with animated confidence ring
4. The "raw agent trace" toggle shows readable JSON

---

## Phase 8.5 — Incident History Strip + Polish Pass (Day 3, ~2 hrs)

### Goal
Show a row of small cards for previously resolved incidents (within this session), and do a final visual polish pass.

### Tasks for Antigravity agent
- [ ] Below the main two-column layout, add an **Incident History** strip — horizontal row of small cards, each showing: severity badge (small), category icon, one-line root cause, timestamp
- [ ] On page load and after each `complete`/`approve`, call `GET /api/incidents` and render this strip
- [ ] Clicking a history card re-populates the Incident Card (right column) with that incident's full details (read-only — no re-running)
- [ ] **Polish pass** — ask Antigravity to take a screenshot of the running app (if it has browser tooling) and do a self-critique against the design direction:
  - Is the trace panel readable at a glance from a few feet away (projector test)?
  - Does the severity color-coding feel consistent across the trace, the card, and the history strip?
  - Is there any unnecessary animation to remove? (per design direction: "remove one accessory")
  - Check responsive behavior — does it degrade reasonably on a laptop screen at 1280px width (common projector resolution)?

### Phase 8.5 — Demo checkpoint (Final)
Run all 4 sample logs in sequence (DB -> Network -> App -> Ambiguous), approving HITL prompts as they arise. The history strip should show 4 cards at the end, color-coded by severity, with the ambiguous one visually distinguished as "fallback-resolved" (e.g., a small dotted border or muted icon instead of the expert's colored dot).

---

## Running the full demo (Day 3, dry run)

### Terminal 1 — Backend
```bash
cd incident-response-poc
uvicorn backend.main:app --reload --port 8000
```

### Terminal 2 — Frontend
If single HTML file: just open `frontend/index.html` in a browser (use the "Live Server" extension in VS Code-based editors, or `python -m http.server 5500` from the `frontend/` folder to avoid CORS file:// issues).

If React/Vite:
```bash
cd frontend
npm run dev
```

### Live demo script (suggested flow for your audience)
1. **Open with the empty dashboard** — "This is our Incident Command Center. Right now, nothing's happening — just like a quiet on-call shift."
2. **Select the DB sample log, click Run** — "A DB connection timeout just fired on payment-service. Watch what happens."
3. **Narrate the trace panel as it streams** — "There's the classifier — Sev 3, database category. Now it's checking memory for similar past incidents... found one from April. Now the DB expert is reasoning about it..."
4. **Point at the completed Incident Card** — "And there's the fix — restart the connection pool, root cause identified, 94% confidence, resolved automatically because it's Sev-3."
5. **Run the Network sample log (Sev-2)** — "This one's more serious. Watch — the system pauses and asks ME before doing anything." Click Approve live.
6. **Run the Ambiguous log last** — "And this one — the system isn't confident enough to assign a specialist, so it falls back gracefully instead of guessing wrong." Point out the muted/dotted styling in the history strip.
7. **Close on the history strip** — "Four incidents, four outcomes, full transparency into every agent's reasoning — and it remembers all of this for next time."

---

## File structure addition

```
incident-response-poc/
+-- ... (existing agents/, tools/, data/, scripts/, tests/ from PLAN.md)
+-- backend/
|   +-- main.py              # FastAPI app, SSE streaming
|   +-- models.py            # Pydantic models
|   +-- requirements.txt
+-- frontend/
    +-- index.html           # or src/App.jsx if React
    +-- styles.css
    +-- (assets/, if any)
```

---

## Tips for beginners on this phase

- **Don't build the frontend and backend simultaneously.** Get Phase 8.1 fully working with `curl`/Postman first — confirm the streaming works correctly — before writing any HTML. Debugging SSE + UI bugs at the same time is confusing.
- **The single HTML file approach is genuinely fine for a demo.** Don't feel pressure to set up React/Vite/npm if you're not comfortable with it — `EventSource` and vanilla JS handle this entire UI without a build step. You can always migrate to React later if you want this to become a "real" project.
- **If SSE feels too advanced, fall back to polling.** An easier (if less elegant) alternative: `POST /api/incidents` runs the whole pipeline synchronously and returns the full list of steps as one JSON array. The frontend then animates through the array with `setTimeout` between each step — visually identical to the audience, much simpler to build and debug. Mention this as Plan B if Phase 8.1's SSE implementation is taking too long.
- **Test the projector/screen-share resolution before your session.** Dark UIs with small monospace text can be hard to read on a projector. Do a screen-share test run with a friend or in a practice session.

---

## Quick reference — what this phase teaches (curriculum mapping)

| Phase | Curriculum week | Pattern |
|---|---|---|
| 8.1 | Week 6, 9 | Streaming responses, API gateway pattern |
| 8.2 | Week 9 | API integration, frontend basics |
| 8.3 | Week 1, 6 | Observability — making agent reasoning visible (Phoenix-equivalent, but custom UI) |
| 8.4 | Week 3 | Human-in-the-loop UX |
| 8.5 | Week 9 | Production polish, documentation via demo |
