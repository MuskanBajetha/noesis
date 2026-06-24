from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.tutor import router as tutor_router
from app.models.database import init_db
import os

app = FastAPI(
    title="Socratic Tutor API",
    description="AI-powered adaptive Socratic tutoring system",
    version="1.0.0"
)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()

app.include_router(tutor_router, prefix="/api", tags=["Tutor"])

@app.get("/")
def root():
    return {"message": "Socratic Tutor API is running! 🚀"}