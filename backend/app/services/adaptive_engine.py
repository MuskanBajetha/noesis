from sqlalchemy.orm import Session
from app.models.database import MasteryScore, LearningHistory, Answer, Question, Topic, Subject, TopicRelationship, Session as SessionModel
from app.services.rag_service import retrieve_context
from app.services.memory_service import build_personalized_context
from app.services.groq_service import generate_socratic_question
import random

def get_adaptive_level(mastery_score: float) -> dict:
    if mastery_score >= 0.8:
        return {"level": "advanced", "label": "🔥 Advanced", "instruction": "Ask a challenging question requiring synthesis of multiple concepts, real-world application, or critical analysis."}
    elif mastery_score >= 0.4:
        return {"level": "intermediate", "label": "📈 Intermediate", "instruction": "Ask a question that connects core concepts and encourages deeper thinking about mechanisms and relationships."}
    else:
        return {"level": "beginner", "label": "🌱 Beginner", "instruction": "Ask a simple foundational question to build basic understanding. Use everyday examples."}


def generate_adaptive_question(student_id: int, topic: Topic, subject_id: int, db: Session) -> dict:
    from app.services.pedagogy_engine import generate_staged_question
    from app.models.database import Question as QuestionModel

    db_mastery = db.query(MasteryScore).filter(
        MasteryScore.student_id == student_id, MasteryScore.topic_id == topic.id
    ).first()

    stage = db_mastery.pedagogical_stage if db_mastery else "recognition"
    mastery_score = db_mastery.score if db_mastery else 0.0

    rag_context = retrieve_context(topic.name, subject_id, n_results=2)
    personal_context = build_personalized_context(student_id, topic.id, subject_id, db)

    full_context = ""
    if rag_context:
        full_context += f"LEARNING MATERIAL:\n{rag_context}\n\n"
    if personal_context:
        full_context += f"STUDENT HISTORY:\n{personal_context}"

    # Avoid repeating recent questions on this topic
    recent_questions = [
        q.question_text for q in db.query(QuestionModel).filter(QuestionModel.topic_id == topic.id)
        .order_by(QuestionModel.created_at.desc()).limit(5).all()
    ]

    question_text = generate_staged_question(topic.name, stage, full_context, recent_questions)

    return {
        "question": question_text,
        "stage": stage,
        "mastery_score": round(mastery_score, 3),
        "rag_used": bool(rag_context),
        "personalized": bool(personal_context),
        "topic_name": topic.name,
    }

def get_concept_graph(subject_id: int, student_id: int, db: Session) -> dict:
    """
    Node graph for ONE subject only. Edges come from TopicRelationship
    (auto-suggested at upload time), not a hardcoded global dict.
    """
    topics = db.query(Topic).filter(Topic.subject_id == subject_id, Topic.is_archived == False).all()
    if not topics:
        return {"nodes": [], "edges": []}

    topic_ids = [t.id for t in topics]
    mastery_map = {
        m.topic_id: m.score
        for m in db.query(MasteryScore).filter(
            MasteryScore.student_id == student_id,
            MasteryScore.topic_id.in_(topic_ids)
        ).all()
    }

    session_counts = {}
    sessions = db.query(SessionModel).filter(
        SessionModel.student_id == student_id,
        SessionModel.subject_id == subject_id
    ).all()
    for s in sessions:
        session_counts[s.topic_id] = session_counts.get(s.topic_id, 0) + 1

    nodes = []
    for t in topics:
        studied = t.id in mastery_map
        mastery = mastery_map.get(t.id, 0.0) if studied else 0.0
        nodes.append({
            "id": str(t.id),
            "name": t.name,
            "mastery": round(mastery, 2),
            "sessions": session_counts.get(t.id, 0),
            "studied": studied,
            "status": (
                "unexplored" if not studied else
                "mastered" if mastery >= 0.8 else
                "learning" if mastery >= 0.4 else
                "struggling"
            )
        })

    edges_raw = db.query(TopicRelationship).filter(TopicRelationship.subject_id == subject_id).all()
    edges = [{"source": str(e.topic_a_id), "target": str(e.topic_b_id)} for e in edges_raw]

    return {"nodes": nodes, "edges": edges}


def get_learning_journey(student_id: int, db: Session, subject_id: int = None) -> dict:
    """Chronological timeline, optionally scoped to one subject."""
    sessions_q = db.query(SessionModel).filter(SessionModel.student_id == student_id)
    history_q = db.query(LearningHistory).filter(LearningHistory.student_id == student_id)

    if subject_id:
        sessions_q = sessions_q.filter(SessionModel.subject_id == subject_id)
        history_q = history_q.filter(LearningHistory.subject_id == subject_id)

    sessions = sessions_q.order_by(SessionModel.started_at).all()
    history = history_q.order_by(LearningHistory.created_at).all()

    topic_ids = {s.topic_id for s in sessions} | {h.topic_id for h in history if h.topic_id}
    topics = {t.id: t.name for t in db.query(Topic).filter(Topic.id.in_(topic_ids)).all()} if topic_ids else {}

    timeline = []
    seen_session_keys = set()
    for s in sessions:
        key = (s.topic_id, s.started_at.replace(microsecond=0))
        if key in seen_session_keys:
            continue
        seen_session_keys.add(key)
        topic_name = topics.get(s.topic_id, "Unknown")
        timeline.append({"type": "session_start", "topic": topic_name, "timestamp": s.started_at.isoformat(), "label": f"Started studying {topic_name}"})

    for h in history:
        topic_name = topics.get(h.topic_id, "Unknown")
        label = h.description.replace("misconception_type:", "Misconception: ") if h.event_type == "misconception" else h.description
        timeline.append({"type": h.event_type, "topic": topic_name, "timestamp": h.created_at.isoformat(), "label": label})

    timeline.sort(key=lambda x: x["timestamp"])
    return {"timeline": timeline, "total_events": len(timeline)}

