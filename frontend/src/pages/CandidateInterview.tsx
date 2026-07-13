import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import {
  getCandidateSession,
  startCandidateSession,
  submitCandidateAnswer,
  CandidateQuestion,
} from "@/lib/api";
import Navbar from "@/components/Navbar";

const ROLE_LABELS: Record<string, string> = {
  ai_ml: "AI / ML Engineer",
  data_science: "Data Scientist",
};

const POLL_INTERVAL_MS = 1500;

type Stage = "loading" | "intro" | "active" | "submitting" | "grading" | "done" | "error";

export default function CandidateInterview() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [stage, setStage] = useState<Stage>("loading");
  const [error, setError] = useState("");
  const [candidateName, setCandidateName] = useState("");
  const [role, setRole] = useState("");
  const [maxQuestions, setMaxQuestions] = useState(0);
  const [question, setQuestion] = useState<CandidateQuestion | null>(null);
  const [answer, setAnswer] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  const pollUntilDone = useCallback((submittedQuestionOrder: number) => {
    if (!sessionId) return;
    pollRef.current = setInterval(async () => {
      try {
        const s = await getCandidateSession(sessionId, token);
        if (s.is_processing) return;

        if (pollRef.current) clearInterval(pollRef.current);

        if (s.processing_error) {
          setError("Something went wrong grading your answer. Please contact support — your answer was saved.");
          setStage("error");
          return;
        }
        if (s.status === "completed") {
          setStage("done");
          return;
        }
        if (s.question && s.question.order > submittedQuestionOrder) {
          setQuestion(s.question);
          setAnswer("");
          setStage("active");
          return;
        }
        // Shouldn't happen, but don't leave the candidate stuck on a spinner.
        setStage("active");
      } catch (err: unknown) {
        if (pollRef.current) clearInterval(pollRef.current);
        setError(err instanceof Error ? err.message : "Lost connection while waiting for your result.");
        setStage("error");
      }
    }, POLL_INTERVAL_MS);
  }, [sessionId, token]);

  const loadSession = useCallback(async () => {
    if (!sessionId || !token) {
      setError("This invite link is missing or invalid.");
      setStage("error");
      return;
    }
    try {
      const s = await getCandidateSession(sessionId, token);
      setCandidateName(s.candidate_name);
      setRole(s.role);
      setMaxQuestions(s.max_questions);
      if (s.status === "completed") {
        setStage("done");
      } else if (s.status === "active" && s.question) {
        setQuestion(s.question);
        if (s.is_processing) {
          // Candidate refreshed/reopened the link mid-grade — resume polling
          // instead of showing the already-answered question as if unanswered.
          setStage("grading");
          pollUntilDone(s.question.order);
        } else {
          setStage("active");
        }
      } else {
        setStage("intro");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "This invite link is no longer valid.");
      setStage("error");
    }
  }, [sessionId, token, pollUntilDone]);

  useEffect(() => { loadSession(); }, [loadSession]);

  const handleStart = async () => {
    if (!sessionId) return;
    setStage("loading");
    try {
      const started = await startCandidateSession(sessionId, token);
      setQuestion(started.question);
      setStage("active");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start the interview.");
      setStage("error");
    }
  };

  const handleSubmit = async () => {
    if (!sessionId || !question || !answer.trim()) return;
    setStage("submitting");
    setError("");

    try {
      // Returns immediately - scoring + next-question generation happen in a
      // background task on the server, so we poll rather than await the result.
      await submitCandidateAnswer(sessionId, token, question.id, answer);
      setStage("grading");
      pollUntilDone(question.order);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to submit your answer.");
      setStage("active");
    }
  };

  if (stage === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg-soft)" }}>
        <span className="w-8 h-8 border-2 rounded-full spin" style={{ borderColor: "#e5e7eb", borderTopColor: "#ea0954" }} />
      </div>
    );
  }

  if (stage === "error") {
    return (
      <div className="page-stack" style={{ background: "var(--bg-soft)" }}>
        <Navbar />
        <main className="section flex-1 flex items-center justify-center">
          <div className="card p-8 max-w-md text-center">
            <h1 className="text-[22px] font-bold mb-3">Something went wrong</h1>
            <p className="muted text-[14px]">{error}</p>
          </div>
        </main>
      </div>
    );
  }

  if (stage === "intro") {
    return (
      <div className="page-stack" style={{ background: "var(--bg-soft)" }}>
        <Navbar />
        <main className="section flex-1 flex items-center justify-center">
          <div className="card p-8 max-w-lg text-center fade-up">
            <div className="eyebrow mb-3">You've been invited</div>
            <h1 className="text-[28px] font-bold tracking-tight mb-3">Hi {candidateName}</h1>
            <p className="muted text-[15px] leading-relaxed mb-6">
              You're being screened for a <strong>{ROLE_LABELS[role] || role}</strong> role.
              This is a self-paced technical interview — you'll answer {maxQuestions} questions
              generated from your resume, one at a time. Take your time on each answer.
            </p>
            <button onClick={handleStart} className="btn btn-primary px-8 py-3">
              Start the interview
            </button>
          </div>
        </main>
      </div>
    );
  }

  if (stage === "done") {
    return (
      <div className="page-stack" style={{ background: "var(--bg-soft)" }}>
        <Navbar />
        <main className="section flex-1 flex items-center justify-center">
          <div className="card p-8 max-w-md text-center fade-up">
            <div className="w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-5" style={{ background: "rgba(16,185,129,0.1)" }}>
              <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="#10b981" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h1 className="text-[22px] font-bold mb-3">All done, thank you</h1>
            <p className="muted text-[14px] leading-relaxed">
              Your responses have been submitted for review. The hiring team will follow up
              with next steps — there's nothing further to do here.
            </p>
          </div>
        </main>
      </div>
    );
  }

  // active / submitting / grading
  return (
    <div className="page-stack" style={{ background: "var(--bg-soft)" }}>
      <Navbar />
      <main className="interview-grid">
        {question && (
          <div className="card p-7 fade-up">
            <div className="flex items-center gap-2 mb-5 flex-wrap">
              {question.topic && <span className="badge badge-brand">{question.topic}</span>}
              <span className="ml-auto text-[12px] font-medium muted">
                Question {question.order} of {maxQuestions}
              </span>
            </div>
            <p className="text-[20px] leading-relaxed font-semibold">{question.text}</p>
          </div>
        )}

        <div className="flex flex-col gap-3 fade-up delay-1">
          <label className="field-label">Your answer</label>
          <textarea
            value={answer}
            onChange={e => setAnswer(e.target.value)}
            placeholder="Type your answer here..."
            rows={8}
            disabled={stage !== "active"}
            className="input px-4 py-3.5 text-[14px] resize-none"
            style={{ borderRadius: "12px", lineHeight: "1.7" }}
          />

          {error && <div className="alert-error fade-in">{error}</div>}

          <div className="flex items-center justify-between pt-1">
            <span className="text-[12px] muted">
              {stage === "grading"
                ? "Grading your answer and preparing the next question…"
                : answer.length > 0 ? `${answer.length} characters` : "Take your time to answer thoroughly"}
            </span>
            <button
              onClick={handleSubmit}
              disabled={stage !== "active" || !answer.trim()}
              className="btn btn-primary text-[14px] px-6 py-2.5"
            >
              {stage === "submitting" || stage === "grading" ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full spin" />
                  {stage === "grading" ? "Grading..." : "Submitting..."}
                </>
              ) : "Submit answer"}
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
