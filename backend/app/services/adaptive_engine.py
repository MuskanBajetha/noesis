from sqlalchemy.orm import Session
from app.models.database import MasteryScore, LearningHistory, Answer, Question
from app.services.knowledge_tracing import knowledge_tracer
from app.services.rag_service import retrieve_context
from app.services.memory_service import build_personalized_context
from app.services.groq_service import generate_socratic_question


def get_adaptive_level(mastery_score: float) -> dict:
    """
    Determine question difficulty based on mastery.
    Implements Zone of Proximal Development.
    """
    if mastery_score >= 0.8:
        return {
            "level": "advanced",
            "label": "🔥 Advanced",
            "description": "Synthesis and critical analysis",
            "instruction": "Ask a challenging question requiring synthesis of multiple concepts, real-world application, or critical analysis."
        }
    elif mastery_score >= 0.4:
        return {
            "level": "intermediate",
            "label": "📈 Intermediate",
            "description": "Connecting concepts",
            "instruction": "Ask a question that connects core concepts and encourages deeper thinking about mechanisms and relationships."
        }
    else:
        return {
            "level": "beginner",
            "label": "🌱 Beginner",
            "description": "Building foundations",
            "instruction": "Ask a simple foundational question to build basic understanding. Use everyday examples."
        }


def generate_adaptive_question(
    student_id: int,
    topic: str,
    db: Session,
    session_id: int = None
) -> dict:
    """
    Generate a fully adaptive question using:
    1. DKT mastery estimate
    2. RAG context from documents
    3. Student memory/history
    4. Zone of proximal development
    """
    # Get DKT mastery estimate
    mastery_map = knowledge_tracer.get_student_mastery(student_id, db)
    topic_mastery = mastery_map.get(topic, 0.5)

    # Also check DB mastery score
    db_mastery = db.query(MasteryScore).filter(
        MasteryScore.student_id == student_id,
        MasteryScore.topic == topic
    ).first()

    if db_mastery:
        # Weighted average: 60% DB score, 40% DKT estimate
        final_mastery = 0.6 * db_mastery.score + 0.4 * topic_mastery
    else:
        final_mastery = topic_mastery

    # Get adaptive level
    adaptive = get_adaptive_level(final_mastery)

    # Get RAG context
    rag_context = retrieve_context(topic, topic, n_results=2)

    # Get personalized context
    personal_context = build_personalized_context(student_id, topic, db)

    # Build full context
    full_context = ""
    if rag_context:
        full_context += f"LEARNING MATERIAL:\n{rag_context}\n\n"
    if personal_context:
        full_context += f"STUDENT HISTORY:\n{personal_context}\n\n"
    full_context += f"DIFFICULTY INSTRUCTION:\n{adaptive['instruction']}"

    # Generate question
    question_text = generate_socratic_question(topic, adaptive["level"], full_context)

    # Get recommendations
    recommendations = knowledge_tracer.get_next_topic_recommendation(mastery_map)

    return {
        "question": question_text,
        "adaptive_level": adaptive["level"],
        "adaptive_label": adaptive["label"],
        "mastery_score": round(final_mastery, 3),
        "rag_used": bool(rag_context),
        "personalized": bool(personal_context),
        "next_topic_recommendation": recommendations.get("focus_topic"),
        "mastery_map": {k: round(v, 2) for k, v in mastery_map.items()}
    }


def get_session_analytics(session_id: int, db: Session) -> dict:
    """Get analytics for a completed session."""
    questions = db.query(Question).filter(
        Question.session_id == session_id
    ).all()

    if not questions:
        return {"error": "No questions found"}

    question_ids = [q.id for q in questions]
    answers = db.query(Answer).filter(
        Answer.question_id.in_(question_ids)
    ).all()

    if not answers:
        return {"questions_asked": len(questions), "answers": 0}

    understanding_counts = {}
    misconceptions = []
    for a in answers:
        level = a.understanding_level or "partial"
        understanding_counts[level] = understanding_counts.get(level, 0) + 1
        if a.misconception_detected:
            misconceptions.append(a.misconception_type)

    excellent = understanding_counts.get("excellent", 0)
    good = understanding_counts.get("good", 0)
    total = len(answers)
    score = (excellent * 1.0 + good * 0.7) / total if total > 0 else 0

    return {
        "questions_asked": len(questions),
        "answers_given": total,
        "understanding_distribution": understanding_counts,
        "misconceptions_found": len(misconceptions),
        "misconception_types": list(set(misconceptions)),
        "session_score": round(score, 2),
        "performance": "excellent" if score >= 0.8 else "good" if score >= 0.5 else "needs_work"
    }