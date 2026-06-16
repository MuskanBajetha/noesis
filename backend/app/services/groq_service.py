import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "llama-3.3-70b-versatile"


def generate_socratic_question(topic: str, student_level: str, context: str = "") -> str:
    level_instruction = {
        "beginner": "Ask a simple foundational question to build basic understanding.",
        "intermediate": "Ask a question that connects concepts and encourages deeper thinking.",
        "advanced": "Ask a challenging question that requires synthesis and critical analysis."
    }.get(student_level, "Ask a standard Socratic question.")

    context_block = f"\n\nUse this context from learning material to ground your question:\n{context}" if context else ""

    prompt = f"""You are a Socratic tutor. Your job is to guide students to discover answers themselves.

RULES:
- NEVER give the answer directly
- Ask ONE clear question that guides the student toward understanding
- Be encouraging and curious
- Keep the question concise (1-2 sentences max)
- If context is provided, base your question on that material

Topic: {topic}
Student Level: {student_level}
Instruction: {level_instruction}{context_block}

Generate only the Socratic question, nothing else:"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=150
    )

    return response.choices[0].message.content.strip()


def evaluate_student_response(question: str, student_response: str, topic: str) -> dict:
    prompt = f"""You are an educational AI evaluating a student's response.

Topic: {topic}
Question Asked: {question}
Student Response: {student_response}

Analyze the response and return a JSON object with exactly these fields:
{{
  "understanding_level": "none/partial/good/excellent",
  "misconception_detected": true/false,
  "misconception_type": "describe the misconception or null",
  "feedback": "encouraging feedback that guides without giving the answer",
  "follow_up_needed": true/false
}}

Return only the JSON, no extra text:"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=300
    )

    try:
        result = json.loads(response.choices[0].message.content.strip())
    except Exception:
        result = {
            "understanding_level": "partial",
            "misconception_detected": False,
            "misconception_type": None,
            "feedback": "Good thinking! Let's explore this further.",
            "follow_up_needed": True
        }

    return result