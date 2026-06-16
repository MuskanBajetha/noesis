import os
from app.services.misconception_service import get_misconception_analytics
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.models.database import get_db, Student, Session as SessionModel, Question, Answer, MasteryScore, LearningHistory
from app.services.groq_service import generate_socratic_question, evaluate_student_response
from datetime import datetime
from app.services.rag_service import process_and_store_pdf, retrieve_context, get_collection_stats
import tempfile
import shutil
from fastapi import UploadFile, File, Form
from app.services.memory_service import (
    get_student_profile, get_topic_memory,
    update_mastery_detailed, build_personalized_context,
    record_learning_event
)
from app.services.knowledge_tracing import knowledge_tracer

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
        feedback=evaluation["feedback"],
        understanding_level=evaluation["understanding_level"]
    )
    db.add(answer)
    db.commit()

    # Use detailed mastery update with memory
    update_mastery_detailed(
        request.student_id,
        question.topic,
        evaluation["understanding_level"],
        evaluation["misconception_detected"],
        db,
        misconception_type=evaluation.get("misconception_type")
    )

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

@router.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    topic: str = Form(...)
):
    """Upload a PDF and store it in ChromaDB for RAG."""
    # Accept any file with pdf content type or .pdf extension
    filename = file.filename or ""
    content_type = file.content_type or ""
    
    if not (filename.lower().endswith(".pdf") or "pdf" in content_type.lower()):
        raise HTTPException(status_code=400, detail=f"Only PDF files are supported. Got: {filename}, type: {content_type}")

    contents = await file.read()
    
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="File is empty")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        result = process_and_store_pdf(tmp_path, topic)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    finally:
        os.unlink(tmp_path)

    return result


@router.get("/rag-stats")
def rag_stats():
    """Get RAG collection statistics."""
    return get_collection_stats()


@router.post("/generate-question-rag")
def generate_question_rag(request: GenerateQuestionRequest, db: Session = Depends(get_db)):
    """Generate a Socratic question grounded in uploaded learning material + student memory."""
    student = db.query(Student).filter(Student.id == request.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    student_level = get_student_level(request.student_id, request.topic, db)

    # Get RAG context from documents
    rag_context = retrieve_context(request.topic, request.topic)

    # Get personalized context from student memory
    personal_context = build_personalized_context(request.student_id, request.topic, db)

    # Combine both contexts
    combined_context = ""
    if rag_context:
        combined_context += f"LEARNING MATERIAL:\n{rag_context}"
    if personal_context:
        combined_context += f"\n\nSTUDENT PROFILE:\n{personal_context}"

    question_text = generate_socratic_question(request.topic, student_level, combined_context)

    if request.session_id:
        session = db.query(SessionModel).filter(SessionModel.id == request.session_id).first()
    else:
        session = SessionModel(student_id=request.student_id, topic=request.topic)
        db.add(session)
        db.commit()
        db.refresh(session)

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
        "topic": request.topic,
        "rag_used": bool(rag_context),
        "personalized": bool(personal_context),
        "context_preview": rag_context[:200] + "..." if rag_context else None
    }

@router.get("/student-profile/{student_id}")
def get_profile(student_id: int, db: Session = Depends(get_db)):
    """Get detailed student learning profile."""
    profile = get_student_profile(student_id, db)
    if not profile:
        raise HTTPException(status_code=404, detail="Student not found")
    return profile


@router.get("/topic-memory/{student_id}/{topic}")
def get_memory(student_id: int, topic: str, db: Session = Depends(get_db)):
    """Get student's memory for a specific topic."""
    memory = get_topic_memory(student_id, topic, db)
    return memory

@router.get("/misconception-analytics/{student_id}")
def misconception_analytics(student_id: int, db: Session = Depends(get_db)):
    """Get misconception analytics for a student."""
    history = db.query(LearningHistory).filter(
        LearningHistory.student_id == student_id,
        LearningHistory.event_type == "misconception"
    ).all()

    misconceptions = [{"misconception_type": h.description, "topic": h.topic} for h in history]
    analytics = get_misconception_analytics(misconceptions)

    # Group by topic
    by_topic = {}
    for h in history:
        if h.topic not in by_topic:
            by_topic[h.topic] = 0
        by_topic[h.topic] += 1

    return {
        "total_misconceptions": len(history),
        "analytics": analytics,
        "by_topic": by_topic,
        "recent": [
            {"topic": h.topic, "description": h.description, "date": h.created_at}
            for h in history[-5:]
        ]
    }

@router.get("/knowledge-state/{student_id}")
def get_knowledge_state(student_id: int, db: Session = Depends(get_db)):
    """Get DKT-estimated mastery probabilities for all topics."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    mastery = knowledge_tracer.get_student_mastery(student_id, db)
    recommendations = knowledge_tracer.get_next_topic_recommendation(mastery)

    return {
        "student_id": student_id,
        "student_name": student.name,
        "mastery_probabilities": mastery,
        "recommendations": recommendations,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/train-dkt/{student_id}")
def train_dkt(student_id: int, db: Session = Depends(get_db)):
    """Train/update DKT model on student interaction data."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    result = knowledge_tracer.train_on_student_data(student_id, db)
    return result