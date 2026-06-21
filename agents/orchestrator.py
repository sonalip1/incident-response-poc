import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.classifier import classify_log
from agents import db_expert
from agents import network_expert
from agents import app_expert
from agents import generic_handler
from agents import reflector
from agents import hitl_gate

def route_incident(log_text: str) -> dict:
    """
    Triage and route log incidents to the appropriate expert agent.
    1. Classifies log_text with fallback on exception.
    2. Routes to database, network, application, or fallback handler.
    3. Triggers fallback to generic_handler if expert fails or confidence < 0.5.
    4. Runs reflection critique and one-time rewrite loop if critique score < 6.
    5. Pauses for human approval gate for Sev-1/2 incidents.
    6. Writes resolved incidents to database memory.
    """
    # 1. Classify the log (with fallback on failure)
    try:
        classification = classify_log(log_text)
    except Exception as e:
        classification = {
            "severity": 3,
            "category": "unknown",
            "root_cause": f"Classifier failed: {str(e)}",
            "confidence": 0.0
        }
        
    category = classification.get("category", "unknown")
    expert_name = None
    analysis = None
    status = "failed"
    reflection_info = None
    
    # 2. Map to expert or fallback directly if unknown
    if category in ["database", "network", "application"]:
        if category == "database":
            expert_module = db_expert
            expert_name = "db_expert"
        elif category == "network":
            expert_module = network_expert
            expert_name = "network_expert"
        else:
            expert_module = app_expert
            expert_name = "app_expert"
            
        try:
            # Call expert (Attempt 1)
            analysis = expert_module.analyze(log_text, classification)
            
            # Check confidence threshold for fallback
            if analysis.get("confidence", 1.0) >= 0.5:
                status = "resolved_by_expert"
                
                # Run Reflector Critique (only if expert succeeded)
                try:
                    critique_res = reflector.review_plan(log_text, analysis)
                    score = critique_res.get("score", 10)
                    critique = critique_res.get("critique", "")
                    
                    reflection_info = {"attempt_1_score": score, "critique": critique}
                    
                    if score < 6:
                        print(f"\n🔍 [Reflector] Score was low ({score}/10). Critique: {critique}")
                        print(f"🔄 [Reflector] Looping back to {expert_name} for a revised resolution plan...")
                        
                        # Re-run expert with critique feedback (Attempt 2)
                        revised_analysis = expert_module.analyze(log_text, classification, critique=critique)
                        
                        # Run final critique on revised output
                        final_critique = reflector.review_plan(log_text, revised_analysis)
                        reflection_info["final_score"] = final_critique.get("score")
                        reflection_info["final_critique"] = final_critique.get("critique")
                        
                        # Keep revised analysis if confidence is still good
                        if revised_analysis.get("confidence", 1.0) >= 0.5:
                            analysis = revised_analysis
                            
                except Exception as ref_exc:
                    print(f"⚠️ Warning: Reflector failed: {ref_exc}")
            else:
                print(f"[Circuit Breaker] Expert {expert_name} returned low confidence ({analysis.get('confidence')}). Falling back to generic_handler.")
                analysis = generic_handler.analyze(log_text, classification)
                status = "resolved_by_fallback"
        except Exception as exc:
            print(f"[Circuit Breaker] Expert {expert_name} failed: {exc}. Falling back to generic_handler.")
            try:
                analysis = generic_handler.analyze(log_text, classification)
                status = "resolved_by_fallback"
            except Exception as fallback_exc:
                print(f"[Fallback Failed] generic_handler also failed: {fallback_exc}")
                analysis = {
                    "severity": classification.get("severity", 3),
                    "owner_team": "On-Call Engineer",
                    "suggested_fix": ["Critical System Failure: Both expert and fallback agents failed to analyze."],
                    "confidence": 0.0
                }
                status = "failed"
    else:
        # Route to generic_handler directly
        expert_name = "generic_handler"
        try:
            analysis = generic_handler.analyze(log_text, classification)
            status = "resolved_by_fallback"
        except Exception as exc:
            print(f"[Fallback Failed] generic_handler failed: {exc}")
            analysis = {
                "severity": classification.get("severity", 3),
                "owner_team": "On-Call Engineer",
                "suggested_fix": ["Critical System Failure: Fallback agent failed to analyze."],
                "confidence": 0.0
            }
            status = "failed"
            
    # Assemble intermediate result
    incident_result = {
        "status": status,
        "classification": classification,
        "expert_handler": expert_name,
        "analysis": analysis
    }
    if reflection_info:
        incident_result["reflection"] = reflection_info
        
    # 3. Human Approval Gate & Memory Write-back
    final_result = hitl_gate.human_approval_gate(log_text, incident_result)
    return final_result


