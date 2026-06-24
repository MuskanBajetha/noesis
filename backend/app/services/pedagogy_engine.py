import json
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

STAGES = ["recognition", "understanding", "application", "analysis", "synthesis", "mastery"]

STAGE_DESCRIPTIONS = {
    "recognition": "Can the student identify or recall the concept? (e.g. 'What is X?')",
    "understanding": "Can the student explain WHY the concept exists or matters? (e.g. 'Why does X happen?')",
    "application": "Can the student use the concept in a new, concrete scenario? (e.g. 'How would X behave if...?')",
    "analysis": "Can the student compare, contrast, or break the concept into its components against alternatives? (e.g. 'Compare X with Y')",
    "synthesis": "Can the student combine the concept with others to design or construct something new? (e.g. 'Design a strategy using X for...')",
    "mastery": "Can the student teach the concept to someone else and anticipate common misconceptions about it?",
}


def next_stage(current: str) -> str:
    idx = STAGES.index(current) if current in STAGES else 0
    return STAGES[min(idx + 1, len(STAGES) - 1)]


def generate_staged_question(topic_name: str, stage: str, context: str = "", avoid_questions: list = None) -> str:
    """
    Generate ONE question that specifically targets the given pedagogical stage.
    avoid_questions prevents repetition by showing the model what's already been asked.
    """
    avoid_block = ""
    if avoid_questions:
        avoid_block = "\n\nQuestions already asked on this topic (do NOT repeat or closely rephrase these):\n" + \
                      "\n".join(f"- {q}" for q in avoid_questions[-5:])

    context_block = f"\n\nGrounding material:\n{context}" if context else ""

    prompt = f"""You are a world-class Socratic tutor teaching "{topic_name}".

    Target pedagogical stage: {stage.upper()}
    What this stage requires: {STAGE_DESCRIPTIONS[stage]}

    Generate exactly ONE question that targets this specific stage — not easier, not harder.
    The question must have a clear pedagogical purpose tied to this stage's requirement.
    Never give the answer. Be concise (1-2 sentences).
    If the topic is mathematical or involves equations, write them in LaTeX using $...$ for inline math or $$...$$ for display math (e.g. $x^2 + y^2 = r^2$).{context_block}{avoid_block}

    Return only the question, nothing else:"""

    response = client.chat.completions.create(
        model=MODEL, messages=[{"role": "user", "content": prompt}],
        temperature=0.65, max_tokens=150
    )
    return response.choices[0].message.content.strip()


STAGE_PASS_CRITERIA = {
    "recognition": "The student correctly identifies or names the concept. A correct definition, even brief, PASSES.",
    "understanding": "The student explains the WHY or the reasoning behind the concept in their own words, even briefly. They do NOT need to derive it from scratch or give a perfect textbook definition — a correct, reasoned explanation PASSES, even if short.",
    "application": "The student correctly applies the concept to solve or reason through the specific scenario asked. A correct worked answer PASSES, even without extensive explanation.",
    "analysis": "The student correctly compares, contrasts, or breaks down the concept relative to something else. A correct comparison PASSES.",
    "synthesis": "The student combines the concept with something else to construct a coherent new idea or strategy. A reasonable, workable proposal PASSES.",
    "mastery": "The student explains the concept clearly enough that a beginner could follow it, OR correctly identifies a real misconception about it. Either alone PASSES.",
}


