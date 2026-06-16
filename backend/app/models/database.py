from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ── Models ──────────────────────────────────────────────

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    total_study_time = Column(Integer, default=0)  # in minutes
    streak_days = Column(Integer, default=0)
    last_active = Column(DateTime, default=datetime.utcnow)

    sessions = relationship("Session", back_populates="student")
    mastery_scores = relationship("MasteryScore", back_populates="student")
    learning_history = relationship("LearningHistory", back_populates="student")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    topic = Column(String, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    completed = Column(Boolean, default=False)
    questions_asked = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)

    student = relationship("Student", back_populates="sessions")
    questions = relationship("Question", back_populates="session")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    question_text = Column(Text, nullable=False)
    question_type = Column(String, default="socratic")
    topic = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="questions")
    answers = relationship("Answer", back_populates="question")


class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"))
    student_response = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=True)
    misconception_detected = Column(Boolean, default=False)
    misconception_type = Column(String, nullable=True)
    feedback = Column(Text, nullable=True)
    understanding_level = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    question = relationship("Question", back_populates="answers")


class MasteryScore(Base):
    __tablename__ = "mastery_scores"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    topic = Column(String, nullable=False)
    score = Column(Float, default=0.0)
    questions_attempted = Column(Integer, default=0)
    misconceptions_count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="mastery_scores")


class LearningHistory(Base):
    __tablename__ = "learning_history"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    topic = Column(String, nullable=False)
    event_type = Column(String, nullable=False)  # misconception, mastery, struggle, breakthrough
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="learning_history")


# ── DB Init ──────────────────────────────────────────────

def init_db():
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()