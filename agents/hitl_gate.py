import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.memory import save_resolution

def human_approval_gate(log_text: str, incident_result: dict) -> dict:
    """
    If the incident is high severity (severity <= 2):
    - Pauses execution and prompts the operator to approve the proposed fix.
    - If approved, or if severity > 2, calls save_resolution() to save the resolution to ChromaDB memory.
    - If rejected, updates status to 'rejected_by_human' and skips memory write-back.
    """
    classification = incident_result.get("classification", {})
    severity = classification.get("severity", 3)
    analysis = incident_result.get("analysis", {})
    
    # Check if high severity (Sev-1 or Sev-2)
    if severity <= 2:
        print("\n" + "!" * 80)
        print(f"🚨 HIGH SEVERITY INCIDENT ALERT: SEV-{severity}")
        print("!" * 80)
        print(f"Log Text:\n{log_text}")
        print("-" * 80)
        print(f"Routed Expert: {incident_result.get('expert_handler')}")
        print(f"Responsible Team: {analysis.get('owner_team')}")
        print("Suggested Fix Steps:")
        for idx, step in enumerate(analysis.get("suggested_fix", []), 1):
            print(f"  {idx}. {step}")
        print(f"Confidence: {analysis.get('confidence')}")
        print("!" * 80)
        
        # Pause for human approval
        user_input = input("\nApprove this resolution plan? (y/n): ").strip().lower()
        if user_input != 'y':
            print("\n❌ Resolution plan REJECTED by operator. Skipping memory write-back.")
            incident_result["status"] = "rejected_by_human"
            return incident_result
            
        print("\n✅ Resolution plan APPROVED by operator.")
        
    # Write to memory (for approved high severity or automatic lower severity incidents)
    try:
        # Pass log text and expert analysis to save_resolution
        save_resolution(log_text, analysis)
    except Exception as e:
        print(f"⚠️ Warning: Failed to save resolution to memory: {e}")
        
    return incident_result
