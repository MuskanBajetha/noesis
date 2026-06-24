import re

CONFUSION_PHRASES = [
    "i don't know", "i dont know", "idk", "no idea", "not sure",
    "i'm confused", "im confused", "i am confused", "can you explain",
    "i'm stuck", "im stuck", "i am stuck", "no clue", "not certain",
    "i have no idea", "explain please", "can you help", "i give up",
    "don't understand", "dont understand", "do not understand",
    "what does this mean", "huh", "what", "?",
]

COMMON_KEYBOARD_MASHES = [
    "qwerty", "asdf", "qwertyuiop", "zxcvbn", "asdfghjkl", "hjkl",
]


def classify_response(text: str) -> dict:
    """
    Classifies a student's submission BEFORE any LLM call.

    Returns one of:
    - "genuine": looks like a real attempt, proceed to LLM evaluation normally
    - "confusion": explicit "I don't know" type response, skip straight to a hint
    - "gibberish": low-effort/nonsense, reject and ask for a real response

    This is intentionally rule-based, not an LLM call — gibberish detection
    doesn't need a model, and skipping the LLM here is the actual token saving.
    """
    cleaned = text.strip().lower()

    if not cleaned:
        return {"category": "gibberish", "reason": "empty"}

    # Category B check first — confusion phrases are legitimate, not low-effort
    for phrase in CONFUSION_PHRASES:
        if phrase in cleaned:
            return {"category": "confusion", "reason": f"matched phrase: {phrase}"}

    # Too short to be a genuine attempt at almost anything
    alpha_only = re.sub(r"[^a-z]", "", cleaned)
    if len(alpha_only) <= 2:
        return {"category": "gibberish", "reason": "too short"}

    # Pure repeated character (e.g. "hshshshsh", "aaaaaa", "......")
    if len(set(cleaned.replace(" ", ""))) <= 2 and len(cleaned) > 3:
        return {"category": "gibberish", "reason": "repeated characters"}

    # Common keyboard-mash patterns
    if any(mash in cleaned for mash in COMMON_KEYBOARD_MASHES):
        return {"category": "gibberish", "reason": "keyboard mash pattern"}

    # Vowel ratio check — real English/most languages' romanized text has a
    # reasonably high vowel density; "dgdhfbndhgvcfvb" has almost none
    if len(alpha_only) >= 5:
        vowels = sum(1 for c in alpha_only if c in "aeiou")
        vowel_ratio = vowels / len(alpha_only)
        if vowel_ratio < 0.12:
            return {"category": "gibberish", "reason": "abnormally low vowel ratio"}

    # Mostly digits/symbols with no real words (e.g. "123", "%%%%%")
    word_chars = sum(1 for c in cleaned if c.isalpha())
    total_chars = len(cleaned.replace(" ", ""))
    if total_chars > 0 and (word_chars / total_chars) < 0.4:
        return {"category": "gibberish", "reason": "mostly non-alphabetic"}

    return {"category": "genuine", "reason": None}