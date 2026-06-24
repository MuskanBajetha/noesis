import json
import os
from groq import Groq
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from app.models.database import Topic, Subject, CrossSubjectBridge

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"


def discover_cross_subject_bridges(student_id: int, db: Session, max_bridges: int = 15) -> dict:
    """
    Look across ALL of a student's subjects and ask the LLM to find genuinely
    interesting interdisciplinary connections between topics in DIFFERENT
    subjects (e.g. Gradient Descent <-> Calculus, Neurons <-> Biology).

    This is intentionally a periodic/on-demand operation, not run on every
    upload, since it scales with total topic count across all subjects.
    """
    subjects = db.query(Subject).filter(Subject.student_id == student_id).all()
    if len(subjects) < 2:
        return {"bridges_created": 0, "reason": "Need at least 2 subjects to find cross-subject bridges"}

    topics_by_subject = {}
    topic_lookup = {}
    for s in subjects:
        topics = db.query(Topic).filter(Topic.subject_id == s.id, Topic.is_archived == False).all()
        if topics:
            topics_by_subject[s.name] = [t.name for t in topics]
            for t in topics:
                topic_lookup[(s.name, t.name)] = t.id

    if len(topics_by_subject) < 2:
        return {"bridges_created": 0, "reason": "Need topics in at least 2 different subjects"}

    subjects_block = "\n\n".join([
        f"Subject: {name}\nTopics: {', '.join(topics)}"
        for name, topics in topics_by_subject.items()
    ])

    prompt = f"""You are mapping interdisciplinary connections across a student's areas of study.

{subjects_block}

Find genuinely meaningful but NON-OBVIOUS connections between topics that belong to
DIFFERENT subjects above. These should feel like discoveries — e.g. "Gradient Descent"
(Machine Learning) relates to "Calculus" (Mathematics) through derivatives, or "Neurons"
(Biology) relates to "Neural Networks" (AI) through the inspiration for the architecture.

Do NOT connect topics within the same subject. Only cross-subject pairs.
Find at most {max_bridges} of the strongest, most interesting connections.

Return a JSON array, nothing else:
[
  {{"subject_a": "Mathematics", "topic_a": "Calculus", "subject_b": "Machine Learning", "topic_b": "Gradient Descent", "relationship": "one sentence on the connection", "strength": 0.0-1.0}}
]"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=1200
    )

    try:
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        bridges = json.loads(raw)
    except Exception:
        return {"bridges_created": 0, "reason": "Could not parse LLM response"}

    # Clear old bridges before inserting fresh ones — avoids stale/duplicate edges
    db.query(CrossSubjectBridge).filter(CrossSubjectBridge.student_id == student_id).delete()

    created = 0
    for b in bridges:
        key_a = (b.get("subject_a"), b.get("topic_a"))
        key_b = (b.get("subject_b"), b.get("topic_b"))
        topic_a_id = topic_lookup.get(key_a)
        topic_b_id = topic_lookup.get(key_b)
        if not topic_a_id or not topic_b_id or topic_a_id == topic_b_id:
            continue

        db.add(CrossSubjectBridge(
            student_id=student_id,
            topic_a_id=topic_a_id,
            topic_b_id=topic_b_id,
            relationship_description=b.get("relationship", ""),
            strength=float(b.get("strength", 0.5))
        ))
        created += 1

    db.commit()
    return {"bridges_created": created}