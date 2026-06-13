from config import call_llm

try:
    print("Calling LLM...")
    response = call_llm("Say hello and confirm you are working.", system="You are a helpful assistant.")
    print("\n--- LLM Response ---")
    print(response)
    print("--------------------")
    print("Phase 0 checkpoint PASSED!")
except Exception as e:
    print(f"Error occurred during LLM call: {e}")
    print("Phase 0 checkpoint FAILED. Please check your .env file and API keys.")
