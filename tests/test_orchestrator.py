import os
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.orchestrator import route_incident
from tests.test_classifier import load_sample_logs

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logs_path = os.path.join(base_dir, "data", "sample_logs.txt")
    
    print(f"Loading sample logs from {logs_path}...")
    try:
        incidents = load_sample_logs(logs_path)
    except Exception as e:
        print(f"Error loading sample logs: {e}")
        sys.exit(1)
        
    print(f"Found {len(incidents)} incidents. Running Orchestration Routing...\n")
    
    for i, (header, body) in enumerate(incidents, start=1):
        print("=" * 80)
        print(f"Incident {i}: {header}")
        print("-" * 80)
        print(body)
        print("-" * 80)
        
        result = route_incident(body)
        print(f"Routed to: {result['expert_handler']}")
        
        # Highlight leveraged history in terminal output
        leveraged = result.get("analysis", {}).get("leveraged_history", [])
        if leveraged:
            print("\n🚨 [RAG ACTIVE] THIS FIX LEVERAGES THE FOLLOWING HISTORICAL RESOLUTIONS:")
            for item in leveraged:
                print(f"  👉 {item}")
            print()
            
        print("Final Triaged Analysis:")
        print(json.dumps(result, indent=2))
        print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
