import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import call_llm
from agents.classifier import clean_json_string

def analyze(log_text: str, classification: dict) -> dict:
    """
    Analyzes generic system logs as a general site reliability / systems engineer.
    Returns: {"severity": int, "owner_team": str, "suggested_fix": [list of steps], "confidence": float}
    """
    system_prompt = (
        "You are a general systems reliability engineer. Your task is to analyze the provided log block and "
        "classification metadata which could not be clearly assigned to a specific expert agent.\n"
        "Analyze the logs and return a JSON object with the following fields:\n"
        "- \"severity\": an integer from 1 to 5 indicating the severity\n"
        "- \"owner_team\": the team that should triage this issue (e.g. \"On-Call Engineer\", \"Ops Triage\")\n"
        "- \"suggested_fix\": a list of strings representing general suggestions or troubleshooting steps to investigate further\n"
        "- \"confidence\": a float from 0.0 to 1.0 representing your confidence in this analysis\n\n"
        "Crucial instructions:\n"
        "1. Return ONLY the JSON object. Do not include any explanations or markdown formatting outside the JSON block."
    )
    
    prompt = f"Classification Metadata: {json.dumps(classification)}\n\nLog text to analyze:\n{log_text}"
    
    try:
        raw_response = call_llm(prompt=prompt, system=system_prompt)
        cleaned_response = clean_json_string(raw_response)
        result = json.loads(cleaned_response)
        
        required_keys = ["severity", "owner_team", "suggested_fix", "confidence"]
        for key in required_keys:
            if key not in result:
                raise ValueError(f"Missing required key in expert response: {key}")
                
        result["severity"] = int(result["severity"])
        result["confidence"] = float(result["confidence"])
        if not isinstance(result["suggested_fix"], list):
            result["suggested_fix"] = [str(result["suggested_fix"])]
            
        return result
    except Exception as e:
        return {
            "severity": classification.get("severity", 3),
            "owner_team": "On-Call Engineer",
            "suggested_fix": [f"Generic SRE failed to analyze. Error: {str(e)}"],
            "confidence": 0.0
        }
