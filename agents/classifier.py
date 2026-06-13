import json
import re
import sys
import os

# Add parent directory to sys.path so we can import from config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import call_llm

def clean_json_string(text: str) -> str:
    """Strips markdown code fences and extraneous text before/after the JSON block."""
    text = text.strip()
    # Remove markdown code block fences if present
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        text = match.group(1).strip()
    return text

def classify_log(log_text: str) -> dict:
    """
    Classifies log text by calling call_llm.
    Returns a dictionary with:
    - severity (int: 1-5)
    - category (str: database|network|application|unknown)
    - root_cause (str)
    - confidence (float: 0.0-1.0)
    """
    system_prompt = (
        "You are an expert system reliability and DevOps engineer. "
        "Your task is to analyze the provided log block and output a JSON object with the following fields:\n"
        "- \"severity\": an integer from 1 to 5 (1 being most severe, 5 being least)\n"
        "- \"category\": one of \"database\", \"network\", \"application\", or \"unknown\"\n"
        "- \"root_cause\": a brief string describing the likely root cause of the log messages\n"
        "- \"confidence\": a float from 0.0 to 1.0 representing your confidence in this analysis\n\n"
        "Crucial instructions:\n"
        "1. Return ONLY the JSON object. Do not include any explanation or markdown formatting outside the JSON block.\n"
        "2. Do not wrap the response in standard text, write only the JSON."
    )
    
    prompt = f"Analyze the following log block:\n\n{log_text}"
    
    try:
        raw_response = call_llm(prompt=prompt, system=system_prompt)
        cleaned_response = clean_json_string(raw_response)
        result = json.loads(cleaned_response)
        
        # Validate required keys and types
        required_keys = ["severity", "category", "root_cause", "confidence"]
        for key in required_keys:
            if key not in result:
                raise ValueError(f"Missing required key in LLM response: {key}")
        
        # Normalize/validate values
        result["severity"] = int(result["severity"])
        result["confidence"] = float(result["confidence"])
        
        valid_categories = {"database", "network", "application", "unknown"}
        if result["category"] not in valid_categories:
            result["category"] = "unknown"
            
        return result
        
    except Exception as e:
        # Fallback dictionary on failure
        return {
            "severity": 3,
            "category": "unknown",
            "root_cause": f"Failed to parse LLM response. Error: {str(e)}",
            "confidence": 0.0
        }
