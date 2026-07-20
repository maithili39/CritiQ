import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useInterview } from "@/context/InterviewContext";
import { submitAnswer, completeSession } from "@/lib/api";
import Navbar from "@/components/Navbar";

function ScoreDisplay({ score }: { score: number }) {
  const color = score >= 7 ? "#16a34a" : score >= 5 ? "#f59e0b" : "#ef4444";
  const label = score >= 7 ? "Strong" : score >= 5 ? "Average" : "Needs work";
  return (
    <div className="flex flex-col items-center gap-1">
      <div
        className="text-[44px] font-bold leading-none tracking-tight"
        style={{ color, fontFamily: "'Outfit', sans-serif" }}
      >
        {score.toFixed(1)}
      </div>
      <div className="text-[11px] font-semibold uppercase tracking-wider" style={{ color }}>
        {label}
      </div>
      <div className="text-[11px]" style={{ color: "var(--cyan)" }}>out of 10</div>
    </div>
  );
}

export default function InterviewPage() {
  const { id: sessionId } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const {
    currentQuestion, questionsRemaining, isComplete,
    setCurrentQuestion, setQuestionsRemaining, setIsComplete,
    setLastScore, setLastFeedback,
  } = useInterview();

  const [answer, setAnswer]           = useState("");
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState("");
  const [showSources, setShowSources] = useState(false);
  const [feedback, setFeedback]       = useState<{
    score: number; rationale: string; strengths: string; gaps: string;
  } | null>(null);

  const [questionCount, setQuestionCount] = useState(currentQuestion?.order ?? 1);
  const maxQ = questionCount + questionsRemaining;
  const progress = Math.round(((questionCount - 1) / maxQ) * 100);

  useEffect(() => {
    if (!currentQuestion && !isComplete) navigate("/", { replace: true });
  }, [currentQuestion, isComplete, navigate]);

  const handleSubmit = async () => {
    if (!answer.trim() || !currentQuestion || !sessionId) return;
    setLoading(true);
    setError("");
    setFeedback(null);

    try {
      const res = await submitAnswer(sessionId, currentQuestion.id, answer);
      setFeedback({ score: res.score, rationale: res.rationale, strengths: res.strengths, gaps: res.gaps });
      setLastScore(res.score);
      setLastFeedback({ rationale: res.rationale, strengths: res.strengths, gaps: res.gaps });

      if (res.is_complete || !res.next_question) {
        setIsComplete(true);
        // Complete the session BEFORE navigating so the report exists when the
        // Report page fetches it. Previously navigate() fired while completeSession
        // was still in-flight, causing the report page to load with no data.
        try {
          await completeSession(sessionId);
        } catch (completeErr: unknown) {
          // If completeSession fails the report may still be generated server-side
          // (e.g., via the candidate background-task path). Navigate anyway; the
          // Report page re-fetches via getSession and will show the report if ready.
          console.error("completeSession failed:", completeErr);
        }
        navigate(`/interview/${sessionId}/report`);
      } else {
        setTimeout(() => {
          setCurrentQuestion(res.next_question!);
          setQuestionsRemaining(res.questions_remaining);
          setQuestionCount(res.next_question?.order ?? questionCount + 1);
          setAnswer("");
          setFeedback(null);
          setShowSources(false);
        }, 3200);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to submit answer.");
    } finally {
      setLoading(false);
    }
  };

  if (!currentQuestion && !isComplete) return null;

  return (
    <div className="page-stack" style={{ background: "var(--bg-soft)" }}>
      <Navbar />

      <div className="h-[4px]" style={{ background: "var(--border)" }}>
        <div className="h-full transition-all duration-700" style={{ width: `${progress}%`, background: "var(--brand)" }} />
      </div>

      <main className="interview-grid">

        {currentQuestion && !feedback && (
          <div className="card p-7 fade-up">
            <div className="flex items-center gap-2 mb-5 flex-wrap">
              {currentQuestion.topic && (
                <span className="badge badge-brand">{currentQuestion.topic}</span>
              )}
              {currentQuestion.difficulty && (
                <span className="badge capitalize">{currentQuestion.difficulty}</span>
              )}
              <span className="ml-auto text-[12px] font-medium muted">
                Question {questionCount}
              </span>
            </div>

            <p className="text-[20px] leading-relaxed font-semibold mb-5">
              {currentQuestion.text}
            </p>

            <button
              onClick={() => setShowSources(s => !s)}
              className="flex items-center gap-1.5 text-[12px] font-medium transition-colors"
              style={{ color: showSources ? "var(--brand)" : "var(--muted)" }}
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
              {showSources ? "Hide" : "Show"} reference context
            </button>

            {showSources && (
              <div
                className="mt-3 p-3 rounded-xl text-[12px] leading-relaxed fade-in whitespace-pre-wrap"
                style={{ background: "var(--brand-soft)", border: "1px solid var(--brand-line)", color: "var(--muted)" }}
              >
                <span className="font-semibold" style={{ color: "var(--ink)" }}>Reference:</span>{" "}
                {currentQuestion.source_context?.trim()
                  ? currentQuestion.source_context
                  : "No source context was retrieved for this question."}
              </div>
            )}
          </div>
        )}

        {!feedback && (
          <div className="flex flex-col gap-3 fade-up delay-1">
            <label className="field-label">Your answer</label>
            <textarea
              value={answer}
              onChange={e => setAnswer(e.target.value)}
              placeholder="Type your answer here..."
              rows={8}
              className="input px-4 py-3.5 text-[14px] resize-none"
              style={{ borderRadius: "12px", lineHeight: "1.7" }}
            />

            {error && (
              <div className="alert-error fade-in">{error}</div>
            )}

            <div className="flex items-center justify-between pt-1">
              <span className="text-[12px] muted">
                {answer.length > 0 ? `${answer.length} characters` : "Take your time to answer thoroughly"}
              </span>
              <button
                onClick={handleSubmit}
                disabled={loading || !answer.trim()}
                className="btn btn-primary text-[14px] px-6 py-2.5"
              >
                {loading ? (
                  <>
                    <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full spin" />
                    Evaluating...
                  </>
                ) : (
                  <>
                    Submit answer
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                    </svg>
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {feedback && (
          <div className="flex flex-col gap-4 fade-up">
            <div className="card p-6">
              <div className="flex items-start justify-between gap-6 mb-5">
                <div className="flex-1">
                  <div
                    className="inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest mb-3 px-2.5 py-1 rounded-full"
                    style={{ background: "var(--brand-soft)", color: "var(--brand)", border: "1px solid var(--brand-line)" }}
                  >
                    Answer evaluated
                  </div>
                  <p className="text-[14px] leading-relaxed muted">
                    {feedback.rationale}
                  </p>
                </div>
                <div className="flex-shrink-0">
                  <ScoreDisplay score={feedback.score} />
                </div>
              </div>

              {/* Score bar */}
              <div className="progress-track">
                <div
                  className="progress-fill"
                  style={{
                    width: `${(feedback.score / 10) * 100}%`,
                    background: feedback.score >= 7 ? "#16a34a" : feedback.score >= 5 ? "#f59e0b" : "#ef4444",
                  }}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {feedback.strengths && (
                <div
                  className="rounded-xl p-5"
                  style={{ background: "rgba(16,185,129,0.04)", border: "1px solid rgba(16,185,129,0.2)" }}
                >
                  <div className="text-[11px] font-bold uppercase tracking-wider mb-2" style={{ color: "#16a34a" }}>
                    Strengths
                  </div>
                  <div className="text-[13px] leading-relaxed" style={{ color: "var(--muted)" }}>
                    {feedback.strengths}
                  </div>
                </div>
              )}
              {feedback.gaps && (
                <div
                  className="rounded-xl p-5"
                  style={{ background: "rgba(239,68,68,0.04)", border: "1px solid rgba(239,68,68,0.2)" }}
                >
                  <div className="text-[11px] font-bold uppercase tracking-wider mb-2" style={{ color: "#ef4444" }}>
                    Areas to improve
                  </div>
                  <div className="text-[13px] leading-relaxed" style={{ color: "var(--muted)" }}>
                    {feedback.gaps}
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center justify-center gap-2.5 text-[13px] py-3" style={{ color: "var(--muted)" }}>
              <span
                className="w-3.5 h-3.5 border-2 rounded-full spin"
                style={{ borderColor: "var(--border)", borderTopColor: "#d97706" }}
              />
              {isComplete ? "Generating your report…" : "Moving to next question…"}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
