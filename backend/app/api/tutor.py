import os
import tempfile
import shutil
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.models.database import (
    get_db, Student, Subject, Topic, TopicRelationship,
    UploadedDocument, PrebuiltDomain, Session as SessionModel,
    Question, Answer, MasteryScore, LearningHistory, SubjectKind, CrossSubjectBridge
)
from app.services.groq_service import generate_socratic_question, evaluate_student_response
from app.services.rag_service import (
    process_and_store_pdf, retrieve_context,
    get_subject_chunk_count, delete_subject_material, delete_document_material
)
from app.services.topic_extraction import extract_topics_from_text, suggest_topic_relationships
from app.services.memory_service import (
    get_topic_memory, update_mastery_detailed,
    build_personalized_context, record_learning_event
)
from app.services.adaptive_engine import (
    generate_adaptive_question, get_concept_graph, get_learning_journey, get_global_knowledge_graph, select_challenge_topic
)
from app.services.evaluation import generate_full_evaluation_report, calculate_learning_gain
from app.services.auth_service import (
    register_credentials_student, authenticate_credentials_student, get_or_create_oauth_student
)
from app.services.bridge_discovery import discover_cross_subject_bridges
from app.services.dashboard_stats import get_dashboard_overview, get_revision_queue

router = APIRouter()

def build_full_explanation_response(question, topic, db: Session) -> dict:
    """
    Single source of truth for building a full-explanation response, used by
    BOTH the genuine-attempt (Category A) and confusion (Category B) paths
    at attempt 3+. This MUST stay as one function — duplicating this logic
    is exactly what caused aids to silently stop appearing for "I don't know"
    responses while working for genuine attempts (or vice versa).
    """
    from app.services.plot_renderer import render_function_plot
    from app.services.image_retrieval import search_educational_image
    from app.services.web_grounding import search_trusted_sources
    from app.services.youtube_search import search_educational_video
    from app.services.aid_query_generator import generate_aid_queries
    from app.services.pedagogy_engine import generate_full_explanation

    session_row = db.query(SessionModel).filter(SessionModel.id == question.session_id).first()
    enabled_aids = session_row.visual_aid_preferences if session_row and session_row.visual_aid_preferences else []

    context = retrieve_context(topic.name, topic.subject_id, n_results=2)
    web_sources = search_trusted_sources(question.question_text, topic.name)

    raw_explanation = generate_full_explanation(question.question_text, topic.name, context, web_sources, enabled_aids=[])

    plots, images, videos = [], [], []

    if enabled_aids:
        aid_content = generate_aid_queries(topic.name, question.question_text, enabled_aids)

        if "diagram" in enabled_aids and aid_content.get("diagram"):
            raw_explanation += f"\n\n```mermaid\n{aid_content['diagram']}\n```"

        if "plot" in enabled_aids and aid_content.get("plot"):
            spec = aid_content["plot"]
            computed = render_function_plot(
                spec.get("expression", "x"),
                float(spec.get("x_min", -10)),
                float(spec.get("x_max", 10)),
            )
            if computed:
                plots.append({
                    "type": "function", "x": computed["x"], "y": computed["y"],
                    "title": spec.get("title", ""), "x_label": spec.get("x_label", "x"),
                    "y_label": spec.get("y_label", "y"),
                })
                raw_explanation += f"\n\n[[PLOT_{len(plots) - 1}]]"

        if "image" in enabled_aids and aid_content.get("image"):
            result = search_educational_image(aid_content["image"])
            if result:
                images.append(result)
                raw_explanation += f"\n\n[[IMAGE_{len(images) - 1}]]"

        if "video" in enabled_aids and aid_content.get("video"):
            result = search_educational_video(aid_content["video"], topic.name)
            if result:
                videos.append(result)
                raw_explanation += f"\n\n[[VIDEO_{len(videos) - 1}]]"

    return {
        "feedback": raw_explanation, "plots": plots, "images": images,
        "videos": videos, "sources": web_sources,
        "hint_level": "full_explanation", "follow_up_needed": True,
    }


# ── Schemas ───────────────────────────────────────────────

