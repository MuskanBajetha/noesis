import json
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"


def extract_topics_from_text(text: str, subject_name: str, max_topics: int = 8) -> list[dict]:
    """
    Read uploaded material and propose a clean list of topics/subtopics.
    Returns [{"name": "...", "description": "..."}], capped at max_topics.
    """
    # Keep the prompt bounded — use a representative slice, not the whole document
    sample = text[:6000]

    prompt = f"""You are analyzing learning material for a subject called "{subject_name}".

Read this excerpt and identify the {max_topics} most important distinct topics or subtopics
a student should learn from it. Topics should be specific concepts (e.g. "Newton's Second Law",
"President", "Linear Regression") — not vague categories (e.g. "Physics Basics", "Chapter 1").

Material excerpt:
{sample}

Return a JSON array of exactly this shape, nothing else:
[
  {{"name": "Topic Name", "description": "one sentence on what this covers"}},
  ...
]"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=600
    )

    try:
        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if the model adds them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        topics = json.loads(raw)
        return topics[:max_topics]
    except Exception:
        # Fallback: a single general topic so the flow never hard-fails
        return [{"name": subject_name, "description": f"General concepts in {subject_name}"}]


def suggest_topic_relationships(topics: list[str]) -> list[tuple[str, str]]:
    """
    Given a flat topic list for ONE subject, ask the LLM which pairs are
    meaningfully related — powers the concept graph edges.
    """
    if len(topics) < 2:
        return []

    topic_list_str = "\n".join(f"- {t}" for t in topics)

    prompt = f"""Here are topics within a single subject:
{topic_list_str}

Identify which pairs of topics are meaningfully related (one helps understand the other).
Return a JSON array of pairs, nothing else:
[["Topic A", "Topic B"], ["Topic C", "Topic D"]]

Only include genuinely related pairs. A topic doesn't need to connect to every other topic."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=400
    )

    try:
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        pairs = json.loads(raw)
        return [(p[0], p[1]) for p in pairs if len(p) == 2]
    except Exception:
        return []