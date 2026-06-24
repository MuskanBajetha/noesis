from sqlalchemy.orm import Session
from app.models.database import (
    Student, MasteryScore, LearningHistory, Topic, Subject,
    Answer, Question, Session as SessionModel
)
from datetime import datetime


def get_topic_memory(student_id: int, topic_id: int, db: Session) -> dict:
    """Get detailed memory for a specific topic (scoped by topic_id, not a string)."""
    mastery = db.query(MasteryScore).filter(
        MasteryScore.student_id == student_id,
        MasteryScore.topic_id == topic_id
    ).first()

    misconceptions = db.query(LearningHistory).filter(
        LearningHistory.student_id == student_id,
        LearningHistory.topic_id == topic_id,
        LearningHistory.event_type == "misconception"
    ).order_by(LearningHistory.created_at.desc()).limit(5).all()

    breakthroughs = db.query(LearningHistory).filter(
        LearningHistory.student_id == student_id,
        LearningHistory.topic_id == topic_id,
        LearningHistory.event_type == "breakthrough"
    ).all()

    return {
        "mastery_score": mastery.score if mastery else 0.5,
        "questions_attempted": mastery.questions_attempted if mastery else 0,
        "misconceptions": [m.description for m in misconceptions],
        "breakthroughs": len(breakthroughs),
        "misconceptions_count": mastery.misconceptions_count if mastery else 0,
    }


def get_subject_profile(student_id: int, subject_id: int, db: Session) -> dict:
    """Weak/strong topics WITHIN one subject — prevents cross-subject bleed in context."""
    topics = db.query(Topic).filter(Topic.subject_id == subject_id).all()
    topic_ids = [t.id for t in topics]
    id_to_name = {t.id: t.name for t in topics}

    mastery_scores = db.query(MasteryScore).filter(
        MasteryScore.student_id == student_id,
        MasteryScore.topic_id.in_(topic_ids)
    ).all() if topic_ids else []

    weak = [{"topic": id_to_name[m.topic_id], "score": m.score} for m in mastery_scores if m.score < 0.4]
    strong = [{"topic": id_to_name[m.topic_id], "score": m.score} for m in mastery_scores if m.score >= 0.8]

    return {"weak_topics": weak, "strong_topics": strong}


def record_learning_event(student_id: int, subject_id: int, topic_id: int, event_type: str, description: str, db: Session):
    event = LearningHistory(
        student_id=student_id, subject_id=subject_id, topic_id=topic_id,
        event_type=event_type, description=description
    )
    db.add(event)
    db.commit()


def update_mastery_detailed(
    student_id: int,
    topic_id: int,
    understanding: str,
    misconception_detected: bool,
    db: Session,
    misconception_type: str = None
):
    delta = {"none": -0.05, "partial": 0.05, "good": 0.10, "excellent": 0.15}.get(understanding, 0)

    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    subject_id = topic.subject_id if topic else None

    mastery = db.query(MasteryScore).filter(
        MasteryScore.student_id == student_id,
        MasteryScore.topic_id == topic_id
    ).first()

    if mastery:
        mastery.score = max(0.0, min(1.0, mastery.score + delta))
        mastery.questions_attempted += 1
        if misconception_detected:
            mastery.misconceptions_count += 1
        mastery.updated_at = datetime.utcnow()
    else:
        mastery = MasteryScore(
            student_id=student_id, topic_id=topic_id,
            score=max(0.0, 0.5 + delta), questions_attempted=1,
            misconceptions_count=1 if misconception_detected else 0
        )
        db.add(mastery)

    if understanding == "excellent":
        record_learning_event(student_id, subject_id, topic_id, "breakthrough", "Excellent understanding demonstrated", db)
    elif misconception_detected:
        record_learning_event(student_id, subject_id, topic_id, "misconception", f"misconception_type:{misconception_type or 'unknown'}", db)
    elif understanding == "none":
        record_learning_event(student_id, subject_id, topic_id, "struggle", "Student struggling with this topic", db)

    student = db.query(Student).filter(Student.id == student_id).first()
    if student:
        student.last_active = datetime.utcnow()

    db.commit()


def build_personalized_context(student_id: int, topic_id: int, subject_id: int, db: Session) -> str:
    """Build personalized context string, scoped to ONE subject only."""
    memory = get_topic_memory(student_id, topic_id, db)
    profile = get_subject_profile(student_id, subject_id, db)

    parts = []
    if memory["misconceptions"]:
        cleaned = [m.replace("misconception_type:", "") for m in memory["misconceptions"][:3]]
        parts.append(f"Previous misconceptions on this topic: {', '.join(cleaned)}")

    if memory["mastery_score"] < 0.4:
        parts.append(f"Student is struggling (mastery: {memory['mastery_score']:.0%}). Use simpler questions.")
    elif memory["mastery_score"] >= 0.8:
        parts.append(f"Student has strong grasp (mastery: {memory['mastery_score']:.0%}). Challenge them more.")

    if memory["questions_attempted"] == 0:
        parts.append("This is the student's first time on this topic. Start with fundamentals.")

    if profile.get("weak_topics"):
        weak = [t["topic"] for t in profile["weak_topics"]][:2]
        if weak:
            parts.append(f"Within this subject, student also struggles with: {', '.join(weak)}")

    return " | ".join(parts) if parts else ""