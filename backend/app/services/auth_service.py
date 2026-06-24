import bcrypt
from sqlalchemy.orm import Session
from app.models.database import Student


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))


def get_or_create_oauth_student(email: str, name: str, db: Session) -> Student:
    """
    Used by Google OAuth login. If the email already exists (e.g. they'd
    previously signed up with credentials), reuse that account — don't
    create a duplicate. Otherwise create a fresh OAuth-only student.
    """
    existing = db.query(Student).filter(Student.email == email).first()
    if existing:
        return existing

    student = Student(name=name, email=email, auth_provider="google", password_hash=None)
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


def register_credentials_student(name: str, email: str, password: str, db: Session) -> dict:
    existing = db.query(Student).filter(Student.email == email).first()
    if existing:
        return {"error": "An account with this email already exists."}

    student = Student(
        name=name, email=email,
        password_hash=hash_password(password),
        auth_provider="credentials"
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return {"student_id": student.id, "name": student.name, "email": student.email}


def authenticate_credentials_student(email: str, password: str, db: Session) -> dict:
    student = db.query(Student).filter(Student.email == email).first()
    if not student or not student.password_hash:
        return {"error": "Invalid email or password."}
    if not verify_password(password, student.password_hash):
        return {"error": "Invalid email or password."}
    return {"student_id": student.id, "name": student.name, "email": student.email}