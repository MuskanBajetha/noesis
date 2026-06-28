# Noesis — Learn by Discovering

> A Socratic AI tutor that never directly gives answers — it helps you *discover* them.

**Live demo:** [noesis-frontend-vh1q.onrender.com](https://noesis-frontend-vh1q.onrender.com)

**Demo video:** 
[Watch Demo](https://drive.google.com/file/d/1YW6oDMYRB6njY6FNBLXA51JDJvowuCZ2/view?usp=sharing)

---

## What it is

Noesis is an AI-powered tutoring system built on **Socratic learning principles**. Instead of answering questions, it guides students toward the answer through progressively deeper questioning — grounded in their own uploaded material or a set of prebuilt domains — while tracking what they actually understand, not just what they got right once.

## Core features

- **RAG-grounded tutoring** — Upload a PDF, get a Socratic session built on *your* material, with topics auto-extracted by an LLM
- **Staged pedagogy** — Learning progresses through Recognition → Mastery; questions target the student's actual stage without repetition or skipping
- **Attempt-aware hints** — Wrong answers trigger progressively stronger guidance, from light hints to full explanations with optional visual or external support
- **Multimodal explanations** — Rendered LaTeX, Mermaid diagrams, interactive Plotly graphs, Wikimedia images, YouTube references, and live web citations — all gated by explicit user preference, not LLM guesswork
- **Misconception detection** — Identifies specific reasoning errors instead of generic *incorrect* feedback
- **Gibberish/low-effort filtering** — Rule-based intent classification rejects junk answers *before* they hit the LLM, so mastery can't be gamed and tokens aren't wasted
- **Knowledge graphs** — Per-subject concept maps plus a global cross-subject graph that surfaces "knowledge bridges" between unrelated domains
- **Challenge mode** — Questions scale to mastery; Challenge mode mixes topics across a whole subject, prioritizing weak areas first

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js, TypeScript, Tailwind, shadcn/ui, D3, Recharts, Plotly |
| Backend | FastAPI, SQLAlchemy, PostgreSQL |
| AI | Groq (Llama 3.3) for reasoning, Gemini for embeddings, ChromaDB for vector search |
| Grounding | Tavily (web search), YouTube Data API, Wikimedia Commons |
| Auth | NextAuth.js v5, bcrypt |
| Hosting | Render (frontend + backend), Neon (Postgres) |

## Architecture
<img width="1440" height="1520" alt="image" src="https://github.com/user-attachments/assets/60a99e46-47cc-4955-95b7-e38f9150618f" />

## Running locally

**Requirements:** Python 3.11+, Node 18+, PostgreSQL, and free API keys for Groq, Gemini, Tavily, YouTube Data API, and Google OAuth.

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows — use `source venv/bin/activate` on Mac/Linux
pip install -r requirements.txt
```

Create `backend/.env`:
```env
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/noesis
GROQ_API_KEY=
GEMINI_API_KEY=
TAVILY_API_KEY=
YOUTUBE_API_KEY=
APP_ENV=
SECRET_KEY=
```

```bash
uvicorn main:app --reload
```
Backend runs at `http://127.0.0.1:8000` — tables and prebuilt domains seed automatically on first startup.

### Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:
```env
AUTH_SECRET=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api
```

```bash
npm run dev
```
Frontend runs at `http://localhost:3000`.
