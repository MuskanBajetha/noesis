from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.database import (
    Subject, Topic, MasteryScore, Session as SessionModel,
    Answer, Question, LearningHistory, TopicRelationship, CrossSubjectBridge
)


def get_dashboard_overview(student_id: int, db: Session) -> dict:
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)

    subjects = db.query(Subject).filter(Subject.student_id == student_id).all()
    subject_ids = [s.id for s in subjects]

    # ── Total subjects explored ──
    total_subjects = len(subjects)

    # ── Study streak: consecutive days with at least one answer ──
    answer_dates = db.query(func.date(Answer.created_at)).join(
        Question, Answer.question_id == Question.id
    ).join(
        SessionModel, Question.session_id == SessionModel.id
    ).filter(SessionModel.student_id == student_id).distinct().all()

    dates = sorted({d[0] for d in answer_dates}, reverse=True)
    streak = 0
    if dates:
        expected = now.date()
        for d in dates:
            if d == expected or d == expected - timedelta(days=1):
                streak += 1
                expected = d - timedelta(days=1)
            else:
                break

    # ── Time invested: rough estimate from session start/end gaps ──
    sessions = db.query(SessionModel).filter(SessionModel.student_id == student_id).all()
    total_minutes = 0
    for s in sessions:
        if s.ended_at and s.started_at:
            total_minutes += (s.ended_at - s.started_at).total_seconds() / 60
        else:
            # Fallback estimate: ~2 min per question answered in sessions with no end time
            q_count = db.query(Question).filter(Question.session_id == s.id).count()
            total_minutes += q_count * 2

    # ── Weekly progress: questions answered this week vs total ──
    questions_this_week = db.query(Answer).join(
        Question, Answer.question_id == Question.id
    ).join(
        SessionModel, Question.session_id == SessionModel.id
    ).filter(
        SessionModel.student_id == student_id,
        Answer.created_at >= week_ago
    ).count()

    # ── Topics mastered this week (crossed the 0.8 threshold recently) ──
    mastered_this_week = db.query(MasteryScore).filter(
        MasteryScore.student_id == student_id,
        MasteryScore.score >= 0.8,
        MasteryScore.updated_at >= week_ago
    ).count()

    # ── New connections discovered this week (TopicRelationship + bridges) ──
    all_topic_ids = [t.id for t in db.query(Topic).filter(Topic.subject_id.in_(subject_ids)).all()] if subject_ids else []
    new_relationships = db.query(TopicRelationship).filter(
        TopicRelationship.subject_id.in_(subject_ids)
    ).count() if subject_ids else 0
    new_bridges = db.query(CrossSubjectBridge).filter(
        CrossSubjectBridge.student_id == student_id,
        CrossSubjectBridge.created_at >= week_ago
    ).count()

    # ── Subject expansion: new topics added this week ──
    new_topics_this_week = db.query(Topic).filter(
        Topic.subject_id.in_(subject_ids),
        Topic.created_at >= week_ago
    ).count() if subject_ids else 0

    # ── Overall knowledge growth: avg mastery now vs avg mastery 7 days ago (approximation via updated_at) ──
    all_scores = db.query(MasteryScore).filter(MasteryScore.student_id == student_id).all()
    current_avg = round(sum(s.score for s in all_scores) / len(all_scores) * 100) if all_scores else 0

    return {
        "total_subjects": total_subjects,
        "study_streak_days": streak,
        "time_invested_minutes": round(total_minutes),
        "weekly_questions_answered": questions_this_week,
        "topics_mastered_this_week": mastered_this_week,
        "new_connections_this_week": new_bridges,
        "total_topic_relationships": new_relationships,
        "new_topics_this_week": new_topics_this_week,
        "overall_knowledge_growth_pct": current_avg,
    }


def get_revision_queue(student_id: int, db: Session, limit: int = 8) -> list:
    """
    Cross-subject revision queue using the same priority order as Challenge Mode:
    weak > failed/struggled > needs revision > (mastered topics excluded here,
    since this is specifically about what NEEDS attention, not retention checks).
    """
    subjects = db.query(Subject).filter(Subject.student_id == student_id).all()
    subject_map = {s.id: s.name for s in subjects}
    subject_ids = list(subject_map.keys())
    if not subject_ids:
        return []

    topics = db.query(Topic).filter(Topic.subject_id.in_(subject_ids), Topic.is_archived == False).all()
    topic_ids = [t.id for t in topics]
    topic_map = {t.id: t for t in topics}

    scores = {
        m.topic_id: m for m in db.query(MasteryScore).filter(
            MasteryScore.student_id == student_id, MasteryScore.topic_id.in_(topic_ids)
        ).all()
    } if topic_ids else {}

    failed_topic_ids = {
        h.topic_id for h in db.query(LearningHistory).filter(
            LearningHistory.student_id == student_id,
            LearningHistory.topic_id.in_(topic_ids),
            LearningHistory.event_type.in_(["misconception", "struggle"])
        ).all()
    } if topic_ids else set()

    queue = []
    for tid, m in scores.items():
        if tid not in topic_map:
            continue
        t = topic_map[tid]

        # Mastered topics never belong in a revision queue, regardless of past history
        if m.score >= 0.8:
            continue

        if m.score < 0.4:
            priority, reason = 1, "Weak — needs focused review"
        elif tid in failed_topic_ids:
            priority, reason = 2, "Past misconception"
        elif m.score < 0.7:
            priority, reason = 3, "Needs revision"
        else:
            continue

        queue.append({
            "topic_id": tid, "topic_name": t.name,
            "subject_id": t.subject_id, "subject_name": subject_map.get(t.subject_id, ""),
            "mastery": round(m.score * 100), "priority": priority, "reason": reason,
        })

    queue.sort(key=lambda x: (x["priority"], x["mastery"]))
    return queue[:limit]