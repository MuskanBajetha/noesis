import json
from groq import Groq
from dotenv import load_dotenv
import os
from sqlalchemy.orm import Session
from app.models.database import Answer, Question, MasteryScore, LearningHistory, Student, Topic, Subject

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"


def evaluate_rag_quality(question: str, context: str, answer: str) -> dict:
    """
    Evaluate RAG quality using RAGAS-inspired metrics.
    Measures: faithfulness, relevance, context precision.
    """
    prompt = f"""You are evaluating the quality of a RAG (Retrieval Augmented Generation) system.

Context Retrieved: {context[:500] if context else "No context"}
Question Generated: {question}
Student Answer: {answer}

Rate the following metrics from 0.0 to 1.0 and return as JSON:
{{
    "context_relevance": 0.0-1.0,
    "question_faithfulness": 0.0-1.0,
    "answer_relevance": 0.0-1.0,
    "overall_quality": 0.0-1.0,
    "issues": ["list any quality issues"] or []
}}

Return only JSON:"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=200
    )

    try:
        return json.loads(response.choices[0].message.content.strip())
    except Exception:
        return {
            "context_relevance": 0.7,
            "question_faithfulness": 0.7,
            "answer_relevance": 0.7,
            "overall_quality": 0.7,
            "issues": []
        }


def calculate_learning_gain(student_id: int, topic_id: int, db: Session) -> dict:
    """Compares early vs recent performance on ONE topic (by id, not name)."""
    answers = (
        db.query(Answer)
        .join(Question, Answer.question_id == Question.id)
        .filter(Question.topic_id == topic_id)
        .order_by(Answer.created_at)
        .all()
    )

    if len(answers) < 2:
        return {"learning_gain": 0, "trend": "insufficient_data"}

    score_map = {"none": 0, "partial": 0.33, "good": 0.66, "excellent": 1.0}

    early = answers[:len(answers)//2]
    recent = answers[len(answers)//2:]

    early_score = sum(score_map.get(a.understanding_level or "partial", 0.33) for a in early) / len(early)
    recent_score = sum(score_map.get(a.understanding_level or "partial", 0.33) for a in recent) / len(recent)
    gain = recent_score - early_score

    return {
        "early_score": round(early_score, 2),
        "recent_score": round(recent_score, 2),
        "learning_gain": round(gain, 2),
        "trend": "improving" if gain > 0.1 else "stable" if gain > -0.1 else "declining",
        "total_interactions": len(answers)
    }


def generate_full_evaluation_report(student_id: int, db: Session, subject_id: int = None) -> dict:
    """Full report, optionally scoped to one subject so subjects never blend in the numbers."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return {"error": "Student not found"}

    topics_q = db.query(Topic)
    if subject_id:
        topics_q = topics_q.filter(Topic.subject_id == subject_id)
        relevant_topic_ids = [t.id for t in topics_q.all()]
        mastery_scores = db.query(MasteryScore).filter(
            MasteryScore.student_id == student_id,
            MasteryScore.topic_id.in_(relevant_topic_ids)
        ).all() if relevant_topic_ids else []
        history = db.query(LearningHistory).filter(
            LearningHistory.student_id == student_id,
            LearningHistory.subject_id == subject_id
        ).all()
    else:
        mastery_scores = db.query(MasteryScore).filter(MasteryScore.student_id == student_id).all()
        history = db.query(LearningHistory).filter(LearningHistory.student_id == student_id).all()

    topic_id_to_name = {t.id: t.name for t in db.query(Topic).all()}

    learning_gains = {}
    for m in mastery_scores:
        gain = calculate_learning_gain(student_id, m.topic_id, db)
        learning_gains[topic_id_to_name.get(m.topic_id, "Unknown")] = gain

    misconceptions = [h for h in history if h.event_type == "misconception"]
    breakthroughs = [h for h in history if h.event_type == "breakthrough"]

    topic_ids_for_count = [m.topic_id for m in mastery_scores]
    total_questions = db.query(Answer).join(Question, Answer.question_id == Question.id).filter(
        Question.topic_id.in_(topic_ids_for_count)
    ).count() if topic_ids_for_count else 0

    avg_mastery = sum(m.score for m in mastery_scores) / len(mastery_scores) if mastery_scores else 0

    education_metrics = {
        "avg_mastery": round(avg_mastery, 2),
        "topics_studied": len(mastery_scores),
        "total_questions_answered": total_questions,
        "total_misconceptions": len(misconceptions),
        "total_breakthroughs": len(breakthroughs),
        "misconception_to_breakthrough_ratio": round(len(misconceptions) / max(len(breakthroughs), 1), 2),
    }

    topic_performance = []
    for m in mastery_scores:
        topic_name = topic_id_to_name.get(m.topic_id, "Unknown")
        gain_data = learning_gains.get(topic_name, {})
        topic_performance.append({
            "topic": topic_name,
            "mastery": round(m.score, 2),
            "questions_attempted": m.questions_attempted,
            "misconceptions": m.misconceptions_count,
            "learning_gain": gain_data.get("learning_gain", 0),
            "trend": gain_data.get("trend", "insufficient_data")
        })
    topic_performance.sort(key=lambda x: x["mastery"], reverse=True)

    return {
        "student_name": student.name,
        "student_id": student_id,
        "subject_id": subject_id,
        "generated_at": __import__("datetime").datetime.utcnow().isoformat(),
        "education_metrics": education_metrics,
        "topic_performance": topic_performance,
        "strengths": [t for t in topic_performance if t["mastery"] >= 0.7],
        "areas_for_improvement": [t for t in topic_performance if t["mastery"] < 0.4],
    }