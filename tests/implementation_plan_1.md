# Implementation Plan - Phase 1: Log Classifier Agent

This plan outlines the steps to build and verify the Phase 1 Single Agent: Log Analyzer.

## Proposed Changes

### Data Layer

#### [NEW] [sample_logs.txt](file:///Users/sonalipatnaik/DocumentsLocal/Projects/AgentAI/poc/data/sample_logs.txt)
Create the sample logs data file containing the four incidents: Database, Network, Application, and Ambiguous. We will delimit them clearly using a separator (e.g. `---`) or headers so they can be parsed programmatically.

### Agent Layer

#### [NEW] [classifier.py](file:///Users/sonalipatnaik/DocumentsLocal/Projects/AgentAI/poc/agents/classifier.py)
Implement `classify_log(log_text: str) -> dict` which:
1. Constructs a system/user prompt instructing the LLM to output a JSON object with:
   - `severity`: 1-5
   - `category`: `"database" | "network" | "application" | "unknown"`
   - `root_cause`: string description
   - `confidence`: 0.0-1.0
2. Calls `call_llm` (from [config.py](file:///Users/sonalipatnaik/DocumentsLocal/Projects/AgentAI/poc/config.py)).
3. Parses the response as JSON, with robust error handling (stripping markdown fences like ` ```json ` and ` ``` `).

### Test Layer

#### [NEW] [test_classifier.py](file:///Users/sonalipatnaik/DocumentsLocal/Projects/AgentAI/poc/tests/test_classifier.py)
Create a test runner that:
1. Loads [sample_logs.txt](file:///Users/sonalipatnaik/DocumentsLocal/Projects/AgentAI/poc/data/sample_logs.txt).
2. Splits the file into the 4 distinct incidents.
3. Passes each incident to `classify_log()`.
4. Prints the JSON results.

## Verification Plan

### Automated Tests
- Run `python tests/test_classifier.py` from the root of the project to check if all four logs are successfully classified and structured output is printed.
