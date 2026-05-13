import re
from llm_client import call_llm
from ddgs import DDGS

# Hardcoded Tier 1 — sexual abuse/trafficking criminals, always blocked
KNOWN_TIER1 = [
    "jeffrey epstein", "epstein",
    "diddy", "sean combs", "p diddy", "puff daddy",
    "r kelly", "r. kelly",
    "harvey weinstein",
    "d4vd", "david anthony burke",
]

# Known historical figures — school curriculum, always allowed
KNOWN_HISTORICAL = [
    "adolf hitler", "hitler",
    "joseph stalin", "stalin",
    "benito mussolini", "mussolini",
    "napoleon", "napoleon bonaparte",
    "genghis khan",
    "mao zedong", "mao tse-tung",
    "pol pot",
    "idi amin",
    "nero", "caligula",
    "vlad the impaler",
    "attila the hun",
]

# Words that indicate a description, not a real name
DESCRIPTION_WORDS = [
    "the main", "the worst", "the best", "the biggest",
    "the villain", "the bad guy", "the good guy",
    "responsible for", "person in", "guy in", "character in",
    "leader of", "president of", "king of", "queen of",
]

VAGUE_PRONOUNS = ["that", "this", "it", "them", "him", "her", "they"]

def is_public_figure_question(message):
    msg = message.lower()
    patterns = [
        r"who is (.+?)\??$",
        r"who was (.+?)\??$",
        r"what did (.+?) do",
        r"tell me about (.+?)\??$",
        r"why is (.+?) famous",
        r"why was (.+?) famous",
        r"have you heard of (.+?)\??$",
        r"do you know (.+?)\??$",
        r"can you tell me about (.+?)\??$",
        r"can you tell me more about (.+?)\??$",
    ]
    for pattern in patterns:
        match = re.search(pattern, msg)
        if match:
            return True, match.group(1).strip()
    return False, None

def is_real_name(name):
    """Check if extracted string looks like a real name vs a description."""
    name_lower = name.lower().strip()
    # Single vague pronoun
    if name_lower in VAGUE_PRONOUNS:
        return False
    if len(name_lower.split()) > 5:
        return False
    for phrase in DESCRIPTION_WORDS:
        if phrase in name_lower:
            return False
    return True

def search_person(name):
    """Search web for information about a person."""
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(f"{name} news crime controversy", max_results=5):
                results.append(r.get("body", "")[:300])
        return " ".join(results)
    except Exception as e:
        return ""

def classify_figure(name):
    name_lower = name.lower().strip()

    # Check hardcoded Tier 1 first (sexual/abuse criminals)
    for known in KNOWN_TIER1:
        if known in name_lower or name_lower in known:
            return 1, "Known Tier 1 - hardcoded (abuse/trafficking)"

    # Check known historical figures (school curriculum)
    for known in KNOWN_HISTORICAL:
        if known in name_lower or name_lower in known:
            return 3, "Known historical figure - school curriculum"

    # Check if this looks like a description not a name
    if not is_real_name(name):
        return 3, "Not a real name - description phrase"

    # Unknown person - use web search + Claude Haiku to classify
    try:

        # Search for current information
        search_results = search_person(name)

        prompt = f"""You are a child safety classifier for a kids AI assistant (ages 7-12).

A child is asking about: "{name}"

Here is current information from the web about this person:
{search_results if search_results else "No search results found."}

Your job is to decide if this person is safe for a child aged 7-12 to learn about.

Reply BLOCK if the person:
- Has been convicted of, charged with, or is strongly associated with serious crimes
- Is primarily known for sexual abuse, trafficking, violence, or deeply disturbing behavior
- Would expose a child to deeply inappropriate or disturbing content

Reply ALLOW if the person:
- Is mainly known for legitimate work (music, acting, sports, politics, business)
- Is a historical figure studied in school (even if they did bad things in history)
- Has some controversy but is not primarily known for criminal behavior

Reply with ONLY one word: BLOCK or ALLOW."""

        answer = call_llm(prompt, max_tokens=10).upper()
        print(f"[Classifier] {name} → Claude says: {answer}")

        if "BLOCK" in answer:
            return 1, "Claude Haiku + web search classified as Tier 1"
        else:
            return 3, "Claude Haiku + web search classified as safe"

    except Exception as e:
        print(f"[Classifier] Error: {e}")
        return 3, "Classification failed, defaulting to safe"
