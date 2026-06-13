# Implementation Plan - Phase 2: Orchestrator + Dynamic Routing

This plan outlines the steps to build and verify the Phase 2 Orchestrator and expert agents.

## Proposed Changes

### Agent Layer

#### [NEW] [db_expert.py](file:///Users/sonalipatnaik/DocumentsLocal/Projects/AgentAI/poc/agents/db_expert.py)
Implement `analyze(log_text: str, classification: dict) -> dict` using the LLM with a system prompt locked to a Senior Database Engineer role. Focuses on connection pools, locks, replication, queries. Returns: `{"severity": int, "owner_team": str, "suggested_fix": [list of steps], "confidence": float}`.

#### [NEW] [network_expert.py](file:///Users/sonalipatnaik/DocumentsLocal/Projects/AgentAI/poc/agents/network_expert.py)
Implement `analyze(log_text: str, classification: dict) -> dict` locked to a Senior Network Engineer role. Focuses on routing, DNS, load balancers, latency. Returns same schema.

#### [NEW] [app_expert.py](file:///Users/sonalipatnaik/DocumentsLocal/Projects/AgentAI/poc/agents/app_expert.py)
Implement `analyze(log_text: str, classification: dict) -> dict` locked to a Senior Application Engineer role. Focuses on memory, thread pools, garbage collection, exceptions. Returns same schema.

#### [NEW] [generic_handler.py](file:///Users/sonalipatnaik/DocumentsLocal/Projects/AgentAI/poc/agents/generic_handler.py)
Implement `analyze(log_text: str, classification: dict) -> dict` as a generic systems reliability fallback with no specific role lock. Returns same schema.

#### [NEW] [orchestrator.py](file:///Users/sonalipatnaik/DocumentsLocal/Projects/AgentAI/poc/agents/orchestrator.py)
Implement `route_incident(log_text: str) -> dict` which:
1. Calls `classify_log(log_text)` to get the initial category, severity, and confidence.
2. Maps `category` to the corresponding expert (`database` -> DB, `network` -> Network, `application` -> App, and `unknown` -> Generic).
3. Executes the selected expert's `analyze` function.
4. Returns a combined dictionary containing classification details and the expert's response.

### Test Layer

#### [NEW] [test_orchestrator.py](file:///Users/sonalipatnaik/DocumentsLocal/Projects/AgentAI/poc/tests/test_orchestrator.py)
Create a test runner that:
1. Loads the 4 sample logs from [sample_logs.txt](file:///Users/sonalipatnaik/DocumentsLocal/Projects/AgentAI/poc/data/sample_logs.txt).
2. Runs each through `route_incident()`.
3. Verifies routing behavior (DB -> db_expert, Network -> network_expert, App -> app_expert, Ambiguous -> generic_handler).
4. Prints the output results.

## Verification Plan

### Automated Tests
- Run `python tests/test_orchestrator.py` from the root of the project to check if all four logs are routed to the correct expert and return the correct response format.
