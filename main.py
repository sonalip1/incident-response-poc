import os
import sys
import argparse
import re
import json

from tools.memory import seed_memory
from agents.orchestrator import route_incident
from tests.test_classifier import load_sample_logs

def parse_args():
    parser = argparse.ArgumentParser(description="Multi-Agent Incident Response Demo Runner")
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed the ChromaDB memory with historical logs before running analysis"
    )
    return parser.parse_args()

def print_separator(char="=", length=80):
    print(char * length)

def main():
    args = parse_args()
    
    if args.seed:
        print("🌱 Seeding ChromaDB memory with historical logs...")
        try:
            seed_memory()
        except Exception as e:
            print(f"❌ Error seeding database: {e}")
            sys.exit(1)
        print("🌱 Seeding completed.\n")
        
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logs_path = os.path.join(base_dir, "data", "sample_logs.txt")
    
    if not os.path.exists(logs_path):
        print(f"❌ Error: Sample logs not found at {logs_path}")
        sys.exit(1)
        
    print(f"Reading logs from: {logs_path}")
    try:
        incidents = load_sample_logs(logs_path)
    except Exception as e:
        print(f"❌ Error parsing sample logs: {e}")
        sys.exit(1)
        
    print(f"Loaded {len(incidents)} incident logs. Beginning analysis...\n")
    
    summary_data = []
    
    for idx, (header, log_body) in enumerate(incidents, start=1):
        print_separator("=", 80)
        print(f"INCIDENT #{idx}: {header}")
        print_separator("-", 80)
        print(log_body)
        print_separator("-", 80)
        
        # Run orchestrator dynamic routing
        result = route_incident(log_body)
        
        classification = result.get("classification", {})
        analysis = result.get("analysis", {})
        reflection = result.get("reflection", {})
        
        print(f"Routed To      : {result.get('expert_handler')}")
        print(f"Triage Status  : {result.get('status')}")
        print(f"Detected Sev   : SEV-{classification.get('severity', 3)}")
        print(f"Responsible    : {analysis.get('owner_team', 'N/A')}")
        
        # Show Reflection if it happened
        if reflection:
            score1 = reflection.get("attempt_1_score")
            final_score = reflection.get("final_score")
            if final_score is not None:
                print(f"Reflection     : Attempt 1 score: {score1}/10 ➡️ Revised score: {final_score}/10")
            else:
                print(f"Reflection     : Approved on attempt 1 (Score: {score1}/10)")
                
        print("\nSuggested Actionable Steps:")
        for step_idx, step in enumerate(analysis.get("suggested_fix", []), 1):
            print(f"  {step_idx}. {step}")
            
        print_separator("=", 80)
        print("\n")
        
        # Save for summary table
        clean_title = header.replace("# ──", "").replace(" ──", "").strip()
        # Truncate title if too long
        if len(clean_title) > 30:
            clean_title = clean_title[:27] + "..."
            
        summary_data.append({
            "title": clean_title,
            "severity": classification.get("severity", 3),
            "category": classification.get("category", "unknown"),
            "status": result.get("status"),
            "confidence": analysis.get("confidence", 0.0)
        })
        
    # Print final summary table
    print_separator("=", 80)
    print("FINAL SUMMARY REPORT")
    print_separator("=", 80)
    
    header_fmt = "{:<30} | {:<8} | {:<12} | {:<20} | {:<10}"
    row_fmt =    "{:<30} | SEV-{:<4} | {:<12} | {:<20} | {:.2f}"
    
    print(header_fmt.format("Incident Title", "Severity", "Category", "Status", "Confidence"))
    print_separator("-", 80)
    
    for row in summary_data:
        print(row_fmt.format(
            row["title"],
            row["severity"],
            row["category"],
            row["status"],
            row["confidence"]
        ))
        
    print_separator("=", 80)
    print()

if __name__ == "__main__":
    main()
