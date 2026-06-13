import os
import sys
import re
import json

# Add parent directory to sys.path so we can import agents
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.classifier import classify_log

def load_sample_logs(file_path: str):
    """Parses sample_logs.txt and returns list of (header, log_content) tuples."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Sample logs file not found at: {file_path}")
        
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Match headers starting with '# ──' and the body until the next header or end of file
    pattern = r'(# ──[^\n]+)\n([\s\S]*?)(?=(?:# ──|$))'
    matches = re.findall(pattern, content)
    
    return [(header.strip(), body.strip()) for header, body in matches]

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logs_path = os.path.join(base_dir, "data", "sample_logs.txt")
    
    print(f"Loading sample logs from {logs_path}...")
    try:
        incidents = load_sample_logs(logs_path)
    except Exception as e:
        print(f"Error loading sample logs: {e}")
        sys.exit(1)
        
    print(f"Found {len(incidents)} incidents. Running classification...\n")
    
    for i, (header, body) in enumerate(incidents, start=1):
        print("=" * 80)
        print(f"Incident {i}: {header}")
        print("-" * 80)
        print(body)
        print("-" * 80)
        
        result = classify_log(body)
        print("Classification Result:")
        print(json.dumps(result, indent=2))
        print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
