import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getSession, SessionSummary } from "@/lib/api";
import Navbar from "@/components/Navbar";
import SiteFooter from "@/components/SiteFooter";

const REC: Record<string, { label: string; color: string; bg: string; border: string }> = {
  strong_yes: { label: "Strong Hire",  color: "#10b981", bg: "rgba(16,185,129,0.06)",  border: "rgba(16,185,129,0.2)" },
  yes:        { label: "Hire",         color: "#10b981", bg: "rgba(16,185,129,0.06)",  border: "rgba(16,185,129,0.2)" },
  maybe:      { label: "Needs Review", color: "#f59e0b", bg: "rgba(245,158,11,0.06)",  border: "rgba(245,158,11,0.2)" },
  no:         { label: "No Hire",      color: "#ef4444", bg: "rgba(239,68,68,0.06)",   border: "rgba(239,68,68,0.2)"  },
};

const ROLE_LABELS: Record<string, string> = {
  ai_ml: "AI / ML Engineer",
  data_science: "Data Scientist",
};

function scoreColor(s: number) {
  return s >= 7 ? "#10b981" : s >= 5 ? "#f59e0b" : "#ef4444";
}

export default function ReportPage() {
  const { id: sessionId } = useParams<{ id: string }>();
  const [session, setSession] = useState<SessionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [openQs, setOpenQs]   = useState<Set<string>>(new Set());

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
          <span className="w-8 h-8 border-2 rounded-full spin" style={{ borderColor: "#e5e7eb", borderTopColor: "#ea0954" }} />
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
                  <div className="text-[11px] font-bold uppercase tracking-widest mb-2" style={{ color: "#10b981" }}>Strengths</div>
                  <p className="text-[13px] leading-relaxed" style={{ color: "#374151" }}>{report.strengths}</p>
                </div>
              )}
              {report.gaps && (
                <div className="rounded-2xl p-5" style={{ background: "rgba(239,68,68,0.04)", border: "1px solid rgba(239,68,68,0.15)" }}>
                  <div className="text-[11px] font-bold uppercase tracking-widest mb-2" style={{ color: "#ef4444" }}>Areas to Improve</div>
                  <p className="text-[13px] leading-relaxed" style={{ color: "#374151" }}>{report.gaps}</p>
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
                          <span className="text-[13px] font-medium" style={{ color: "#0b0c15" }}>{topic}</span>
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

            <div className="card p-6">
              <div className="text-[11px] font-bold uppercase tracking-widest mb-5" style={{ color: "var(--brand)" }}>
                Interview Transcript
              </div>
              <div className="flex flex-col gap-2">
                {questions.map((q, i) => {
                  const isOpen = openQs.has(q.id);
                  return (
                    <div
                      key={q.id}
                      className="rounded-xl overflow-hidden transition-all"
                      style={{ border: `1px solid ${isOpen ? "#e5e7eb" : "#f3f4f6"}` }}
                    >
                      <button
                        onClick={() => toggleQ(q.id)}
                        className="w-full flex items-center gap-3 px-5 py-4 text-left"
                        style={{ background: isOpen ? "#f9fafb" : "#fff" }}
                      >
                        <span className="text-[11px] font-bold w-6 flex-shrink-0" style={{ color: "#ea0954" }}>
                          Q{i + 1}
                        </span>
                        {q.topic && (
                          <span className="badge badge-brand flex-shrink-0 hidden sm:inline-flex">{q.topic}</span>
                        )}
                        <p className="text-[13px] font-medium flex-1 text-left line-clamp-1" style={{ color: "#0b0c15" }}>
                          {q.text}
                        </p>
                        {q.answer?.score != null && (
                          <span className="text-[12px] font-bold flex-shrink-0" style={{ color: scoreColor(q.answer.score) }}>
                            {q.answer.score.toFixed(1)}/10
                          </span>
                        )}
                        <svg
                          className="w-4 h-4 flex-shrink-0 transition-transform duration-200"
                          style={{ color: "#9ca3af", transform: isOpen ? "rotate(180deg)" : "none" }}
                          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                        </svg>
                      </button>

                      {isOpen && (
                        <div className="px-5 pb-5 fade-in" style={{ borderTop: "1px solid #f3f4f6" }}>
                          <p className="text-[14px] font-medium pt-4 mb-4 leading-relaxed" style={{ color: "#0b0c15" }}>
                            {q.text}
                          </p>
                          {q.answer ? (
                            <div className="rounded-xl p-4" style={{ background: "#f9fafb", border: "1px solid #e5e7eb" }}>
                              <div className="flex justify-between items-center mb-2">
                                <span className="text-[11px] font-bold uppercase tracking-wide" style={{ color: "#9ca3af" }}>
                                  Answer
                                </span>
                                {q.answer.score != null && (
                                  <span className="text-[12px] font-bold" style={{ color: scoreColor(q.answer.score) }}>
                                    {q.answer.score.toFixed(1)}/10
                                  </span>
                                )}
                              </div>
                              <p className="text-[13px] leading-relaxed" style={{ color: "#4b5563" }}>{q.answer.text}</p>
                              {q.answer.rationale && (
                                <p className="text-[12px] mt-3 leading-relaxed" style={{ color: "#ea0954" }}>
                                  <span className="font-semibold">Feedback:</span> {q.answer.rationale}
                                </p>
                              )}
                            </div>
                          ) : (
                            <span className="text-[13px] italic" style={{ color: "#9ca3af" }}>No answer submitted</span>
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
              <div className="text-[11px] font-bold uppercase tracking-widest mb-4" style={{ color: "#9ca3af" }}>
                Overall Score
              </div>
              <div
                className="text-[60px] font-bold leading-none mb-1 tracking-tight"
                style={{ color: scoreColor(score), fontFamily: "'Outfit', sans-serif" }}
              >
                {score.toFixed(1)}
              </div>
              <div className="text-[12px] mb-5" style={{ color: "#9ca3af" }}>out of 10</div>
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
              <div className="text-[11px] font-bold uppercase tracking-widest mb-3" style={{ color: "#9ca3af" }}>
                Recommendation
              </div>
              <div className="flex items-center justify-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full" style={{ background: rec.color }} />
                <span className="text-[18px] font-bold" style={{ color: rec.color }}>{rec.label}</span>
              </div>
            </div>

            <div className="card p-5">
              <div className="text-[11px] font-bold uppercase tracking-widest mb-4" style={{ color: "#9ca3af" }}>
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
                    <span className="text-[12px]" style={{ color: "#9ca3af" }}>{item.label}</span>
                    <span className={`text-[12px] font-semibold ${item.cap ? "capitalize" : ""}`} style={{ color: "#0b0c15" }}>
                      {item.value}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {parsed_resume?.skills?.length > 0 && (
              <div className="card p-5">
                <div className="text-[11px] font-bold uppercase tracking-widest mb-4" style={{ color: "#9ca3af" }}>
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
