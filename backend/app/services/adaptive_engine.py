from sqlalchemy.orm import Session
from app.models.database import MasteryScore, LearningHistory, Answer, Question, Session as SessionModel
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

# ── Concept Relationship Map ─────────────────────────────

CONCEPT_RELATIONSHIPS = {
    "Newton's Laws": ["Gravity", "Thermodynamics"],
    "Gravity": ["Newton's Laws", "Quantum Physics"],
    "Photosynthesis": ["Cell Division", "Evolution"],
    "Cell Division": ["Photosynthesis", "Evolution"],
    "Algebra": ["Quantum Physics", "Newton's Laws"],
    "Thermodynamics": ["Newton's Laws", "Quantum Physics"],
    "Evolution": ["Photosynthesis", "Cell Division"],
    "Quantum Physics": ["Gravity", "Algebra", "Thermodynamics"],
    "Radar": ["Newton's Laws", "Quantum Physics"],
}


def get_concept_graph(student_id: int, db: Session) -> dict:
    """
    Build a node graph of concept relationships,
    annotated with the student's mastery for each node.
    """
    mastery_map = knowledge_tracer.get_student_mastery(student_id, db)

    db_mastery = {
        m.topic: m.score
        for m in db.query(MasteryScore).filter(MasteryScore.student_id == student_id).all()
    }

    # Get session counts per topic for node sizing
    from app.models.database import Session as SessionModel
    session_counts = {}
    sessions = db.query(SessionModel).filter(SessionModel.student_id == student_id).all()
    for s in sessions:
        session_counts[s.topic] = session_counts.get(s.topic, 0) + 1

    nodes = []
    for topic in CONCEPT_RELATIONSHIPS.keys():
        mastery = db_mastery.get(topic, mastery_map.get(topic, 0.5))
        nodes.append({
            "id": topic,
            "mastery": round(mastery, 2),
            "sessions": session_counts.get(topic, 0),
            "studied": topic in db_mastery,
            "status": (
                "mastered" if mastery >= 0.8 else
                "learning" if mastery >= 0.4 else
                "struggling" if topic in db_mastery else "unexplored"
            )
        })

    edges = []
    seen_pairs = set()
    for topic, related in CONCEPT_RELATIONSHIPS.items():
        for r in related:
            pair = tuple(sorted([topic, r]))
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                edges.append({"source": topic, "target": r})

    return {"nodes": nodes, "edges": edges}


def get_learning_journey(student_id: int, db: Session) -> dict:
    """
    Build a chronological timeline of the student's learning events
    across all topics and sessions.
    """
    from app.models.database import Session as SessionModel

    sessions = db.query(SessionModel).filter(
        SessionModel.student_id == student_id
    ).order_by(SessionModel.started_at).all()

    history = db.query(LearningHistory).filter(
        LearningHistory.student_id == student_id
    ).order_by(LearningHistory.created_at).all()

    timeline = []

    seen_session_keys = set()
    for s in sessions:
        key = (s.topic, s.started_at.replace(microsecond=0))
        if key in seen_session_keys:
            continue
        seen_session_keys.add(key)
        timeline.append({
            "type": "session_start",
            "topic": s.topic,
            "timestamp": s.started_at.isoformat(),
            "label": f"Started studying {s.topic}"
        })

    for h in history:
        timeline.append({
            "type": h.event_type,
            "topic": h.topic,
            "timestamp": h.created_at.isoformat(),
            "label": h.description
        })

    timeline.sort(key=lambda x: x["timestamp"])

    # Compute cumulative mastery trend per topic over time
    topics_seen = {}
    trend_points = []
    for event in timeline:
        topic = event["topic"]
        if event["type"] == "breakthrough":
            topics_seen[topic] = min(1.0, topics_seen.get(topic, 0.5) + 0.15)
        elif event["type"] == "misconception":
            topics_seen[topic] = max(0.0, topics_seen.get(topic, 0.5) - 0.05)
        elif event["type"] == "struggle":
            topics_seen[topic] = max(0.0, topics_seen.get(topic, 0.5) - 0.05)
        else:
            topics_seen.setdefault(topic, 0.5)

        trend_points.append({
            "timestamp": event["timestamp"],
            "topic": topic,
            "event": event["type"],
            "estimated_mastery": round(topics_seen[topic], 2)
        })

    return {
        "timeline": timeline,
        "trend_points": trend_points,
        "total_events": len(timeline)
    }