import anthropic
from ddgs import DDGS

def needs_web_search(question):
    """Ask Claude Haiku if this question needs current/recent information."""
    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{
                "role": "user",
                "content": f"""Does this question require current, recent, or up-to-date information to answer accurately?

Question: "{question}"

Answer YES if the question asks about:
- Current events, recent news, or what's happening now
- Who currently holds a position (president, champion, record holder)
- Recent releases (movies, songs, games) from the last year
- Sports scores, standings, or recent results
- Latest discoveries or announcements

Answer NO if the question is about:
- Science facts, history, how things work
- Definitions or concepts
- Things that don't change over time

Reply with ONLY one word: YES or NO."""
            }]
        )
        answer = response.content[0].text.strip().upper()
        return answer.startswith("YES")
    except Exception as e:
        print(f"[WebSearch Router] Error: {e}")
        return False

def search_web(query, max_results=5):
    """Search DuckDuckGo and return results as a string."""
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                title = r.get("title", "")
                body = r.get("body", "")[:300]
                results.append(f"{title}: {body}")
        if results:
            return "\n\n".join(results)
        return ""
    except Exception as e:
        print(f"[WebSearch] Error: {e}")
        return ""

def get_web_context(question):
    """Full pipeline: decide if search needed, run search, return context."""
    if not needs_web_search(question):
        print(f"[WebSearch] No search needed for: {question[:50]}")
        return None

    print(f"[WebSearch] Searching for: {question[:50]}")
    results = search_web(question)

    if not results:
        print("[WebSearch] No results found")
        return None

    context = f"""IMPORTANT: The following are CURRENT web search results from today. Always trust these results over anything you already know — your training data may be outdated.

{results}

Use ONLY this current information to answer. If the results say someone is currently in a role, trust that over your training data. Answer in a warm, age-appropriate way for a child aged 7-12."""

    return context
