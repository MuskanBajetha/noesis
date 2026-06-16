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
    """
    Evaluate student response using enhanced misconception detection.
    """
    from app.services.misconception_service import detect_misconceptions_detailed, generate_targeted_followup

    # Run misconception detection
    misconception_data = detect_misconceptions_detailed(student_response, topic, question)

    # Generate targeted follow-up if misconception found
    follow_up_question = None
    if misconception_data["misconception_detected"] and misconception_data.get("teaching_strategy"):
        follow_up_question = generate_targeted_followup(
            misconception_data.get("misconception_type", ""),
            topic,
            misconception_data.get("teaching_strategy", "")
        )

    # Generate feedback
    prompt = f"""You are a Socratic tutor giving feedback.

Topic: {topic}
Question: {question}
Student Response: {student_response}
Misconception Detected: {misconception_data["misconception_detected"]}
{"Misconception: " + str(misconception_data.get("misconception_type")) if misconception_data["misconception_detected"] else ""}

Write encouraging feedback (2-3 sentences) that:
- Acknowledges what they got right
- Gently hints at what needs more thought WITHOUT giving the answer
- Ends with encouragement

Return only the feedback text:"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=200
    )

    feedback = response.choices[0].message.content.strip()

    # Determine understanding level
    confidence = misconception_data.get("confidence", 0)
    severity = misconception_data.get("severity")

    if misconception_data["misconception_detected"] and severity == "major":
        understanding_level = "none"
    elif misconception_data["misconception_detected"] and severity == "moderate":
        understanding_level = "partial"
    elif misconception_data["misconception_detected"] and severity == "minor":
        understanding_level = "good"
    else:
        understanding_level = "excellent" if len(student_response.split()) > 15 else "good"

    return {
        "understanding_level": understanding_level,
        "misconception_detected": misconception_data["misconception_detected"],
        "misconception_type": misconception_data.get("misconception_type"),
        "misconception_description": misconception_data.get("misconception_description"),
        "severity": misconception_data.get("severity"),
        "related_misconceptions": misconception_data.get("related_misconceptions", []),
        "teaching_strategy": misconception_data.get("teaching_strategy"),
        "follow_up_question": follow_up_question,
        "feedback": feedback,
        "follow_up_needed": True
    }