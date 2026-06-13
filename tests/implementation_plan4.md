# Implementation Plan - Phase 4: Graceful Degradation + Circuit Breaker

This plan outlines the steps to build robust error handling, transient fault tolerance, and agent fallbacks.

## Proposed Changes

### Configuration Layer

#### [MODIFY] [config.py](file:///Users/sonalipatnaik/DocumentsLocal/Projects/AgentAI/poc/config.py)
Integrate retry logic using the `tenacity` library:
- Wrap LLM invocations inside `call_llm` with exponential backoff and a maximum of 2 retries (3 attempts total) to recover from transient API errors.

### Agent Layer

#### [MODIFY] [orchestrator.py](file:///Users/sonalipatnaik/DocumentsLocal/Projects/AgentAI/poc/agents/orchestrator.py)
Enhance `route_incident(log_text: str) -> dict` with circuit breaker and fallback logic:
1. Wrap the expert call in a `try/except` block.
2. If the expert throws an exception OR returns a confidence score less than `0.5`, log the warning/exception and call `generic_handler.analyze()`.
3. Add a `status` field to the returned dictionary:
   - `"resolved_by_expert"`: Expert completed successfully with `confidence >= 0.5`.
   - `"resolved_by_fallback"`: Ran fallback generic handler (due to expert failure, low confidence, or `"unknown"` category).
   - `"failed"`: Both the expert and fallback failed.

### Test Layer

#### [NEW] [test_degradation.py](file:///Users/sonalipatnaik/DocumentsLocal/Projects/AgentAI/poc/tests/test_degradation.py)
Create a test runner that:
1. Passes an empty log string to `route_incident()`.
2. Passes a completely nonsense/gibberish log string to `route_incident()`.
3. Asserts that both do not crash and return `status: "resolved_by_fallback"`.

## Verification Plan

### Automated Tests
- Run `python tests/test_degradation.py` to check that malformed/nonsense inputs are handled gracefully and output `"resolved_by_fallback"`.
- Re-run `python tests/test_orchestrator.py` to verify that standard logs are still processed correctly with `"resolved_by_expert"` status.
