import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getSession, recordOutcome, SessionSummary, IntegrityFlags, Outcome } from "@/lib/api";
import Navbar from "@/components/Navbar";
import SiteFooter from "@/components/SiteFooter";

const REC: Record<string, { label: string; color: string; bg: string; border: string }> = {
  strong_yes: { label: "Strong Hire",  color: "#16a34a", bg: "rgba(16,185,129,0.06)",  border: "rgba(16,185,129,0.2)" },
  yes:        { label: "Hire",         color: "#16a34a", bg: "rgba(16,185,129,0.06)",  border: "rgba(16,185,129,0.2)" },
  maybe:      { label: "Needs Review", color: "#f59e0b", bg: "rgba(245,158,11,0.06)",  border: "rgba(245,158,11,0.2)" },
  no:         { label: "No Hire",      color: "#ef4444", bg: "rgba(239,68,68,0.06)",   border: "rgba(239,68,68,0.2)"  },
};

const ROLE_LABELS: Record<string, string> = {
  ai_ml: "AI / ML Engineer",
  data_science: "Data Scientist",
};

const INTEGRITY_REASON_LABELS: Record<string, string> = {
  paste_detected:          "Paste detected",
  sub_15s_response:        "< 15s response time",
  high_score_fast_response:"High score + fast answer",
};

function scoreColor(s: number) {
  return s >= 7 ? "#16a34a" : s >= 5 ? "#f59e0b" : "#ef4444";
}

