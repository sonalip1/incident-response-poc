import os
import sys
import uuid
import json
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import route_incident_streaming
from backend.models import IncidentRequest, IncidentApproval

app = FastAPI(title="Incident Response POC Backend")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for active pipeline tasks
# Map: incident_id -> asyncio.Queue (contains SSE dictionaries)
queues = {}
# Map: incident_id -> asyncio.Event (used to pause/resume Sev-1/2 HITL gate)
hitl_events = {}
# Map: incident_id -> bool (operator's choice: True = approved, False = rejected)
hitl_decisions = {}
# Map: incident_id -> original log text
active_logs = {}

# In-memory circular buffer for the last 10 completed incidents
history = []

async def run_pipeline_task(incident_id: str, log_text: str):
    """Background task that runs the streaming generator and enqueues SSE events."""
    event = asyncio.Event()
    hitl_events[incident_id] = event
    hitl_decisions[incident_id] = False
    
    queue = asyncio.Queue()
    queues[incident_id] = queue
    
    try:
        async for step_event in route_incident_streaming(
            log_text=log_text,
            incident_id=incident_id,
            hitl_event=event,
            hitl_decision_dict=hitl_decisions
        ):
            await queue.put(step_event)
            
            # If complete, save to history
            if step_event.get("step") == "complete":
                result = step_event.get("data", {})
                # Add original incident ID & log text to output metadata
                result["incident_id"] = incident_id
                result["log_text"] = log_text
                
                # Prepend to history, keeping max 10 records
                history.insert(0, result)
                if len(history) > 10:
                    history.pop()
                    
    except Exception as e:
        print(f"Error in background pipeline task {incident_id}: {e}")
        await queue.put({
            "step": "error",
            "data": {"message": f"Pipeline task failed: {str(e)}"}
        })
    finally:
        # Signal end-of-stream
        await queue.put(None)

@app.post("/api/incidents")
async def create_incident(req: IncidentRequest, background_tasks: BackgroundTasks):
    """
    Accepts log text, triggers background analysis pipeline, and returns generated incident_id.
    """
    if not req.log_text.strip():
        raise HTTPException(status_code=400, detail="Log text cannot be empty.")
        
    incident_id = str(uuid.uuid4())
    active_logs[incident_id] = req.log_text
    
    # Start the async orchestrator task in the background
    background_tasks.add_task(run_pipeline_task, incident_id, req.log_text)
    
    return {"incident_id": incident_id}

@app.get("/api/incidents/{incident_id}/stream")
async def stream_incident(incident_id: str):
    """
    SSE endpoint to stream live trace steps of agent execution.
    """
    if incident_id not in queues:
        raise HTTPException(status_code=404, detail="Incident ID not found or expired.")
        
    async def event_generator():
        queue = queues[incident_id]
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield {
                    "event": "message",
                    "data": json.dumps(item)
                }
        except asyncio.CancelledError:
            # Handle client disconnect
            print(f"Client disconnected from SSE stream for {incident_id}")
            
    return EventSourceResponse(event_generator())

@app.post("/api/incidents/{incident_id}/approve")
async def approve_incident(incident_id: str, approval: IncidentApproval):
    """
    Resumes a paused Sev-1/2 incident's pipeline based on the operator's decision.
    """
    if incident_id not in hitl_events:
        raise HTTPException(status_code=404, detail="Active incident not found.")
        
    hitl_decisions[incident_id] = approval.approved
    # Resume the paused orchestrator generator
    hitl_events[incident_id].set()
    
    return {"status": "resumed", "approved": approval.approved}

@app.get("/api/incidents")
async def get_incidents_history():
    """
    Returns the last 10 completed incidents.
    """
    return history