async def route_incident_streaming(log_text: str, incident_id: str = None, hitl_event: str = None, hitl_decision_dict: dict = None):
    """
    Async generator version of the incident response pipeline.
    Yields event dictionaries after each step:
    - 'classification'
    - 'rag_retrieval'
    - 'expert_analysis'
    - 'reflection'
    - 'hitl_required' (if Sev-1/2, then pauses awaiting hitl_event)
    - 'complete'
    """
    import asyncio
    from tools.memory import get_similar_incidents, save_resolution
    
    # 1. Classify the log
    try:
        classification = classify_log(log_text)
    except Exception as e:
        classification = {
            "severity": 3,
            "category": "unknown",
            "root_cause": f"Classifier failed: {str(e)}",
            "confidence": 0.0
        }
    yield {"step": "classification", "data": classification}
    
    category = classification.get("category", "unknown")
    severity = classification.get("severity", 3)
    expert_name = None
    analysis = None
    status = "failed"
    reflection_info = None
    
    # 2. Retrieve RAG memory
    similar = []
    if category in ["database", "network", "application"]:
        try:
            similar = get_similar_incidents(log_text, category=category, n=2)
        except Exception as e:
            print(f"⚠️ Warning: RAG retrieval failed: {e}")
    yield {"step": "rag_retrieval", "data": {"category": category, "incidents": similar}}
    
    # 3. Call Expert or fallback
    if category in ["database", "network", "application"]:
        if category == "database":
            expert_module = db_expert
            expert_name = "db_expert"
        elif category == "network":
            expert_module = network_expert
            expert_name = "network_expert"
        else:
            expert_module = app_expert
            expert_name = "app_expert"
            
        try:
            # Call expert (Attempt 1)
            analysis = expert_module.analyze(log_text, classification)
            yield {"step": "expert_analysis", "data": {"expert_handler": expert_name, "analysis": analysis, "attempt": 1}}
            
            # Check confidence threshold for fallback
            if analysis.get("confidence", 1.0) >= 0.5:
                status = "resolved_by_expert"
                
                # Run Reflector Critique
                try:
                    critique_res = reflector.review_plan(log_text, analysis)
                    score = critique_res.get("score", 10)
                    critique = critique_res.get("critique", "")
                    
                    reflection_info = {"attempt_1_score": score, "critique": critique}
                    yield {"step": "reflection", "data": reflection_info}
                    
                    if score < 6:
                        # Re-run expert with critique feedback (Attempt 2)
                        revised_analysis = expert_module.analyze(log_text, classification, critique=critique)
                        
                        # Run final critique on revised output
                        final_critique = reflector.review_plan(log_text, revised_analysis)
                        reflection_info["final_score"] = final_critique.get("score")
                        reflection_info["final_critique"] = final_critique.get("critique")
                        
                        # Keep revised analysis if confidence is still good
                        if revised_analysis.get("confidence", 1.0) >= 0.5:
                            analysis = revised_analysis
                        
                        yield {"step": "expert_analysis", "data": {"expert_handler": expert_name, "analysis": analysis, "attempt": 2}}
                        yield {"step": "reflection", "data": reflection_info}
                            
                except Exception as ref_exc:
                    print(f"⚠️ Warning: Reflector failed: {ref_exc}")
            else:
                expert_name = "generic_handler"
                analysis = generic_handler.analyze(log_text, classification)
                status = "resolved_by_fallback"
                yield {"step": "expert_analysis", "data": {"expert_handler": expert_name, "analysis": analysis, "fallback_reason": "low_confidence"}}
        except Exception as exc:
            expert_name = "generic_handler"
            try:
                analysis = generic_handler.analyze(log_text, classification)
                status = "resolved_by_fallback"
            except Exception as fallback_exc:
                analysis = {
                    "severity": severity,
                    "owner_team": "On-Call Engineer",
                    "suggested_fix": ["Critical System Failure: Both expert and fallback agents failed to analyze."],
                    "confidence": 0.0
                }
                status = "failed"
            yield {"step": "expert_analysis", "data": {"expert_handler": expert_name, "analysis": analysis, "fallback_reason": f"error: {str(exc)}"}}
    else:
        expert_name = "generic_handler"
        try:
            analysis = generic_handler.analyze(log_text, classification)
            status = "resolved_by_fallback"
        except Exception as exc:
            analysis = {
                "severity": severity,
                "owner_team": "On-Call Engineer",
                "suggested_fix": ["Critical System Failure: Fallback agent failed to analyze."],
                "confidence": 0.0
            }
            status = "failed"
        yield {"step": "expert_analysis", "data": {"expert_handler": expert_name, "analysis": analysis, "reason": "unknown_category"}}
        
    # Assemble intermediate result
    incident_result = {
        "status": status,
        "classification": classification,
        "expert_handler": expert_name,
        "analysis": analysis
    }
    if reflection_info:
        incident_result["reflection"] = reflection_info
        
    # 4. Human Approval Gate (HITL)
    if severity <= 2:
        yield {"step": "hitl_required", "data": incident_result}
        
        # Pause execution if an asyncio Event is provided
        if hitl_event is not None and hitl_decision_dict is not None and incident_id is not None:
            print(f"[Streaming Orchestrator] Pausing pipeline for incident {incident_id} awaiting approval...")
            await hitl_event.wait()
            approved = hitl_decision_dict.get(incident_id, False)
            if not approved:
                print(f"[Streaming Orchestrator] Incident {incident_id} rejected by user.")
                incident_result["status"] = "rejected_by_human"
                yield {"step": "complete", "data": incident_result}
                return
            print(f"[Streaming Orchestrator] Incident {incident_id} approved by user.")
        else:
            # Fallback for CLI/Direct tests (auto-approve or non-interactive fallback)
            print("[Streaming Orchestrator] No hitl_event context provided, auto-approving for stream.")
            
    # Write to memory on approval/auto-pass
    try:
        save_resolution(log_text, analysis)
    except Exception as e:
        print(f"⚠️ Warning: Failed to save resolution to memory: {e}")
        
    yield {"step": "complete", "data": incident_result}
