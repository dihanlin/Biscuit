import os

# Set these in your .env file:
#   LLM_PROVIDER = anthropic | openai | google
#   LLM_API_KEY  = your key
#   LLM_MODEL    = optional override (defaults shown below)

PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").lower()
API_KEY  = os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
MODEL    = os.getenv("LLM_MODEL")

DEFAULT_MODELS = {
    "anthropic": "claude-haiku-4-5-20251001",
    "openai":    "gpt-4o-mini",
    "google":    "gemini-1.5-flash",
}

def call_llm(prompt, max_tokens=100):
    model = MODEL or DEFAULT_MODELS.get(PROVIDER, "")

    if PROVIDER == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=API_KEY)
        response = client.messages.create(
            model=model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()

    elif PROVIDER == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=API_KEY)
        response = client.chat.completions.create(
            model=model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()

    elif PROVIDER == "google":
        import google.generativeai as genai
        genai.configure(api_key=API_KEY)
        m = genai.GenerativeModel(model)
        return m.generate_content(prompt).text.strip()

    else:
        raise ValueError(f"Unknown LLM_PROVIDER '{PROVIDER}'. Use: anthropic, openai, or google.")
