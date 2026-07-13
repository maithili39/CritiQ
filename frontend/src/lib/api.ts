// window.__API_BASE__ is injected at container start (docker-entrypoint.sh writes
// /config.js from the API_BASE env var) so the same built image can be deployed to
// different environments without a rebuild. VITE_API_URL is the build-time fallback
// for `vite dev`/`vite build` run outside Docker.
declare global {
  interface Window { __API_BASE__?: string }
}
const API_BASE = window.__API_BASE__ || import.meta.env.VITE_API_URL || "http://localhost:8000/api";
const TOKEN_KEY = "screening_access_token";

export function getAuthToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setAuthToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearAuthToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);
  const token = getAuthToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export async function register(email: string, password: string) {
  const result = await request<{ access_token: string; email: string }>("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  setAuthToken(result.access_token);
  return result;
}

export async function login(email: string, password: string) {
  const result = await request<{ access_token: string; email: string }>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  setAuthToken(result.access_token);
  return result;
}

export async function getMe() {
  return request<{ id: string; email: string }>("/auth/me");
}

export async function listSessions() {
  return request<{ sessions: SessionListItem[] }>("/sessions");
}

export async function createSession(formData: FormData) {
  return request<{
    session_id: string;
    status: string;
    parsed_resume: Record<string, unknown>;
    invite_url: string;
    message: string;
  }>("/sessions", { method: "POST", body: formData });
}

export async function sendInvite(sessionId: string) {
  return request<{ message: string; invite_url: string }>(
    `/sessions/${sessionId}/invite/send`,
    { method: "POST" }
  );
}

export async function startSession(sessionId: string) {
  return request<{
    session_id: string;
    status: string;
    question: Question;
    questions_remaining: number;
  }>(`/sessions/${sessionId}/start`, { method: "POST" });
}

export async function submitAnswer(
  sessionId: string,
  questionId: string,
  answerText: string
) {
  return request<{
    answer_id: string;
    score: number;
    rationale: string;
    strengths: string;
    gaps: string;
    next_question: Question | null;
    is_complete: boolean;
    questions_remaining: number;
  }>(`/sessions/${sessionId}/answers?question_id=${questionId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer_text: answerText }),
  });
}

export async function completeSession(sessionId: string) {
  return request<{ session_id: string; report: Report }>(
    `/sessions/${sessionId}/complete`,
    { method: "POST" }
  );
}

export async function getSession(sessionId: string) {
  return request<SessionSummary>(`/sessions/${sessionId}`);
}

export interface Question {
  id: string;
  text: string;
  topic: string | null;
  difficulty: string | null;
  order: number;
  source_context?: string | null;
  answer?: AnswerData | null;
}

export interface AnswerData {
  id: string;
  text: string;
  score: number | null;
  rationale: string;
  strengths: string;
  gaps: string;
}

export interface Report {
  summary: string;
  overall_score: number;
  topic_coverage: Record<string, number>;
  strengths: string;
  gaps: string;
  recommendation: string;
}

export interface SessionListItem {
  id: string;
  candidate_name: string;
  role: string;
  status: string;
  overall_score: number | null;
  created_at: string;
  completed_at: string | null;
}

export interface SessionSummary {
  id: string;
  candidate_name: string;
  candidate_email: string | null;
  role: string;
  status: string;
  current_question_index: number;
  max_questions: number;
  parsed_resume: {
    skills: string[];
    technologies: string[];
    experience_level: string;
    domains: string[];
    summary: string;
  };
  questions: (Question & { answer: AnswerData | null })[];
  report: Report | null;
  invite_url: string;
  created_at: string;
  completed_at: string | null;
}

// --- Candidate-facing API (token-authenticated invite link, no account needed) ---

export interface CandidateQuestion {
  id: string;
  text: string;
  topic: string | null;
  difficulty: string | null;
  order: number;
}

async function candidateRequest<T>(sessionId: string, token: string, path: string, options?: RequestInit): Promise<T> {
  const sep = path.includes("?") ? "&" : "?";
  const res = await fetch(`${API_BASE}/candidate/sessions/${sessionId}${path}${sep}token=${encodeURIComponent(token)}`, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export async function getCandidateSession(sessionId: string, token: string) {
  return candidateRequest<{
    session_id: string;
    candidate_name: string;
    role: string;
    status: string;
    question: CandidateQuestion | null;
    questions_answered: number;
    max_questions: number;
  }>(sessionId, token, "");
}

export async function startCandidateSession(sessionId: string, token: string) {
  return candidateRequest<{ session_id: string; status: string; question: CandidateQuestion }>(
    sessionId, token, "/start", { method: "POST" }
  );
}

export async function submitCandidateAnswer(sessionId: string, token: string, questionId: string, answerText: string) {
  return candidateRequest<{ next_question: CandidateQuestion | null; is_complete: boolean }>(
    sessionId, token, `/answers?question_id=${encodeURIComponent(questionId)}`,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ answer_text: answerText }) }
  );
}

export async function completeCandidateSession(sessionId: string, token: string) {
  return candidateRequest<{ message: string }>(sessionId, token, "/complete", { method: "POST" });
}
