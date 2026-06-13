# Implementation Plan - Phase 6: Demo Script + CLI Runner

This plan outlines the creation of the main entry point and CLI runner to showcase the entire multi-agent incident response POC.

## Proposed Changes

### Entrypoint Layer

#### [NEW] [main.py](file:///Users/sonalipatnaik/DocumentsLocal/Projects/AgentAI/poc/main.py)
Create the main execution script:
1. Parse arguments using `argparse` to support the `--seed` flag.
2. If `--seed` is passed, automatically trigger database initialization and seeding.
3. Load [sample_logs.txt](file:///Users/sonalipatnaik/DocumentsLocal/Projects/AgentAI/poc/data/sample_logs.txt) and split them into individual incident logs.
4. Loop through each incident:
   - Display a clean separator banner.
   - Call `route_incident(log_text)`.
   - Print the routed handler, critique score, reflection details, and the resulting suggested fixes.
5. Print a final summary table in the terminal outlining:
   - Incident Type / Title
   - Severity
   - Category
   - Status (e.g., `resolved_by_expert`, `resolved_by_fallback`, `rejected_by_human`)
   - Confidence

## Verification Plan

### Manual Verification
- Run the demo script in the terminal:
  ```bash
  python main.py --seed
  ```
- Go through the interactive prompt validations (approving/rejecting Sev-1/2 plans).
- Check that the final summary table prints correctly and summarizes the outcome of all processed incidents.
