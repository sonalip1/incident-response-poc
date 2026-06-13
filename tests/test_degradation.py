import os
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.orchestrator import route_incident

def run_test(name: str, log_text: str):
    print("=" * 80)
    print(f"Testing Fallback: {name}")
    print(f"Input Log: {repr(log_text)}")
    print("-" * 80)
    
    try:
        result = route_incident(log_text)
        print("Result Status:", result.get("status"))
        print("Expert Handler:", result.get("expert_handler"))
        print("\nFull Triaged Output:")
        print(json.dumps(result, indent=2))
        
        # Verification checks
        assert result.get("status") == "resolved_by_fallback", f"Expected 'resolved_by_fallback' but got {result.get('status')}"
        print(f"\n✅ SUCCESS: test '{name}' degraded gracefully as expected.")
        
    except Exception as e:
        print(f"\n❌ FAILURE: test '{name}' raised an unhandled exception: {e}")
        sys.exit(1)
        
    print("=" * 80 + "\n")

def main():
    print("Starting Graceful Degradation & Fallback Tests...\n")
    
    # Test 1: Empty string
    run_test("Empty Log Text", "")
    
    # Test 2: Nonsense / Gibberish log
    run_test("Nonsense Log Text", "xyzabc123 random error system not working potato")
    
    print("All degradation tests completed successfully!")

if __name__ == "__main__":
    main()