def get_global_knowledge_graph(student_id: int, db: Session) -> dict:
    """
    Aggregate view across ALL subjects for one student.
    Each subject becomes a cluster; its topics are sub-nodes linked to it.
    Within-subject topic relationships are preserved. No cross-subject
    links are inferred automatically (kept structurally separate),
    but the data shape leaves room for that later.
    """
    subjects = db.query(Subject).filter(Subject.student_id == student_id).all()
    if not subjects:
        return {"nodes": [], "edges": []}

    all_topic_ids = []
    nodes = []
    edges = []

    for s in subjects:
        # Subject node itself — the cluster anchor
        subject_topics = db.query(Topic).filter(Topic.subject_id == s.id, Topic.is_archived == False).all()
        topic_ids = [t.id for t in subject_topics]
        all_topic_ids.extend(topic_ids)

        mastery_map = {
            m.topic_id: m.score
            for m in db.query(MasteryScore).filter(
                MasteryScore.student_id == student_id,
                MasteryScore.topic_id.in_(topic_ids)
            ).all()
        } if topic_ids else {}

        avg_mastery = round(sum(mastery_map.values()) / len(mastery_map), 2) if mastery_map else 0.0

        nodes.append({
            "id": f"subject-{s.id}",
            "name": s.name,
            "kind": "subject",
            "mastery": avg_mastery,
            "topic_count": len(subject_topics),
        })

        for t in subject_topics:
            studied = t.id in mastery_map
            mastery = mastery_map.get(t.id, 0.0) if studied else 0.0
            nodes.append({
                "id": f"topic-{t.id}",
                "name": t.name,
                "kind": "topic",
                "subject_id": s.id,
                "mastery": round(mastery, 2),
                "studied": studied,
                "status": (
                    "unexplored" if not studied else
                    "mastered" if mastery >= 0.8 else
                    "learning" if mastery >= 0.4 else
                    "struggling"
                ),
            })
            # Every topic links back to its subject anchor
            edges.append({"source": f"subject-{s.id}", "target": f"topic-{t.id}", "kind": "anchor"})

        # Within-subject topic-to-topic relationships, carried over as-is
        rels = db.query(TopicRelationship).filter(TopicRelationship.subject_id == s.id).all()
        for r in rels:
            edges.append({"source": f"topic-{r.topic_a_id}", "target": f"topic-{r.topic_b_id}", "kind": "related"})

    # Cross-subject bridges — separate edge "kind" so the frontend can render distinctly
    from app.models.database import CrossSubjectBridge
    bridges = db.query(CrossSubjectBridge).filter(CrossSubjectBridge.student_id == student_id).all()
    for b in bridges:
        if b.topic_a_id in all_topic_ids and b.topic_b_id in all_topic_ids:
            edges.append({
                "source": f"topic-{b.topic_a_id}",
                "target": f"topic-{b.topic_b_id}",
                "kind": "bridge",
                "description": b.relationship_description,
                "strength": b.strength,
            })

    return {"nodes": nodes, "edges": edges}


def select_challenge_topic(subject_id: int, student_id: int, db: Session) -> Topic:
    """
    Picks the next topic for a 'Challenge me' session, following priority:
    1. Weak concepts (mastery < 0.4, studied at least once)
    2. Previously failed concepts (has a misconception/struggle history entry)
    3. Topics needing revision (mastery 0.4-0.7, studied a while ago)
    4. Random mastered concepts (mastery >= 0.8) — for retention checks
    """
    topics = db.query(Topic).filter(Topic.subject_id == subject_id, Topic.is_archived == False).all()
    if not topics:
        return None
    topic_ids = [t.id for t in topics]

    scores = {
        m.topic_id: m for m in db.query(MasteryScore).filter(
            MasteryScore.student_id == student_id, MasteryScore.topic_id.in_(topic_ids)
        ).all()
    }

    weak = [t for t in topics if t.id in scores and scores[t.id].score < 0.4]
    if weak:
        return random.choice(weak)

    failed_topic_ids = {
        h.topic_id for h in db.query(LearningHistory).filter(
            LearningHistory.student_id == student_id,
            LearningHistory.topic_id.in_(topic_ids),
            LearningHistory.event_type.in_(["misconception", "struggle"])
        ).all()
    }
    failed = [t for t in topics if t.id in failed_topic_ids]
    if failed:
        return random.choice(failed)

    needs_revision = [t for t in topics if t.id in scores and 0.4 <= scores[t.id].score < 0.7]
    if needs_revision:
        return random.choice(needs_revision)

    mastered = [t for t in topics if t.id in scores and scores[t.id].score >= 0.8]
    if mastered:
        return random.choice(mastered)

    # Fallback: nothing studied yet at all — just pick anything to start somewhere
    return random.choice(topics)