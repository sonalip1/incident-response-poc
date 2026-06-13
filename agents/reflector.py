import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import call_llm
from agents.classifier import clean_json_string

def review_plan(log_text: str, analysis: dict) -> dict:
    """
    Critiques the proposed fix from the expert agent.
    Returns: {"score": int (1-10), "critique": str}
    """
    system_prompt = (
        "You are a critical Site Reliability and QA Engineer.\n"
        "Your task is to review the proposed suggested fix for a system incident log.\n"
        "Critique the suggested fix based on the following criteria:\n"
        "- Is this fix specific enough? (e.g. does it name specific configuration variables, tools, or procedures?)\n"
        "- Does it address the likely root cause directly, or is it just addressing symptoms?\n"
        "- Are the steps actionable and clear?\n\n"
        "Return a JSON object with the following fields:\n"
        "- \"score\": an integer from 1 to 10 (10 being perfect, < 6 means needs rewrite/additional detail)\n"
        "- \"critique\": a detailed explanation of why the score was given, highlighting any shortcomings or areas of improvement.\n\n"
        "Crucial instructions:\n"
        "1. Return ONLY the JSON object. Do not include any explanations or markdown formatting outside the JSON block."
    )
    
    prompt = (
        f"Input Incident Log:\n{log_text}\n\n"
        f"Proposed Expert Analysis:\n{json.dumps(analysis, indent=2)}"
    )
    
    try:
        raw_response = call_llm(prompt=prompt, system=system_prompt)
        cleaned_response = clean_json_string(raw_response)
        result = json.loads(cleaned_response)
        
        required_keys = ["score", "critique"]
        for key in required_keys:
            if key not in result:
                raise ValueError(f"Missing required key in critique response: {key}")
                
        result["score"] = int(result["score"])
        result["critique"] = str(result["critique"])
        return result
    except Exception as e:
        # Fallback critique
        return {
            "score": 5,
            "critique": f"Reflector failed to critique. Error: {str(e)}"
        }
