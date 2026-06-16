from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.models.database import get_db, Student, Session as SessionModel, Question, Answer, MasteryScore
from app.services.groq_service import generate_socratic_question, evaluate_student_response
from datetime import datetime

router = APIRouter()

# ── Pydantic Schemas ─────────────────────────────────────

class GenerateQuestionRequest(BaseModel):
    topic: str
    student_id: int
    session_id: Optional[int] = None

class EvaluateAnswerRequest(BaseModel):
    question_id: int
    student_response: str
    student_id: int

class CreateStudentRequest(BaseModel):
    name: str
    email: str

# ── Helpers ──────────────────────────────────────────────

def get_student_level(student_id: int, topic: str, db: Session) -> str:
    mastery = db.query(MasteryScore).filter(
        MasteryScore.student_id == student_id,
        MasteryScore.topic == topic
    ).first()

    if not mastery:
        return "beginner"
    if mastery.score >= 0.8:
        return "advanced"
    if mastery.score >= 0.4:
        return "intermediate"
    return "beginner"

def update_mastery(student_id: int, topic: str, understanding: str, db: Session):
    delta = {
        "none": -0.05,
        "partial": 0.05,
        "good": 0.1,
        "excellent": 0.15
    }.get(understanding, 0)

    mastery = db.query(MasteryScore).filter(
        MasteryScore.student_id == student_id,
        MasteryScore.topic == topic
    ).first()

    if mastery:
        mastery.score = max(0.0, min(1.0, mastery.score + delta))
        mastery.updated_at = datetime.utcnow()
    else:
        mastery = MasteryScore(
            student_id=student_id,
            topic=topic,
            score=max(0.0, 0.5 + delta)
        )
        db.add(mastery)

    db.commit()

# ── Routes ───────────────────────────────────────────────

@router.post("/students")
def create_student(request: CreateStudentRequest, db: Session = Depends(get_db)):
    existing = db.query(Student).filter(Student.email == request.email).first()
    if existing:
        return {"student_id": existing.id, "message": "Student already exists"}

    student = Student(name=request.name, email=request.email)
    db.add(student)
    db.commit()
    db.refresh(student)
    return {"student_id": student.id, "message": "Student created successfully"}


@router.post("/generate-question")
def generate_question(request: GenerateQuestionRequest, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == request.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    student_level = get_student_level(request.student_id, request.topic, db)
    question_text = generate_socratic_question(request.topic, student_level)

    # Create or get session
    if request.session_id:
        session = db.query(SessionModel).filter(SessionModel.id == request.session_id).first()
    else:
        session = SessionModel(student_id=request.student_id, topic=request.topic)
        db.add(session)
        db.commit()
        db.refresh(session)

    # Save question
    question = Question(
        session_id=session.id,
        question_text=question_text,
        question_type=student_level,
        topic=request.topic
    )
    db.add(question)
    db.commit()
    db.refresh(question)

    return {
        "question_id": question.id,
        "session_id": session.id,
        "question": question_text,
        "student_level": student_level,
        "topic": request.topic
    }


@router.post("/evaluate-answer")
def evaluate_answer(request: EvaluateAnswerRequest, db: Session = Depends(get_db)):
    question = db.query(Question).filter(Question.id == request.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    evaluation = evaluate_student_response(
        question.question_text,
        request.student_response,
        question.topic
    )

    answer = Answer(
        question_id=request.question_id,
        student_response=request.student_response,
        misconception_detected=evaluation["misconception_detected"],
        misconception_type=evaluation.get("misconception_type"),
        feedback=evaluation["feedback"]
    )
    db.add(answer)
    db.commit()

    update_mastery(request.student_id, question.topic, evaluation["understanding_level"], db)

    return {
        "feedback": evaluation["feedback"],
        "understanding_level": evaluation["understanding_level"],
        "misconception_detected": evaluation["misconception_detected"],
        "misconception_type": evaluation.get("misconception_type"),
        "follow_up_needed": evaluation["follow_up_needed"]
    }


@router.get("/student-progress/{student_id}")
def get_student_progress(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    mastery_scores = db.query(MasteryScore).filter(MasteryScore.student_id == student_id).all()
    sessions = db.query(SessionModel).filter(SessionModel.student_id == student_id).all()

    return {
        "student_name": student.name,
        "total_sessions": len(sessions),
        "mastery_scores": [
            {"topic": m.topic, "score": round(m.score, 2)} for m in mastery_scores
        ]
    }