class CreateStudentRequest(BaseModel):
    name: str
    email: str

class CreateCustomSubjectRequest(BaseModel):
    student_id: int
    name: str

class CreatePrebuiltSubjectRequest(BaseModel):
    student_id: int
    prebuilt_domain_id: int

class GenerateQuestionRequest(BaseModel):
    topic_id: int
    student_id: int
    subject_id: int
    session_id: Optional[int] = None

class EvaluateAnswerRequest(BaseModel):
    question_id: int
    student_response: str
    student_id: int

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class OAuthLoginRequest(BaseModel):
    name: str
    email: str

class UpdatePreferencesRequest(BaseModel):
    session_id: int
    visual_aid_preferences: list[str]

# ── Students ──────────────────────────────────────────────

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

@router.post("/auth/register")
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    result = register_credentials_student(request.name, request.email, request.password, db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/auth/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    result = authenticate_credentials_student(request.email, request.password, db)
    if "error" in result:
        raise HTTPException(status_code=401, detail=result["error"])
    return result


@router.post("/auth/oauth-login")
def oauth_login(request: OAuthLoginRequest, db: Session = Depends(get_db)):
    student = get_or_create_oauth_student(request.email, request.name, db)
    return {"student_id": student.id, "name": student.name, "email": student.email}


# ── Prebuilt Domain Catalog ───────────────────────────────

@router.get("/prebuilt-domains")
def list_prebuilt_domains(db: Session = Depends(get_db)):
    domains = db.query(PrebuiltDomain).all()
    return [
        {
            "id": d.id, "name": d.name, "slug": d.slug,
            "description": d.description, "icon": d.icon,
            "topic_count": len(d.seed_topics or [])
        }
        for d in domains
    ]


# ── Subjects ──────────────────────────────────────────────

@router.get("/subjects/{student_id}")
def list_student_subjects(student_id: int, db: Session = Depends(get_db)):
    """List all subjects for a student — powers the 'returning user' dashboard."""
    subjects = db.query(Subject).filter(Subject.student_id == student_id).all()
    result = []
    for s in subjects:
        topics = db.query(Topic).filter(Topic.subject_id == s.id, Topic.is_archived == False).all()
        topic_ids = [t.id for t in topics]

        scores = db.query(MasteryScore).filter(
            MasteryScore.student_id == student_id,
            MasteryScore.topic_id.in_(topic_ids)
        ).all() if topic_ids else []

        topics_learned = len(scores)  # topics with at least one studied interaction
        overall_mastery = round(sum(sc.score for sc in scores) / len(scores) * 100) if scores else 0

        result.append({
            "id": s.id,
            "name": s.name,
            "kind": s.kind.value if hasattr(s.kind, "value") else s.kind,
            "topic_count": len(topics),
            "topics_learned": topics_learned,
            "overall_mastery": overall_mastery,
            "last_studied_at": s.last_studied_at.isoformat() if s.last_studied_at else None,
            "last_topic": s.last_topic,
            "created_at": s.created_at.isoformat(),
        })
    return result


@router.post("/subjects/custom")
def create_custom_subject(request: CreateCustomSubjectRequest, db: Session = Depends(get_db)):
    """Step 1 of Option A: define a custom learning domain. Topics come later via upload."""
    subject = Subject(
        student_id=request.student_id,
        name=request.name,
        kind=SubjectKind.custom
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return {"subject_id": subject.id, "name": subject.name, "kind": "custom"}


@router.post("/subjects/prebuilt")
def create_prebuilt_subject(request: CreatePrebuiltSubjectRequest, db: Session = Depends(get_db)):
    """Option B: spin up a subject from a prebuilt domain, seeding its topics immediately."""
    domain = db.query(PrebuiltDomain).filter(PrebuiltDomain.id == request.prebuilt_domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Prebuilt domain not found")
    
    # Reuse existing subject if this student already has this prebuilt domain
    existing = db.query(Subject).filter(
        Subject.student_id == request.student_id,
        Subject.prebuilt_domain_id == domain.id
    ).first()
    if existing:
        return {"subject_id": existing.id, "name": existing.name, "kind": "prebuilt", "topics_created": 0, "reused": True}


    subject = Subject(
        student_id=request.student_id,
        name=domain.name,
        kind=SubjectKind.prebuilt,
        prebuilt_domain_id=domain.id
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)

    # Seed topics directly from the catalog — no LLM call needed, names are curated
    created_topics = []
    for topic_name in (domain.seed_topics or []):
        t = Topic(subject_id=subject.id, name=topic_name)
        db.add(t)
        created_topics.append(t)
    db.commit()

    # Suggest relationships among the seeded topics
    topic_names = [t.name for t in created_topics]
    pairs = suggest_topic_relationships(topic_names)
    name_to_id = {t.name: t.id for t in created_topics}
    for a, b in pairs:
        if a in name_to_id and b in name_to_id:
            db.add(TopicRelationship(subject_id=subject.id, topic_a_id=name_to_id[a], topic_b_id=name_to_id[b]))
    db.commit()

    return {
        "subject_id": subject.id,
        "name": subject.name,
        "kind": "prebuilt",
        "topics_created": len(created_topics)
    }


@router.get("/subjects/{subject_id}/topics")
def list_subject_topics(subject_id: int, include_archived: bool = False, db: Session = Depends(get_db)):
    query = db.query(Topic).filter(Topic.subject_id == subject_id)
    if not include_archived:
        query = query.filter(Topic.is_archived == False)
    topics = query.all()
    return [{"id": t.id, "name": t.name, "description": t.description} for t in topics]


# ── Upload Material (Option A, Step 2 + 3) ───────────────

@router.post("/subjects/{subject_id}/upload")
async def upload_material(
    subject_id: int,
    file: UploadFile = File(...),
    replace_document_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload a PDF for a custom subject.
    - If replace_document_id is provided: removes ONLY that document's chunks
      and topics (and their mastery/history), then processes the new file as
      a fresh document in the same subject.
    - If omitted: simply adds the new document alongside existing ones.
    """
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    filename = file.filename or ""
    if not (filename.lower().endswith(".pdf") or "pdf" in (file.content_type or "").lower()):
        raise HTTPException(status_code=400, detail=f"Only PDF files are supported. Got: {filename}")

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="File is empty")

    # ── Document-scoped replace: clean up ONLY the targeted document ──
    if replace_document_id:
        old_doc = db.query(UploadedDocument).filter(
            UploadedDocument.id == replace_document_id,
            UploadedDocument.subject_id == subject_id
        ).first()
        if not old_doc:
            raise HTTPException(status_code=404, detail="Document to replace not found in this subject")

        # Remove this document's RAG chunks — material itself is fully gone
        delete_document_material(replace_document_id)

        old_topics = db.query(Topic).filter(Topic.source_document_id == replace_document_id).all()
        old_topic_ids = [t.id for t in old_topics]

        if old_topic_ids:
            # Topics with NO study history can be safely hard-deleted
            topic_ids_with_sessions = {
                row[0] for row in db.query(SessionModel.topic_id).filter(
                    SessionModel.topic_id.in_(old_topic_ids)
                ).distinct().all()
            }
            clean_ids = [tid for tid in old_topic_ids if tid not in topic_ids_with_sessions]
            studied_ids = [tid for tid in old_topic_ids if tid in topic_ids_with_sessions]

            if clean_ids:
                db.query(TopicRelationship).filter(
                    (TopicRelationship.topic_a_id.in_(clean_ids)) |
                    (TopicRelationship.topic_b_id.in_(clean_ids))
                ).delete(synchronize_session=False)
                db.query(MasteryScore).filter(MasteryScore.topic_id.in_(clean_ids)).delete(synchronize_session=False)
                db.query(Topic).filter(Topic.id.in_(clean_ids)).delete(synchronize_session=False)

            if studied_ids:
                # Has real history — archive instead of delete. Drop its graph
                # edges (so it vanishes from the active concept graph) but keep
                # the Topic row, MasteryScore, sessions, and learning_history intact.
                db.query(TopicRelationship).filter(
                    (TopicRelationship.topic_a_id.in_(studied_ids)) |
                    (TopicRelationship.topic_b_id.in_(studied_ids))
                ).delete(synchronize_session=False)
                db.query(Topic).filter(Topic.id.in_(studied_ids)).update(
                    {Topic.is_archived: True}, synchronize_session=False
                )

        db.delete(old_doc)
        db.commit()

    # ── Process the new file ──
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    # Create the UploadedDocument row FIRST so we have a real id to tag chunks with
    new_doc = UploadedDocument(subject_id=subject_id, filename=filename, chunks_stored=0)
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    try:
        result = process_and_store_pdf(tmp_path, subject_id, filename, new_doc.id)
    except Exception as e:
        db.delete(new_doc)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    finally:
        os.unlink(tmp_path)

    if result["status"] != "success":
        db.delete(new_doc)
        db.commit()
        raise HTTPException(status_code=500, detail=result.get("message", "Unknown processing error"))

    new_doc.chunks_stored = result["chunks_stored"]
    db.commit()

    # Auto-extract topics from THIS document's text, tagged with its document_id
    extracted = extract_topics_from_text(result["full_text"], subject.name)
    created_topics = []
    for t in extracted:
        existing = db.query(Topic).filter(Topic.subject_id == subject_id, Topic.name == t["name"]).first()
        if existing:
            continue
        new_topic = Topic(
            subject_id=subject_id, name=t["name"], description=t.get("description"),
            source_document_id=new_doc.id
        )
        db.add(new_topic)
        created_topics.append(new_topic)
    db.commit()

    # Suggest relationships across ALL topics now in this subject
    all_topics = db.query(Topic).filter(Topic.subject_id == subject_id).all()
    topic_names = [t.name for t in all_topics]
    pairs = suggest_topic_relationships(topic_names)
    name_to_id = {t.name: t.id for t in all_topics}

    db.query(TopicRelationship).filter(TopicRelationship.subject_id == subject_id).delete()

    llm_edges = set()
    for a, b in pairs:
        if a in name_to_id and b in name_to_id:
            edge_key = tuple(sorted([name_to_id[a], name_to_id[b]]))
            if edge_key not in llm_edges:
                llm_edges.add(edge_key)
                db.add(TopicRelationship(subject_id=subject_id, topic_a_id=edge_key[0], topic_b_id=edge_key[1]))

    connected_ids = {tid for pair in llm_edges for tid in pair}
    pre_existing = [t for t in all_topics if t.name not in [nt.name for nt in created_topics]]
    anchor_id = pre_existing[0].id if pre_existing else (all_topics[0].id if all_topics else None)

    if anchor_id:
        for t in all_topics:
            if t.id != anchor_id and t.id not in connected_ids:
                edge_key = tuple(sorted([anchor_id, t.id]))
                if edge_key not in llm_edges:
                    llm_edges.add(edge_key)
                    db.add(TopicRelationship(subject_id=subject_id, topic_a_id=edge_key[0], topic_b_id=edge_key[1]))

    db.commit()

    return {
        "status": "success",
        "chunks_stored": result["chunks_stored"],
        "subject_id": subject_id,
        "document_id": new_doc.id,
        "topics_extracted": [t.name for t in created_topics],
        "total_topics": len(all_topics)
    }


@router.get("/subjects/{subject_id}/material-status")
def material_status(subject_id: int, db: Session = Depends(get_db)):
    docs = db.query(UploadedDocument).filter(UploadedDocument.subject_id == subject_id).all()
    return {
        "documents": [{"id": d.id, "filename": d.filename, "chunks": d.chunks_stored, "uploaded_at": d.uploaded_at.isoformat()} for d in docs],
        "total_chunks": get_subject_chunk_count(subject_id)
    }

@router.delete("/subjects/{subject_id}/material")
def clear_subject_material(subject_id: int, db: Session = Depends(get_db)):
    """Manual cleanup utility — wipes RAG chunks + uploaded-doc records for a subject."""
    delete_subject_material(subject_id)
    db.query(UploadedDocument).filter(UploadedDocument.subject_id == subject_id).delete()
    db.commit()
    return {"status": "cleared", "subject_id": subject_id}

# ── Tutoring ──────────────────────────────────────────────

@router.post("/generate-question-adaptive")
def generate_question_adaptive(request: GenerateQuestionRequest, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == request.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    topic = db.query(Topic).filter(Topic.id == request.topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    result = generate_adaptive_question(request.student_id, topic, request.subject_id, db)

    if request.session_id:
        session = db.query(SessionModel).filter(SessionModel.id == request.session_id).first()
    else:
        session = SessionModel(student_id=request.student_id, subject_id=request.subject_id, topic_id=topic.id)
        db.add(session)
        db.commit()
        db.refresh(session)

    question = Question(session_id=session.id, topic_id=topic.id, question_text=result["question"], question_type=result.get("stage", "recognition"), target_stage=result.get("stage", "recognition"))
    db.add(question)
    db.commit()
    db.refresh(question)

    # Track "resume where you left off"
    subject = db.query(Subject).filter(Subject.id == request.subject_id).first()
    if subject:
        subject.last_studied_at = datetime.utcnow()
        subject.last_topic = topic.name
        db.commit()

    return {"question_id": question.id, "session_id": session.id, **result}


@router.post("/evaluate-answer")
def evaluate_answer(request: EvaluateAnswerRequest, db: Session = Depends(get_db)):
    from app.services.pedagogy_engine import (
        evaluate_staged_response, generate_hint, generate_full_explanation, next_stage
    )
    from app.services.intent_classifier import classify_response

    question = db.query(Question).filter(Question.id == request.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    topic = db.query(Topic).filter(Topic.id == question.topic_id).first()
    stage = question.target_stage or "recognition"

    classification = classify_response(request.student_response)

    # Category C — gibberish/low-effort. Reject BEFORE any LLM call, no attempt
    # counter increment, no answer row saved. This is the actual fix: a student
    # cannot grind toward a hint or mastery by submitting nonsense.
    if classification["category"] == "gibberish":
        return {
            "understanding_level": None,
            "misconception_detected": False,
            "misconception_type": None,
            "attempt_number": question.attempt_count or 0,
            "resolved": False,
            "rejected": True,
            "feedback": "Please enter a meaningful response. You can either try answering the question or tell me that you're unsure (e.g., \"I don't know\" or \"I'm confused\").",
            "follow_up_needed": False,
        }

    # Category B — explicit confusion. This DOES count as an attempt (the
    # student engaged honestly), but skips straight to a hint without
    # pretending the LLM needs to "evaluate" an "I don't know" as if it
    # were a content answer.
    if classification["category"] == "confusion":
        question.attempt_count = (question.attempt_count or 0) + 1
        current_attempt = question.attempt_count

        answer = Answer(
            question_id=request.question_id,
            student_response=request.student_response,
            misconception_detected=False,
            understanding_level="none",
        )
        db.add(answer)

        if current_attempt >= 3:
            explanation_result = build_full_explanation_response(question, topic, db)
            update_mastery_detailed(request.student_id, topic.id, "none", False, db)
            db.commit()
            return {
                "understanding_level": "none", "misconception_detected": False,
                "attempt_number": current_attempt, "resolved": False,
                **explanation_result,
            }
        else:
            hint_num = 1 if current_attempt == 1 else 2
            hint = generate_hint(question.question_text, stage, topic.name, hint_num, "the student said they don't know")
            db.commit()
            return {
                "understanding_level": "none", "misconception_detected": False,
                "attempt_number": current_attempt, "resolved": False,
                "feedback": hint, "hint_level": "light" if hint_num == 1 else "guided",
                "follow_up_needed": False,
            }

    # Category A — genuine attempt, proceed exactly as before
    evaluation = evaluate_staged_response(question.question_text, stage, request.student_response, topic.name)

    answer = Answer(
        question_id=request.question_id,
        student_response=request.student_response,
        misconception_detected=evaluation["misconception_detected"],
        misconception_type=evaluation.get("misconception_type"),
        feedback=evaluation["feedback"],
        understanding_level=evaluation["understanding_level"]
    )
    db.add(answer)

    question.attempt_count = (question.attempt_count or 0) + 1
    current_attempt = question.attempt_count

    succeeded = evaluation["understanding_level"] in ("good", "excellent")

    response_payload = {
        "understanding_level": evaluation["understanding_level"],
        "misconception_detected": evaluation["misconception_detected"],
        "misconception_type": evaluation.get("misconception_type"),
        "attempt_number": current_attempt,
        "resolved": succeeded,
    }

    if succeeded:
        # Resolved — update mastery, possibly advance stage, move on to a new question
        update_mastery_detailed(
            request.student_id, topic.id, evaluation["understanding_level"],
            evaluation["misconception_detected"], db,
            misconception_type=evaluation.get("misconception_type")
        )

        mastery_row = db.query(MasteryScore).filter(
            MasteryScore.student_id == request.student_id, MasteryScore.topic_id == topic.id
        ).first()
        if mastery_row and evaluation.get("ready_to_advance"):
            mastery_row.pedagogical_stage = next_stage(mastery_row.pedagogical_stage or "recognition")
            db.commit()

        response_payload["feedback"] = evaluation["feedback"]
        response_payload["follow_up_needed"] = True

    elif current_attempt == 1:
        hint = generate_hint(question.question_text, stage, topic.name, 1, request.student_response)
        response_payload["feedback"] = hint
        response_payload["hint_level"] = "light"
        response_payload["follow_up_needed"] = False  # same question stays active

    elif current_attempt == 2:
        hint = generate_hint(question.question_text, stage, topic.name, 2, request.student_response)
        response_payload["feedback"] = hint
        response_payload["hint_level"] = "guided"
        response_payload["follow_up_needed"] = False

    else:
        explanation_result = build_full_explanation_response(question, topic, db)
        update_mastery_detailed(
            request.student_id, topic.id, "partial",
            evaluation["misconception_detected"], db,
            misconception_type=evaluation.get("misconception_type")
        )
        response_payload.update(explanation_result)

    db.commit()
    return response_payload


# ── Analytics (subject-scoped) ────────────────────────────

@router.get("/concept-graph/{subject_id}")
def concept_graph(subject_id: int, student_id: int, db: Session = Depends(get_db)):
    return get_concept_graph(subject_id, student_id, db)


@router.get("/learning-journey/{student_id}")
def learning_journey(student_id: int, subject_id: Optional[int] = None, db: Session = Depends(get_db)):
    return get_learning_journey(student_id, db, subject_id=subject_id)


@router.get("/mastery-radar/{student_id}")
def mastery_radar(student_id: int, db: Session = Depends(get_db)):
    """Multi-subject mastery dashboard data — one radar dataset per subject."""
    subjects = db.query(Subject).filter(Subject.student_id == student_id).all()
    result = []
    for s in subjects:
        topics = db.query(Topic).filter(Topic.subject_id == s.id, Topic.is_archived == False).all()
        radar_points = []
        for t in topics:
            m = db.query(MasteryScore).filter(MasteryScore.student_id == student_id, MasteryScore.topic_id == t.id).first()
            radar_points.append({"topic": t.name, "mastery": round((m.score if m else 0.0) * 100)})
        result.append({"subject_id": s.id, "subject_name": s.name, "data": radar_points})
    return result


@router.get("/evaluation-report/{student_id}")
def evaluation_report(student_id: int, subject_id: Optional[int] = None, db: Session = Depends(get_db)):
    return generate_full_evaluation_report(student_id, db, subject_id=subject_id)

@router.get("/knowledge-graph/{student_id}")
def knowledge_graph(student_id: int, db: Session = Depends(get_db)):
    """Global cross-subject knowledge graph — every subject and topic the student has ever touched."""
    return get_global_knowledge_graph(student_id, db)

@router.post("/knowledge-bridges/{student_id}/discover")
def discover_bridges(student_id: int, db: Session = Depends(get_db)):
    """Run (or re-run) cross-subject bridge discovery for a student."""
    return discover_cross_subject_bridges(student_id, db)

@router.post("/subjects/{subject_id}/challenge")
def start_challenge(subject_id: int, student_id: int, db: Session = Depends(get_db)):
    """
    Start a 'Challenge me' session — picks the highest-priority topic across
    the WHOLE subject (weak > failed > needs-revision > random mastered)
    and generates an adaptive question for it.
    """
    topic = select_challenge_topic(subject_id, student_id, db)
    if not topic:
        raise HTTPException(status_code=404, detail="No topics found in this subject")

    result = generate_adaptive_question(student_id, topic, subject_id, db)

    session = SessionModel(student_id=student_id, subject_id=subject_id, topic_id=topic.id)
    db.add(session)
    db.commit()
    db.refresh(session)

    question = Question(session_id=session.id, topic_id=topic.id, question_text=result["question"], question_type=result.get("stage", "recognition"), target_stage=result.get("stage", "recognition"))
    db.add(question)
    db.commit()
    db.refresh(question)

    return {
        "question_id": question.id, "session_id": session.id,
        "topic_id": topic.id, "topic_name": topic.name,
        **result
    }

@router.get("/dashboard/{student_id}/overview")
def dashboard_overview(student_id: int, db: Session = Depends(get_db)):
    return get_dashboard_overview(student_id, db)


@router.get("/dashboard/{student_id}/revision-queue")
def revision_queue(student_id: int, db: Session = Depends(get_db)):
    return get_revision_queue(student_id, db)


@router.delete("/subjects/{subject_id}")
def delete_subject(subject_id: int, student_id: int, db: Session = Depends(get_db)):
    """
    Fully delete a subject and everything tied to it: topics, mastery scores,
    learning history, sessions/questions/answers, topic relationships,
    cross-subject bridges, uploaded document records, and RAG chunks.
    """
    subject = db.query(Subject).filter(Subject.id == subject_id, Subject.student_id == student_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    topic_ids = [t.id for t in db.query(Topic).filter(Topic.subject_id == subject_id).all()]

    if topic_ids:
        db.query(CrossSubjectBridge).filter(
            (CrossSubjectBridge.topic_a_id.in_(topic_ids)) |
            (CrossSubjectBridge.topic_b_id.in_(topic_ids))
        ).delete(synchronize_session=False)

        db.query(TopicRelationship).filter(TopicRelationship.subject_id == subject_id).delete(synchronize_session=False)

        question_ids = [q.id for q in db.query(Question).filter(Question.topic_id.in_(topic_ids)).all()]
        if question_ids:
            db.query(Answer).filter(Answer.question_id.in_(question_ids)).delete(synchronize_session=False)
            db.query(Question).filter(Question.id.in_(question_ids)).delete(synchronize_session=False)

        db.query(LearningHistory).filter(LearningHistory.topic_id.in_(topic_ids)).delete(synchronize_session=False)
        db.query(MasteryScore).filter(MasteryScore.topic_id.in_(topic_ids)).delete(synchronize_session=False)

    db.query(SessionModel).filter(SessionModel.subject_id == subject_id).delete(synchronize_session=False)
    db.query(Topic).filter(Topic.subject_id == subject_id).delete(synchronize_session=False)
    db.query(UploadedDocument).filter(UploadedDocument.subject_id == subject_id).delete(synchronize_session=False)

    delete_subject_material(subject_id)  # wipes RAG chunks for this subject

    db.delete(subject)
    db.commit()

    return {"status": "deleted", "subject_id": subject_id}


@router.post("/sessions/preferences")
def update_session_preferences(request: UpdatePreferencesRequest, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.id == request.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    valid_aids = {"diagram", "plot", "image", "video"}
    session.visual_aid_preferences = [a for a in request.visual_aid_preferences if a in valid_aids]
    db.commit()
    return {"session_id": session.id, "visual_aid_preferences": session.visual_aid_preferences}

@router.get("/debug/gemini-models")
def debug_gemini_models():
    import os
    from google import genai as google_genai
    try:
        client = google_genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        models = list(client.models.list())
        return {"status": "ok", "models": [m.name for m in models]}
    except Exception as e:
        return {"status": "error", "error": repr(e)}