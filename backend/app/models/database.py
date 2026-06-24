from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean,
    DateTime, Text, ForeignKey, JSON, Enum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
import enum

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class SubjectKind(str, enum.Enum):
    custom = "custom"
    prebuilt = "prebuilt"


# ── Core Identity ────────────────────────────────────────

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=True)  # null for OAuth-only users
    auth_provider = Column(String, default="credentials")  # credentials | google
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    streak_days = Column(Integer, default=0)

    subjects = relationship("Subject", back_populates="student")


# ── Subjects (Domains) ───────────────────────────────────

class PrebuiltDomain(Base):
    """Catalog of ready-made domains, e.g. Physics, Finance, AI."""
    __tablename__ = "prebuilt_domains"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)         # "Physics"
    slug = Column(String, unique=True, nullable=False)          # "physics"
    description = Column(Text, nullable=True)
    icon = Column(String, nullable=True)                        # lucide icon name
    seed_topics = Column(JSON, default=list)                    # ["Newton's Laws", "Thermodynamics", ...]


class Subject(Base):
    """
    A learning domain instance owned by a student.
    Either spun up from a PrebuiltDomain, or fully custom with uploaded material.
    """
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    name = Column(String, nullable=False)                       # "Polity", "Machine Learning"
    kind = Column(Enum(SubjectKind), default=SubjectKind.custom)
    prebuilt_domain_id = Column(Integer, ForeignKey("prebuilt_domains.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_studied_at = Column(DateTime, nullable=True)
    last_topic = Column(String, nullable=True)                  # for "resume where you left off"

    student = relationship("Student", back_populates="subjects")
    topics = relationship("Topic", back_populates="subject", cascade="all, delete-orphan")
    documents = relationship("UploadedDocument", back_populates="subject", cascade="all, delete-orphan")


class Topic(Base):
    """
    A topic/subtopic that belongs to exactly one Subject.
    Auto-extracted from uploads, or seeded from a PrebuiltDomain.
    """
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    source_document_id = Column(Integer, ForeignKey("uploaded_documents.id"), nullable=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    subject = relationship("Subject", back_populates="topics")
    mastery_scores = relationship("MasteryScore", back_populates="topic", cascade="all, delete-orphan")


class TopicRelationship(Base):
    """Edges between topics within the SAME subject — powers the concept graph."""
    __tablename__ = "topic_relationships"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    topic_a_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    topic_b_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    strength = Column(Float, default=1.0)

class CrossSubjectBridge(Base):
    """
    Weak, interdisciplinary links between topics in DIFFERENT subjects.
    Computed periodically by an LLM pass over a student's full topic set,
    not auto-generated at upload time (too expensive to run on every upload).
    """
    __tablename__ = "cross_subject_bridges"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    topic_a_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    topic_b_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    relationship_description = Column(Text, nullable=True)
    strength = Column(Float, default=0.5)
    created_at = Column(DateTime, default=datetime.utcnow)


class UploadedDocument(Base):
    """Tracks PDFs uploaded for a subject — for replace/add-more workflows."""
    __tablename__ = "uploaded_documents"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    filename = Column(String, nullable=False)
    chunks_stored = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    subject = relationship("Subject", back_populates="documents")
    topics = relationship("Topic", backref="source_document")


# ── Learning Activity (now subject + topic scoped) ──────

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    topic_id = Column(Integer, ForeignKey("topics.id"))
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    completed = Column(Boolean, default=False)
    visual_aid_preferences = Column(JSON, default=lambda: ["diagram", "plot", "image", "video"])

    questions = relationship("Question", back_populates="session")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    topic_id = Column(Integer, ForeignKey("topics.id"))
    question_text = Column(Text, nullable=False)
    question_type = Column(String, default="socratic")
    target_stage = Column(String, default="recognition")
    attempt_count = Column(Integer, default=0)
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
    topic_id = Column(Integer, ForeignKey("topics.id"))
    score = Column(Float, default=0.5)
    questions_attempted = Column(Integer, default=0)
    misconceptions_count = Column(Integer, default=0)
    pedagogical_stage = Column(String, default="recognition")
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    topic = relationship("Topic", back_populates="mastery_scores")


class LearningHistory(Base):
    __tablename__ = "learning_history"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    topic_id = Column(Integer, ForeignKey("topics.id"))
    event_type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── DB Init ──────────────────────────────────────────────

def init_db():
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")
    seed_prebuilt_domains()


def seed_prebuilt_domains():
    db = SessionLocal()
    try:
        existing = db.query(PrebuiltDomain).count()
        if existing > 0:
            return

        domains = [
            {
                "name": "Physics", "slug": "physics", "icon": "Atom",
                "description": "Mechanics, thermodynamics, and the forces that govern motion.",
                "seed_topics": ["Newton's Laws", "Gravity", "Thermodynamics", "Quantum Physics", "Energy & Work"]
            },
            {
                "name": "Mathematics", "slug": "mathematics", "icon": "Sigma",
                "description": "Algebra, calculus, and the structures underneath them.",
                "seed_topics": ["Algebra", "Calculus", "Probability", "Linear Algebra", "Geometry"]
            },
            {
                "name": "Finance", "slug": "finance", "icon": "TrendingUp",
                "description": "Markets, valuation, and how money moves.",
                "seed_topics": ["Time Value of Money", "Stocks & Bonds", "Financial Statements", "Risk & Return", "Derivatives"]
            },
            {
                "name": "Economics", "slug": "economics", "icon": "LineChart",
                "description": "Supply, demand, and the incentives that shape markets.",
                "seed_topics": ["Supply & Demand", "Inflation", "Market Structures", "Fiscal Policy", "Monetary Policy"]
            },
            {
                "name": "Artificial Intelligence", "slug": "ai", "icon": "Brain",
                "description": "Machine learning, neural networks, and how machines learn.",
                "seed_topics": ["Linear Regression", "Neural Networks", "Transformers", "Evaluation Metrics", "Reinforcement Learning"]
            },
            {
                "name": "Global News", "slug": "global-news", "icon": "Globe",
                "description": "Current events and the context behind them.",
                "seed_topics": ["Geopolitics", "Climate Policy", "Trade", "Elections", "Conflict & Diplomacy"]
            },
            {
                "name": "Sports", "slug": "sports", "icon": "Trophy",
                "description": "Rules, strategy, and the numbers behind the game.",
                "seed_topics": ["Game Strategy", "Player Statistics", "Rules & Officiating", "Sports History", "Team Dynamics"]
            },
            {
                "name": "Indian Polity", "slug": "polity", "icon": "Landmark",
                "description": "The Constitution, government structure, and how power is organized.",
                "seed_topics": ["President", "Vice President", "Parliament", "Judiciary", "Fundamental Rights"]
            },
        ]

        for d in domains:
            db.add(PrebuiltDomain(**d))
        db.commit()
        print(f"✅ Seeded {len(domains)} prebuilt domains")
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()