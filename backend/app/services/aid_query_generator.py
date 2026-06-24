import json
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"


def generate_aid_queries(topic_name: str, question: str, enabled_aids: list[str]) -> dict:
    """
    For each enabled aid, generates ONLY the query/expression content needed
    to render it — never decides WHETHER to include it (the backend always
    includes every enabled aid; this function just fills in the content).

    Returns a dict keyed by aid type, each value shaped for its renderer:
    {
      "diagram": "graph TD\\n A-->B",
      "plot": {"expression": "x**2", "x_min": -10, "x_max": 10, "title": "...", ...},
      "image": "search query string",
      "video": "search query string",
    }
    Any aid that genuinely cannot apply (e.g. a plot for a non-mathematical
    topic) returns null for that key — but diagram/image/video almost always
    have SOME reasonable angle, so nulls should be rare.
    """
    if not enabled_aids:
        return {}

    sections = []
    if "diagram" in enabled_aids:
        sections.append('"diagram": a Mermaid graph definition (just the body, no ```), e.g. "graph TD\\n A[Concept] --> B[Related idea]". If a flow/structure genuinely does not apply, use null.')
    if "plot" in enabled_aids:
        sections.append('"plot": {"expression": "valid Python math expression using x, +, -, *, /, **, sin, cos, tan, sqrt, exp, log, abs, pi", "x_min": number, "x_max": number, "title": "string", "x_label": "string", "y_label": "string"}. If no mathematical function relates to this topic at all, use null.')
    if "image" in enabled_aids:
        sections.append('"image": a SHORT search phrase (2-4 words MAX) likely to match a real Wikimedia Commons file title — think like a search engine query, not a descriptive sentence. Favor the most well-known, generic name for the subject (e.g. "Isaac Newton portrait", "Indus Valley sculpture", "neuron diagram") over long, specific descriptions. Wikimedia search is literal keyword matching, not semantic — shorter and more generic finds more results.')
    if "video" in enabled_aids:
        sections.append('"video": a specific search phrase for an explainer video on this topic.')

    prompt = f"""Topic: {topic_name}
Question being explained: {question}

Generate content for these visual aids. For each, provide genuinely relevant content tied to THIS topic — do not generate generic placeholders.

{chr(10).join(sections)}

Return ONLY a JSON object with exactly these keys: {enabled_aids}
Example shape: {{"diagram": "...", "plot": {{...}}}}  (only include keys for: {enabled_aids})"""

    response = client.chat.completions.create(
        model=MODEL, messages=[{"role": "user", "content": prompt}],
        temperature=0.4, max_tokens=400
    )

    raw = response.choices[0].message.content.strip()
    print(f"[AID DEBUG] Raw LLM response for aid queries:\n{raw}")
    try:
        cleaned = raw
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        result = json.loads(cleaned)
        print(f"[AID DEBUG] Parsed aid content: {result}")
        return result
    except Exception as e:
        print(f"[AID DEBUG] Failed to parse aid queries JSON: {e}")
        return {}