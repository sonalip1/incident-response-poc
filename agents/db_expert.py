import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import call_llm
from agents.classifier import clean_json_string
from tools.memory import get_similar_incidents

def analyze(log_text: str, classification: dict, critique: str = None) -> dict:
    """
    Analyzes database logs as a senior database engineer.
    Uses similar past incidents retrieved from ChromaDB to guide its analysis.
    If a critique is provided, uses it to improve the output.
    Returns: {"severity": int, "owner_team": str, "suggested_fix": [list of steps], "confidence": float}
    """
    system_prompt = (
        "You are a senior database engineer. Focus on database connection pools, locks, replication, queries, "
        "and database-related issues.\n"
        "Analyze the provided log block and classification metadata, then return a JSON object with the following fields:\n"
        "- \"severity\": an integer from 1 to 5 indicating the severity (can adjust initial classification severity if needed)\n"
        "- \"owner_team\": the team responsible for this issue (e.g. \"DBA\", \"Platform Engineering\", \"Backend Team\")\n"
        "- \"suggested_fix\": a list of strings representing specific actionable steps to resolve the database issue. "
        "If a past incident from the provided history was helpful and has the same resolution, explicitly prefix or add a note "
        "in that step stating that it leverages a historical resolution (e.g., '[Leveraged from DB History]: ...').\n"
        "- \"confidence\": a float from 0.0 to 1.0 representing your confidence in this analysis\n\n"
        "Crucial instructions:\n"
        "1. Return ONLY the JSON object. Do not include any explanations or markdown formatting outside the JSON block."
    )
    
    # Retrieve relevant database incidents from memory
    similar = get_similar_incidents(log_text, category="database", n=2)
    similar_text = "\n".join([f"- {doc}" for doc in similar]) if similar else "No similar incidents found in history."
    
    prompt = (
        f"Classification Metadata: {json.dumps(classification)}\n\n"
        f"Here are similar past incidents and how they were resolved:\n{similar_text}\n\n"
        f"Log text to analyze:\n{log_text}"
    )
    if critique:
        prompt += f"\n\nCRITIQUE OF PREVIOUS ATTEMPT (Please revise the suggested_fix to address this): {critique}"
    
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
            
        # Add the leveraged history directly to the returned dict
        result["leveraged_history"] = similar
        return result
    except Exception as e:
        return {
            "severity": classification.get("severity", 3),
            "owner_team": "DBA",
            "suggested_fix": [f"Database expert failed to analyze. Error: {str(e)}"],
            "confidence": 0.0,
            "leveraged_history": similar
        }
