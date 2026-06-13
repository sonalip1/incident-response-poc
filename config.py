import os
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

PROVIDER = os.getenv("LLM_PROVIDER", "groq")  # "gemini" | "groq" | "anthropic"

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def call_llm(prompt: str, system: str = "", max_tokens: int = 1024) -> str:
    """Single entry point for all LLM calls with automated tenacity retries."""

    if PROVIDER == "gemini":
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment variables.")
        genai.configure(api_key=api_key)
        # Using gemini-2.5-flash or gemini-2.0-flash. The plan specifies gemini-2.0-flash.
        # Let's use gemini-2.0-flash as specified, or we can use gemini-2.5-flash.
        model_name = "gemini-2.0-flash"
        model = genai.GenerativeModel(model_name, system_instruction=system)
        
        # Adjust generation config for max_tokens if needed
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=max_tokens
        )
        response = model.generate_content(prompt, generation_config=generation_config)
        return response.text

    elif PROVIDER == "groq":
        from groq import Groq
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    elif PROVIDER == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model="claude-3-5-sonnet-latest",  # Claude 3.5 Sonnet
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {PROVIDER}")
