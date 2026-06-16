import json
from groq import Groq
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

# ── Misconception Knowledge Base ─────────────────────────

MISCONCEPTION_PATTERNS = {
    "Newton's Laws": [
        "heavier objects fall faster",
        "objects need force to keep moving",
        "action and reaction forces cancel out",
        "more mass means more acceleration with same force",
        "gravity only acts when object is moving",
    ],
    "Gravity": [
        "gravity only exists on Earth",
        "there is no gravity in space",
        "gravity depends on the size not mass",
        "gravity pulls things down not toward center",
        "heavier objects fall faster than lighter ones",
    ],
    "Photosynthesis": [
        "plants get food from soil",
        "plants only perform photosynthesis during day",
        "oxygen is absorbed by plants",
        "plants do not respire",
        "chlorophyll produces glucose directly",
    ],
    "Cell Division": [
        "cells divide to repair all damage",
        "mitosis produces gametes",
        "meiosis creates identical cells",
        "DNA doubles during cell division not before",
        "all cells divide at the same rate",
    ],
    "Thermodynamics": [
        "heat and temperature are the same",
        "cold is a form of energy",
        "heat flows from cold to hot naturally",
        "insulation generates heat",
        "entropy always decreases in isolated systems",
    ],
    "Evolution": [
        "evolution is just a theory meaning guess",
        "humans evolved from monkeys",
        "evolution has a direction or goal",
        "individual organisms evolve during lifetime",
        "evolution always leads to more complexity",
    ],
    "Algebra": [
        "dividing by zero gives zero",
        "negative times negative is negative",
        "variables always represent unknown numbers",
        "equals sign means calculate the answer",
        "brackets just change order not priority",
    ],
    "Quantum Physics": [
        "quantum effects only apply to subatomic particles",
        "observation does not affect quantum systems",
        "schrodingers cat is actually about a cat",
        "quantum entanglement allows faster than light communication",
        "electrons orbit nucleus like planets orbit sun",
    ],
}


def detect_misconceptions_detailed(
    student_response: str,
    topic: str,
    question: str
) -> dict:
    """
    Detect misconceptions using LLM-based analysis.
    Returns detailed misconception info with confidence scores.
    """

    known_misconceptions = MISCONCEPTION_PATTERNS.get(topic, [])
    misconceptions_str = "\n".join([f"- {m}" for m in known_misconceptions]) if known_misconceptions else "No specific patterns defined."

    prompt = f"""You are an expert educational AI specializing in detecting student misconceptions.

Topic: {topic}
Question Asked: {question}
Student Response: {student_response}

Known common misconceptions for this topic:
{misconceptions_str}

Analyze the student's response carefully and return a JSON object with exactly these fields:
{{
    "misconception_detected": true/false,
    "confidence": 0.0 to 1.0,
    "misconception_type": "short name of misconception or null",
    "misconception_description": "detailed description of what the student misunderstands or null",
    "correct_concept": "brief correct explanation of the concept without giving full answer",
    "severity": "minor/moderate/major or null",
    "related_misconceptions": ["list", "of", "related", "misconceptions"] or [],
    "teaching_strategy": "how to address this misconception through Socratic questioning"
}}

Be precise. Only flag as misconception if clearly wrong reasoning, not just incomplete answers.
Return only the JSON, no extra text:"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=500
    )

    try:
        result = json.loads(response.choices[0].message.content.strip())
    except Exception:
        result = {
            "misconception_detected": False,
            "confidence": 0.0,
            "misconception_type": None,
            "misconception_description": None,
            "correct_concept": None,
            "severity": None,
            "related_misconceptions": [],
            "teaching_strategy": "Continue with Socratic questioning"
        }

    return result


def generate_targeted_followup(
    misconception_type: str,
    topic: str,
    teaching_strategy: str
) -> str:
    """Generate a targeted Socratic question to address a specific misconception."""

    prompt = f"""You are a Socratic tutor addressing a student misconception.

Topic: {topic}
Misconception: {misconception_type}
Teaching Strategy: {teaching_strategy}

Generate ONE targeted Socratic question that:
1. Does NOT directly correct the student
2. Guides them to discover the flaw in their thinking
3. Uses a real-world example or thought experiment
4. Is encouraging and curious in tone

Return only the question, nothing else:"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=150
    )

    return response.choices[0].message.content.strip()


def get_misconception_analytics(misconceptions: list) -> dict:
    """Analyze a list of misconceptions to find patterns."""
    if not misconceptions:
        return {"total": 0, "by_type": {}, "most_common": None}

    type_counts = {}
    for m in misconceptions:
        t = m.get("misconception_type", "unknown")
        if t:
            type_counts[t] = type_counts.get(t, 0) + 1

    most_common = max(type_counts, key=type_counts.get) if type_counts else None

    return {
        "total": len(misconceptions),
        "by_type": type_counts,
        "most_common": most_common
    }