def evaluate_staged_response(question: str, stage: str, student_response: str, topic_name: str) -> dict:
    """
    Judges whether the response demonstrates the TARGETED stage's kind of thinking.
    Calibrated to be a fair, not harsh, grader: a correct and reasoned answer should
    PASS even if it isn't maximally elaborate. Only fail responses that are wrong,
    off-topic, or show no real reasoning at all.
    """
    prompt = f"""You are a fair, encouraging tutor evaluating one student answer. Default toward PASSING a correct answer — do not require more depth than the stage needs.

Topic: {topic_name}
Pedagogical stage being tested: {stage.upper()}
What PASSES at this stage: {STAGE_PASS_CRITERIA[stage]}

Question asked: {question}
Student's response: {student_response}

Evaluate ONLY against the pass criteria above. If the response is correct and meets that bar, it PASSES even if brief.
Only mark demonstrates_stage as false if the response is factually wrong, off-topic, or shows no real reasoning.

Return JSON only:
{{
  "demonstrates_stage": true/false,
  "understanding_level": "none/partial/good/excellent",
  "misconception_detected": true/false,
  "misconception_type": "string or null",
  "ready_to_advance": true/false,
  "feedback": "1-2 sentences. If passing, acknowledge what they got right before moving on. Never give the answer if not passing."
}}"""

    response = client.chat.completions.create(
        model=MODEL, messages=[{"role": "user", "content": prompt}],
        temperature=0.15, max_tokens=350
    )
    try:
        result = json.loads(response.choices[0].message.content.strip())
        # Safety net: if the model says "excellent" or "good" understanding but somehow
        # still marked demonstrates_stage false, trust the understanding_level instead —
        # it's a less ambiguous signal and prevents exactly the stuck-loop bug we saw.
        if result.get("understanding_level") in ("good", "excellent") and not result.get("demonstrates_stage"):
            result["demonstrates_stage"] = True
        return result
    except Exception:
        return {
            "demonstrates_stage": False, "understanding_level": "partial",
            "misconception_detected": False, "misconception_type": None,
            "ready_to_advance": False, "feedback": "Let's think about this a bit more."
        }


def generate_hint(question: str, stage: str, topic_name: str, attempt_number: int, student_response: str) -> str:
    """
    attempt_number: 1 = light hint, 2 = guided hint (more directive, narrows the path).
    """
    intensity = "a light nudge — point toward the right direction without narrowing it too much" \
        if attempt_number == 1 else \
        "a guided hint — be more directive, break the question into a smaller sub-question that leads toward the answer"

    prompt = f"""You are tutoring on "{topic_name}". The student struggled with this question:
    "{question}"

    Their response was: "{student_response}"

    Give {intensity}. Never state the answer directly. Keep it to 1-2 sentences.
    Use LaTeX ($...$ inline, $$...$$ display) for any mathematical notation.

    Return only the hint text:"""

    response = client.chat.completions.create(
        model=MODEL, messages=[{"role": "user", "content": prompt}],
        temperature=0.5, max_tokens=150
    )
    return response.choices[0].message.content.strip()


def generate_full_explanation(
    question: str, topic_name: str, context: str = "",
    web_sources: list[dict] = None, enabled_aids: list[str] = None
) -> str:
    """
    Attempt 3 — full explanation. Visual aid generation is now gated by
    explicit user preference (enabled_aids), not LLM discretion. This makes
    output deterministic: same topic + same preferences = same kind of aid
    every time, rather than varying by the model's mood.
    """
    enabled_aids = enabled_aids or []

    context_block = f"\n\nMaterial from the student's own uploaded document:\n{context}" if context else ""

    web_block = ""
    if web_sources:
        from app.services.web_grounding import format_sources_for_prompt
        formatted = format_sources_for_prompt(web_sources)
        web_block = f"\n\nTrusted web sources (cite by number, e.g. 'as [Source 1] explains...'):\n{formatted}"

    grounding_instruction = ""
    if context or web_sources:
        grounding_instruction = "\nGround your explanation in the material/sources provided below — cite them explicitly where you draw on them. Do not state facts that contradict the provided sources."

    aid_block = ""

    prompt = f"""The student has struggled with this question on "{topic_name}" across multiple attempts:
"{question}"

Give a clear, complete explanation now. Cover:
- The core idea, explained thoroughly
- One concrete example
- An intuitive analogy if one fits naturally
- How this connects to what they likely already know

Keep it focused — 4-6 sentences, not an essay.
Use LaTeX ($...$ inline, $$...$$ display) for any equations or mathematical notation.{grounding_instruction}{context_block}{web_block}{aid_block}

Return only the explanation."""

    response = client.chat.completions.create(
        model=MODEL, messages=[{"role": "user", "content": prompt}],
        temperature=0.5, max_tokens=600
    )
    return response.choices[0].message.content.strip()