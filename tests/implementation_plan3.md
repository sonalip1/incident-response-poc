# Implementation Plan - Phase 3: RAG Memory with ChromaDB

This plan outlines the steps to build and integrate RAG Memory for our expert agents.

## Proposed Changes

### Data Layer

#### [NEW] [seed_incidents.json](file:///Users/sonalipatnaik/DocumentsLocal/Projects/AgentAI/poc/data/seed_incidents.json)
Create a database of 6 past incidents in JSON format, containing an ID, category, and text description of the incident and its resolution.

### Tools Layer

#### [NEW] [memory.py](file:///Users/sonalipatnaik/DocumentsLocal/Projects/AgentAI/poc/tools/memory.py)
Implement the vector database memory module using `chromadb`:
- `init_memory()`: Initializes a persistent ChromaDB client at `./chroma_db/` and returns the collection.
- `seed_memory()`: Loads the json dataset and seeds the collection (with documents, IDs, and metadatas).
- `get_similar_incidents(log_text: str, n: int = 3) -> list[str]`: Queries the collection for similar incidents. We will implement robust similarity querying (optionally filtering by category).
- `save_resolution(log_text: str, resolution: dict)`: Saves new resolutions back to the collection.

### Scripts Layer

#### [NEW] [seed_db.py](file:///Users/sonalipatnaik/DocumentsLocal/Projects/AgentAI/poc/scripts/seed_db.py)
Create a simple runner script to initialize and seed the database once.

### Agent Layer

#### [MODIFY] [db_expert.py](file:///Users/sonalipatnaik/DocumentsLocal/Projects/AgentAI/poc/agents/db_expert.py)
#### [MODIFY] [network_expert.py](file:///Users/sonalipatnaik/DocumentsLocal/Projects/AgentAI/poc/agents/network_expert.py)
#### [MODIFY] [app_expert.py](file:///Users/sonalipatnaik/DocumentsLocal/Projects/AgentAI/poc/agents/app_expert.py)
Update the experts to:
1. Retrieve similar past incidents from the database using `get_similar_incidents()`.
2. Inject these past resolutions into the LLM system/user prompts to guide the suggestions.

## Verification Plan

### Automated Tests
1. Run `python scripts/seed_db.py` to populate the database.
2. Run `python tests/test_orchestrator.py` to verify that:
   - Past incident details are fetched and included in the prompts.
   - The final expert recommendations reference these past incidents (e.g. `inc_001` PgBouncer connection limit details for the DB incident).
