from sqlalchemy.orm import Session
from app.models.database import (
    Student, MasteryScore, LearningHistory,
    Answer, Question, Session as SessionModel
)
from datetime import datetime
from typing import Optional


def get_student_profile(student_id: int, db: Session) -> dict:
    """Get complete student profile with learning history."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return {}

    mastery_scores = db.query(MasteryScore).filter(
        MasteryScore.student_id == student_id
    ).all()

    history = db.query(LearningHistory).filter(
        LearningHistory.student_id == student_id
    ).order_by(LearningHistory.created_at.desc()).limit(20).all()

    weak_topics = [m for m in mastery_scores if m.score < 0.4]
    strong_topics = [m for m in mastery_scores if m.score >= 0.8]
    misconceptions = [h for h in history if h.event_type == "misconception"]

    return {
        "name": student.name,
        "weak_topics": [{"topic": m.topic, "score": m.score} for m in weak_topics],
        "strong_topics": [{"topic": m.topic, "score": m.score} for m in strong_topics],
        "recent_misconceptions": [
            {"topic": h.topic, "description": h.description}
            for h in misconceptions[:5]
        ],
        "total_sessions": db.query(SessionModel).filter(
            SessionModel.student_id == student_id
        ).count(),
        "streak_days": student.streak_days,
    }


def get_topic_memory(student_id: int, topic: str, db: Session) -> dict:
    """Get detailed memory for a specific topic."""
    mastery = db.query(MasteryScore).filter(
        MasteryScore.student_id == student_id,
        MasteryScore.topic == topic
    ).first()

    misconceptions = db.query(LearningHistory).filter(
        LearningHistory.student_id == student_id,
        LearningHistory.topic == topic,
        LearningHistory.event_type == "misconception"
    ).order_by(LearningHistory.created_at.desc()).limit(5).all()

    breakthroughs = db.query(LearningHistory).filter(
        LearningHistory.student_id == student_id,
        LearningHistory.topic == topic,
        LearningHistory.event_type == "breakthrough"
    ).all()

    return {
        "topic": topic,
        "mastery_score": mastery.score if mastery else 0.0,
        "questions_attempted": mastery.questions_attempted if mastery else 0,
        "misconceptions": [m.description for m in misconceptions],
        "breakthroughs": len(breakthroughs),
        "misconceptions_count": mastery.misconceptions_count if mastery else 0,
    }


def record_learning_event(
    student_id: int,
    topic: str,
    event_type: str,
    description: str,
    db: Session
):
    """Record a learning event (misconception, breakthrough, struggle)."""
    event = LearningHistory(
        student_id=student_id,
        topic=topic,
        event_type=event_type,
        description=description
    )
    db.add(event)
    db.commit()


def update_mastery_detailed(
    student_id: int,
    topic: str,
    understanding: str,
    misconception_detected: bool,
    db: Session
):
    """Update mastery score with detailed tracking."""
    delta = {
        "none": -0.05,
        "partial": 0.05,
        "good": 0.10,
        "excellent": 0.15
    }.get(understanding, 0)

    mastery = db.query(MasteryScore).filter(
        MasteryScore.student_id == student_id,
        MasteryScore.topic == topic
    ).first()

    if mastery:
        mastery.score = max(0.0, min(1.0, mastery.score + delta))
        mastery.questions_attempted += 1
        if misconception_detected:
            mastery.misconceptions_count += 1
        mastery.updated_at = datetime.utcnow()
    else:
        mastery = MasteryScore(
            student_id=student_id,
            topic=topic,
            score=max(0.0, 0.5 + delta),
            questions_attempted=1,
            misconceptions_count=1 if misconception_detected else 0
        )
        db.add(mastery)

    # Record events
    if understanding == "excellent":
        record_learning_event(student_id, topic, "breakthrough",
                              f"Excellent understanding demonstrated", db)
    elif misconception_detected:
        record_learning_event(student_id, topic, "misconception",
                              f"Misconception detected during {topic} session", db)
    elif understanding == "none":
        record_learning_event(student_id, topic, "struggle",
                              f"Student struggling with {topic}", db)

    # Update student last active
    student = db.query(Student).filter(Student.id == student_id).first()
    if student:
        student.last_active = datetime.utcnow()

    db.commit()


def build_personalized_context(student_id: int, topic: str, db: Session) -> str:
    """Build a personalized context string for the AI based on student history."""
    memory = get_topic_memory(student_id, topic, db)
    profile = get_student_profile(student_id, db)

    context_parts = []

    if memory["misconceptions"]:
        context_parts.append(
            f"Previous misconceptions in {topic}: {', '.join(memory['misconceptions'][:3])}"
        )

    if memory["mastery_score"] < 0.4:
        context_parts.append(f"Student is struggling with {topic} (mastery: {memory['mastery_score']:.0%}). Use simpler questions.")
    elif memory["mastery_score"] >= 0.8:
        context_parts.append(f"Student has strong grasp of {topic} (mastery: {memory['mastery_score']:.0%}). Challenge them more.")

    if memory["questions_attempted"] == 0:
        context_parts.append("This is the student's first time on this topic. Start with fundamentals.")

    if profile.get("weak_topics"):
        weak = [t["topic"] for t in profile["weak_topics"] if t["topic"] != topic][:2]
        if weak:
            context_parts.append(f"Student also struggles with: {', '.join(weak)}")

    return " | ".join(context_parts) if context_parts else ""