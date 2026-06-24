import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

export const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

// Students
export const createStudent = (name: string, email: string) =>
  api.post("/students", { name, email });

// Questions
export const generateQuestion = (topic: string, student_id: number, session_id?: number) =>
  api.post("/generate-question", { topic, student_id, session_id });

// Evaluate
export const evaluateAnswer = (question_id: number, student_response: string, student_id: number) =>
  api.post("/evaluate-answer", { question_id, student_response, student_id });

// Progress
export const getStudentProgress = (student_id: number) =>
  api.get(`/student-progress/${student_id}`);