function formatMs(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60_000)}m ${Math.floor((ms % 60_000) / 1000)}s`;
}

function formatReasonLabel(reason: string): string {
  // Handle dynamic reasons like "tab_switched_2x"
  const match = reason.match(/^tab_switched_(\d+)x$/);
  if (match) return `Tab switched ${match[1]}×`;
  return INTEGRITY_REASON_LABELS[reason] ?? reason.replace(/_/g, " ");
}

function IntegrityBadge({ flags }: { flags: IntegrityFlags | null | undefined }) {
  if (!flags) return null;
  if (flags.suspicious) {
    return (
      <span
        className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full"
        style={{ background: "rgba(239,68,68,0.1)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.25)" }}
        title={flags.reasons.map(formatReasonLabel).join(", ")}
      >
        🚨 Flagged
      </span>
    );
  }
  return (
    <span
      className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full"
      style={{ background: "rgba(16,185,129,0.08)", color: "#16a34a", border: "1px solid rgba(16,185,129,0.2)" }}
    >
      ✅ Clean
    </span>
  );
}

export default function ReportPage() {
  const { id: sessionId } = useParams<{ id: string }>();
  const [session, setSession] = useState<SessionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [openQs, setOpenQs]   = useState<Set<string>>(new Set());
  const [savingOutcome, setSavingOutcome] = useState(false);

  const saveOutcome = async (outcome: Outcome) => {
    if (!sessionId) return;
    setSavingOutcome(true);
    try {
      await recordOutcome(sessionId, outcome);
      setSession((s) => (s ? { ...s, outcome, outcome_at: new Date().toISOString() } : s));
    } finally {
      setSavingOutcome(false);
    }
  };

  useEffect(() => {
    if (!sessionId) return;
    getSession(sessionId).then(setSession).finally(() => setLoading(false));
  }, [sessionId]);

  const toggleQ = (id: string) =>
    setOpenQs((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg-soft)" }}>
        <div className="flex flex-col items-center gap-3">
          <span className="w-8 h-8 border-2 rounded-full spin" style={{ borderColor: "var(--border)", borderTopColor: "#d97706" }} />
          <span className="text-[14px] muted">Loading report</span>
        </div>
      </div>
    );
  }

  if (!session?.report) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg-soft)" }}>
        <div className="text-[14px] muted">Report not available yet.</div>
      </div>
    );
  }

  const { report, parsed_resume, questions } = session;
  const rec = REC[report.recommendation] ?? REC.maybe;
  const topicEntries = Object.entries(report.topic_coverage || {});
  const score = report.overall_score ?? 0;

  // Integrity summary stats
  const answeredQs   = questions.filter((q) => q.answer);
  const flaggedCount = answeredQs.filter((q) => q.answer?.integrity_flags?.suspicious).length;
  const pasteCount   = answeredQs.filter((q) => q.answer?.paste_detected).length;
  const totalTabSwitches = answeredQs.reduce((acc, q) => acc + (q.answer?.tab_switch_count ?? 0), 0);
  const cameraCount  = answeredQs.filter((q) => q.answer?.has_camera_snapshot).length;
  const hasIntegrityData = answeredQs.some((q) => q.answer?.response_time_ms != null);

  return (
    <div className="page-stack" style={{ background: "var(--bg-soft)" }}>
      <Navbar />

      <main className="section" style={{ flex: 1 }}>
      <div className="shell shell-wide">

        <div className="mb-8 fade-up">
          <div className="text-[11px] font-bold uppercase tracking-widest mb-3" style={{ color: "var(--brand)" }}>
            Screening Report
          </div>
          <h1 className="text-[34px] font-bold tracking-tight mb-2">
            {session.candidate_name}
          </h1>
          <div className="flex items-center gap-2 text-[13px] flex-wrap muted">
            <span>{ROLE_LABELS[session.role] || session.role}</span>
            <span>•</span>
            <span className="capitalize">{parsed_resume?.experience_level} level</span>
            <span>•</span>
            <span>{new Date(session.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}</span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 flex flex-col gap-5 fade-up delay-1">

            {report.summary && (
              <div className="card p-6">
                <div className="text-[11px] font-bold uppercase tracking-widest mb-3" style={{ color: "var(--brand)" }}>
                  Assessment Summary
                </div>
                <p className="text-[14px] leading-relaxed muted">{report.summary}</p>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {report.strengths && (
                <div className="rounded-2xl p-5" style={{ background: "rgba(16,185,129,0.04)", border: "1px solid rgba(16,185,129,0.15)" }}>
                  <div className="text-[11px] font-bold uppercase tracking-widest mb-2" style={{ color: "#16a34a" }}>Strengths</div>
                  <p className="text-[13px] leading-relaxed" style={{ color: "var(--muted)" }}>{report.strengths}</p>
                </div>
              )}
              {report.gaps && (
                <div className="rounded-2xl p-5" style={{ background: "rgba(239,68,68,0.04)", border: "1px solid rgba(239,68,68,0.15)" }}>
                  <div className="text-[11px] font-bold uppercase tracking-widest mb-2" style={{ color: "#ef4444" }}>Areas to Improve</div>
                  <p className="text-[13px] leading-relaxed" style={{ color: "var(--muted)" }}>{report.gaps}</p>
                </div>
              )}
            </div>

            {topicEntries.length > 0 && (
              <div className="card p-6">
                <div className="text-[11px] font-bold uppercase tracking-widest mb-5" style={{ color: "var(--brand)" }}>
                  Topic Coverage
                </div>
                <div className="flex flex-col gap-4">
                  {topicEntries.map(([topic, val]) => {
                    const s = val as number;
                    const c = scoreColor(s);
                    return (
                      <div key={topic}>
                        <div className="flex justify-between items-center mb-1.5">
                          <span className="text-[13px] font-medium" style={{ color: "var(--ink)" }}>{topic}</span>
                          <span className="text-[13px] font-bold" style={{ color: c }}>{s.toFixed(1)}/10</span>
                        </div>
                        <div className="progress-track">
                          <div
                            className="progress-fill"
                            style={{ width: `${(s / 10) * 100}%`, background: c }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* ---- Integrity Summary (Audit Trail) ---- */}
            {hasIntegrityData && (
              <div className="card p-6">
                <div className="flex items-center justify-between mb-5">
                  <div className="text-[11px] font-bold uppercase tracking-widest" style={{ color: "var(--brand)" }}>
                    Integrity Audit
                  </div>
                  <span
                    className="text-[11px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full"
                    style={
                      flaggedCount > 0
                        ? { background: "rgba(239,68,68,0.08)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.2)" }
                        : { background: "rgba(16,185,129,0.08)", color: "#16a34a", border: "1px solid rgba(16,185,129,0.2)" }
                    }
                  >
                    {flaggedCount > 0 ? `⚠️ ${flaggedCount} flagged` : "✅ All clear"}
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {[
                    { label: "Flagged answers", value: `${flaggedCount} / ${answeredQs.length}`, warn: flaggedCount > 0 },
                    { label: "Paste events",    value: String(pasteCount),  warn: pasteCount > 0 },
                    { label: "Tab switches",    value: String(totalTabSwitches), warn: totalTabSwitches > 0 },
                    { label: "Camera captures", value: `${cameraCount} / ${answeredQs.length}`, warn: false },
                  ].map((stat) => (
                    <div
                      key={stat.label}
                      className="rounded-xl p-3.5 text-center"
                      style={{
                        background: stat.warn ? "rgba(239,68,68,0.04)" : "var(--surface-alt)",
                        border: `1px solid ${stat.warn ? "rgba(239,68,68,0.15)" : "var(--border)"}`,
                      }}
                    >
                      <div
                        className="text-[22px] font-bold leading-none mb-1"
                        style={{ color: stat.warn ? "#ef4444" : "var(--ink)", fontFamily: "'Outfit', sans-serif" }}
                      >
                        {stat.value}
                      </div>
                      <div className="text-[11px]" style={{ color: "var(--cyan)" }}>{stat.label}</div>
                    </div>
                  ))}
                </div>
                <p className="text-[11px] mt-4 leading-relaxed" style={{ color: "var(--cyan)" }}>
                  Integrity signals are collected automatically during the proctored interview session and stored for legal audit purposes. Flagged answers warrant human review before a hiring decision.
                </p>
              </div>
            )}

            {/* ---- Interview Transcript (Audit Trail) ---- */}
            <div className="card p-6">
              <div className="text-[11px] font-bold uppercase tracking-widest mb-5" style={{ color: "var(--brand)" }}>
                Interview Transcript
              </div>
              <div className="flex flex-col gap-2">
                {questions.map((q, i) => {
                  const isOpen = openQs.has(q.id);
                  const integrity = q.answer?.integrity_flags;
                  return (
                    <div
                      key={q.id}
                      className="rounded-xl overflow-hidden transition-all"
                      style={{ border: `1px solid ${isOpen ? "var(--border)" : "var(--surface-alt)"}` }}
                    >
                      <button
                        onClick={() => toggleQ(q.id)}
                        className="w-full flex items-center gap-3 px-5 py-4 text-left"
                        style={{ background: isOpen ? "var(--surface-alt)" : "#fff" }}
                      >
                        <span className="text-[11px] font-bold w-6 flex-shrink-0" style={{ color: "#d97706" }}>
                          Q{i + 1}
                        </span>
                        {q.topic && (
                          <span className="badge badge-brand flex-shrink-0 hidden sm:inline-flex">{q.topic}</span>
                        )}
                        <p className="text-[13px] font-medium flex-1 text-left line-clamp-1" style={{ color: "var(--ink)" }}>
                          {q.text}
                        </p>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          {integrity != null && <IntegrityBadge flags={integrity} />}
                          {q.answer?.score != null && (
                            <span className="text-[12px] font-bold" style={{ color: scoreColor(q.answer.score) }}>
                              {q.answer.score.toFixed(1)}/10
                            </span>
                          )}
                        </div>
                        <svg
                          className="w-4 h-4 flex-shrink-0 transition-transform duration-200"
                          style={{ color: "var(--cyan)", transform: isOpen ? "rotate(180deg)" : "none" }}
                          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                        </svg>
                      </button>

                      {isOpen && (
                        <div className="px-5 pb-5 fade-in" style={{ borderTop: "1px solid var(--surface-alt)" }}>
                          <p className="text-[14px] font-medium pt-4 mb-4 leading-relaxed" style={{ color: "var(--ink)" }}>
                            {q.text}
                          </p>
                          {q.answer ? (
                            <div className="flex flex-col gap-3">
                              <div className="rounded-xl p-4" style={{ background: "var(--surface-alt)", border: "1px solid var(--border)" }}>
                                <div className="flex justify-between items-center mb-2">
                                  <span className="text-[11px] font-bold uppercase tracking-wide" style={{ color: "var(--cyan)" }}>
                                    Answer
                                  </span>
                                  {q.answer.score != null && (
                                    <span className="text-[12px] font-bold" style={{ color: scoreColor(q.answer.score) }}>
                                      {q.answer.score.toFixed(1)}/10
                                    </span>
                                  )}
                                </div>
                                <p className="text-[13px] leading-relaxed" style={{ color: "var(--muted)" }}>{q.answer.text}</p>
                                {q.answer.rationale && (
                                  <p className="text-[12px] mt-3 leading-relaxed" style={{ color: "#d97706" }}>
                                    <span className="font-semibold">Feedback:</span> {q.answer.rationale}
                                  </p>
                                )}

                                {/* Per-dimension rubric breakdown (how the score was built) */}
                                {q.answer.dimension_scores && Object.keys(q.answer.dimension_scores).length > 0 && (
                                  <div className="mt-3 flex flex-wrap gap-1.5">
                                    {Object.entries(q.answer.dimension_scores).map(([dim, val]) => (
                                      <span
                                        key={dim}
                                        className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                                        style={{ background: "var(--surface-alt)", color: "var(--muted)" }}
                                        title={`${dim}: ${(val as number).toFixed(1)}/10`}
                                      >
                                        {dim.replace(/_/g, " ")} {(val as number).toFixed(1)}
                                      </span>
                                    ))}
                                    {q.answer.needs_human_review && (
                                      <span
                                        className="text-[10px] font-bold px-2 py-0.5 rounded-full"
                                        style={{ background: "rgba(245,158,11,0.12)", color: "#b45309" }}
                                        title={`The two scoring passes disagreed by ${q.answer.score_variance ?? "?"} points`}
                                      >
                                        ⚖ Score uncertain — review
                                      </span>
                                    )}
                                  </div>
                                )}
                              </div>

                              {/* ---- RAG traceability: what this question was grounded in ---- */}
                              {q.source_context && (
                                <details className="rounded-xl" style={{ background: "var(--brand-soft)", border: "1px solid var(--brand-line)" }}>
                                  <summary className="cursor-pointer px-4 py-2.5 text-[11px] font-bold uppercase tracking-wide" style={{ color: "#d97706" }}>
                                    📎 Grounded in knowledge base
                                  </summary>
                                  <div className="px-4 pb-4">
                                    <p className="text-[11px] mb-2" style={{ color: "var(--muted)" }}>
                                      This question was generated from the following retrieved source material — not free-form by the model:
                                    </p>
                                    <pre className="text-[11px] leading-relaxed whitespace-pre-wrap" style={{ color: "var(--muted)", fontFamily: "inherit" }}>
                                      {q.source_context}
                                    </pre>
                                  </div>
                                </details>
                              )}

                              {/* Audit meta row */}
                              <div
                                className="rounded-xl px-4 py-3 flex flex-wrap gap-x-5 gap-y-1.5 text-[11px]"
                                style={{ background: "var(--surface-alt)", color: "var(--muted)" }}
                              >
                                {q.answer.submitted_at && (
                                  <span>
                                    🕐 Submitted {new Date(q.answer.submitted_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                                  </span>
                                )}
                                {q.answer.response_time_ms != null && (
                                  <span>⏱ Response time: {formatMs(q.answer.response_time_ms)}</span>
                                )}
                                <span>📋 Paste: {q.answer.paste_detected ? "⚠️ Detected" : "None"}</span>
                                <span>🔍 Tab switches: {q.answer.tab_switch_count ?? 0}</span>
                                <span>📷 Camera: {q.answer.has_camera_snapshot ? "Captured" : "No snapshot"}</span>
                                {integrity?.suspicious && integrity.reasons.length > 0 && (
                                  <span style={{ color: "#ef4444" }}>
                                    🚨 Flags: {integrity.reasons.map(formatReasonLabel).join(", ")}
                                  </span>
                                )}
                              </div>
                            </div>
                          ) : (
                            <span className="text-[13px] italic" style={{ color: "var(--cyan)" }}>No answer submitted</span>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-4 fade-up delay-2">
            <div className="card p-6 text-center">
              <div className="text-[11px] font-bold uppercase tracking-widest mb-4" style={{ color: "var(--cyan)" }}>
                Overall Score
              </div>
              <div
                className="text-[60px] font-bold leading-none mb-1 tracking-tight"
                style={{ color: scoreColor(score), fontFamily: "'Outfit', sans-serif" }}
              >
                {score.toFixed(1)}
              </div>
              <div className="text-[12px] mb-5" style={{ color: "var(--cyan)" }}>out of 10</div>
              <div className="progress-track">
                <div
                  className="progress-fill"
                  style={{ width: `${(score / 10) * 100}%`, background: scoreColor(score) }}
                />
              </div>
            </div>

            <div
              className="rounded-2xl p-5 text-center"
              style={{ background: rec.bg, border: `1px solid ${rec.border}` }}
            >
              <div className="text-[11px] font-bold uppercase tracking-widest mb-3" style={{ color: "var(--cyan)" }}>
                Recommendation
              </div>
              <div className="flex items-center justify-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full" style={{ background: rec.color }} />
                <span className="text-[18px] font-bold" style={{ color: rec.color }}>{rec.label}</span>
              </div>
            </div>

            {/* ---- Fused integrity confidence (session-level) ---- */}
            {report.integrity_summary && report.integrity_summary.answers_analyzed > 0 && (() => {
              const isum = report.integrity_summary!;
              const c = isum.risk_level === "low" ? "#16a34a" : isum.risk_level === "medium" ? "#f59e0b" : "#ef4444";
              return (
                <div className="card p-5">
                  <div className="text-[11px] font-bold uppercase tracking-widest mb-3" style={{ color: "var(--cyan)" }}>
                    Integrity Confidence
                  </div>
                  <div className="flex items-end gap-2 mb-2">
                    <span className="text-[40px] font-bold leading-none" style={{ color: c, fontFamily: "'Outfit', sans-serif" }}>
                      {isum.confidence}
                    </span>
                    <span className="text-[12px] mb-1" style={{ color: "var(--cyan)" }}>/ 100</span>
                    <span className="ml-auto mb-1 text-[11px] font-bold uppercase tracking-wide" style={{ color: c }}>
                      {isum.risk_level} risk
                    </span>
                  </div>
                  <div className="progress-track mb-3">
                    <div className="progress-fill" style={{ width: `${isum.confidence}%`, background: c }} />
                  </div>
                  {isum.signals.length > 0 ? (
                    <ul className="flex flex-col gap-1">
                      {isum.signals.map((sig) => (
                        <li key={sig.code} className="text-[11px] flex justify-between gap-2" style={{ color: "var(--muted)" }}>
                          <span>{sig.detail}</span>
                          <span className="font-semibold" style={{ color: c }}>−{sig.weight}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-[11px]" style={{ color: "var(--cyan)" }}>No integrity signals fired across the session.</p>
                  )}
                </div>
              );
            })()}

            {/* ---- Recruiter outcome feedback (ground truth for calibration) ---- */}
            <div className="card p-5">
              <div className="text-[11px] font-bold uppercase tracking-widest mb-1" style={{ color: "var(--cyan)" }}>
                Actual Hiring Outcome
              </div>
              <p className="text-[11px] mb-3 leading-relaxed" style={{ color: "var(--cyan)" }}>
                Record what really happened — this calibrates the AI's scores against real hires over time.
              </p>
              <div className="grid grid-cols-2 gap-2">
                {([
                  { key: "hired_strong", label: "Strong hire", c: "#16a34a" },
                  { key: "hired", label: "Hired", c: "#16a34a" },
                  { key: "rejected", label: "Rejected", c: "#ef4444" },
                  { key: "no_show", label: "No show", c: "var(--cyan)" },
                ] as { key: Outcome; label: string; c: string }[]).map((o) => {
                  const active = session.outcome === o.key;
                  return (
                    <button
                      key={o.key}
                      disabled={savingOutcome}
                      onClick={() => saveOutcome(o.key)}
                      className="text-[12px] font-semibold py-2 rounded-lg transition-all"
                      style={{
                        background: active ? o.c : "var(--surface-alt)",
                        color: active ? "#fff" : "var(--muted)",
                        border: `1px solid ${active ? o.c : "var(--border)"}`,
                        opacity: savingOutcome ? 0.6 : 1,
                      }}
                    >
                      {o.label}
                    </button>
                  );
                })}
              </div>
              {session.outcome_at && (
                <p className="text-[10px] mt-2" style={{ color: "var(--cyan)" }}>
                  Recorded {new Date(session.outcome_at).toLocaleDateString("en-GB")}
                </p>
              )}
            </div>

            <div className="card p-5">
              <div className="text-[11px] font-bold uppercase tracking-widest mb-4" style={{ color: "var(--cyan)" }}>
                Candidate Details
              </div>
              <div className="flex flex-col gap-3">
                {[
                  { label: "Role",      value: ROLE_LABELS[session.role] || session.role },
                  { label: "Level",     value: parsed_resume?.experience_level || "—", cap: true },
                  { label: "Questions", value: `${questions.length} asked` },
                  { label: "Answered",  value: `${questions.filter(q => q.answer).length} of ${questions.length}` },
                ].map(item => (
                  <div key={item.label} className="flex justify-between items-center">
                    <span className="text-[12px]" style={{ color: "var(--cyan)" }}>{item.label}</span>
                    <span className={`text-[12px] font-semibold ${item.cap ? "capitalize" : ""}`} style={{ color: "var(--ink)" }}>
                      {item.value}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Compact integrity summary in sidebar */}
            {hasIntegrityData && (
              <div className="card p-5">
                <div className="text-[11px] font-bold uppercase tracking-widest mb-3" style={{ color: "var(--cyan)" }}>
                  Integrity
                </div>
                <div className="flex flex-col gap-2">
                  <div className="flex justify-between items-center">
                    <span className="text-[12px]" style={{ color: "var(--cyan)" }}>Flagged answers</span>
                    <span className="text-[12px] font-semibold" style={{ color: flaggedCount > 0 ? "#ef4444" : "#16a34a" }}>
                      {flaggedCount} / {answeredQs.length}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-[12px]" style={{ color: "var(--cyan)" }}>Paste events</span>
                    <span className="text-[12px] font-semibold" style={{ color: pasteCount > 0 ? "#ef4444" : "#16a34a" }}>
                      {pasteCount}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-[12px]" style={{ color: "var(--cyan)" }}>Tab switches</span>
                    <span className="text-[12px] font-semibold" style={{ color: totalTabSwitches > 0 ? "#f59e0b" : "#16a34a" }}>
                      {totalTabSwitches}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {parsed_resume?.skills?.length > 0 && (
              <div className="card p-5">
                <div className="text-[11px] font-bold uppercase tracking-widest mb-4" style={{ color: "var(--cyan)" }}>
                  Detected Skills
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {parsed_resume.skills.slice(0, 12).map(sk => (
                    <span key={sk} className="badge badge-brand text-[11px] px-2 py-0.5">{sk}</span>
                  ))}
                </div>
              </div>
            )}

            <Link to="/interview/setup" className="btn btn-primary w-full text-[14px] py-3">
              Screen another candidate
            </Link>
          </div>
        </div>
      </div>
      </main>

      <SiteFooter />
    </div>
  );
}
