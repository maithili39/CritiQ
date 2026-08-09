import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listSessions, getCalibration, SessionListItem } from "@/lib/api";
import Navbar from "@/components/Navbar";
import SiteFooter from "@/components/SiteFooter";

type Calibration = Awaited<ReturnType<typeof getCalibration>>;

function CalibrationBanner({ cal }: { cal: Calibration }) {
  if (cal.total_labeled === 0) return null;
  const corr = cal.correlation;
  const corrColor =
    corr == null ? "var(--muted)" : corr >= 0.5 ? "var(--success)" : corr >= 0.3 ? "var(--warning)" : "var(--danger)";
  const corrLabel =
    corr == null ? "Need ≥3 outcomes" : corr >= 0.5 ? "Strong" : corr >= 0.3 ? "Moderate" : "Weak";
  const { true_positive: tp, false_positive: fp, false_negative: fn, true_negative: tn } = cal.confusion;
  const decided = tp + fp + fn + tn;
  const accuracy = decided ? Math.round(((tp + tn) / decided) * 100) : null;

  const stats = [
    { label: "Labeled outcomes",         value: String(cal.total_labeled), color: undefined },
    { label: "Score↔hire correlation",  value: corr == null ? "—" : corr.toFixed(2), sub: corrLabel, color: corrColor },
    { label: "Recommendation accuracy", value: accuracy == null ? "—" : `${accuracy}%`,  color: undefined },
    { label: "Missed strong hires",      value: String(fn), color: fn > 0 ? "var(--warning)" : "var(--success)" },
  ];

  return (
    <div
      className="card p-6 mb-6 fade-up"
      style={{ borderColor: "rgba(245,158,11,0.2)", background: "rgba(245,158,11,0.04)" }}
    >
      <div className="flex items-center justify-between mb-5">
        <div className="eyebrow" style={{ background: "none", border: "none", padding: 0 }}>
          <span>✦</span> Screening Calibration
        </div>
        <span
          className="badge"
          style={{ fontSize: "11px", color: "var(--muted)" }}
        >
          Validated against real hiring outcomes
        </span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-5">
        {stats.map((s) => (
          <div key={s.label}>
            <div
              className="font-bold leading-none mb-1"
              style={{
                fontSize: "30px",
                color: s.color ?? "var(--ink)",
                fontFamily: "'Outfit', sans-serif",
              }}
            >
              {s.value}
            </div>
            <div style={{ fontSize: "12px", color: "var(--muted)", fontFamily: "'Inter', sans-serif" }}>
              {s.label}
            </div>
            {s.sub ? (
              <div
                className="text-[10px] font-semibold mt-0.5"
                style={{ color: s.color, fontFamily: "'Inter', sans-serif" }}
              >
                {s.sub}
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

const ROLE_LABELS: Record<string, string> = {
  ai_ml: "AI / ML Engineer",
  data_science: "Data Scientist",
};

const STATUS_MAP: Record<string, { label: string; color: string; statusClass: string }> = {
  created:   { label: "Not started",  color: "var(--muted)",   statusClass: "" },
  active:    { label: "In progress",  color: "var(--warning)", statusClass: "status-active" },
  completed: { label: "Completed",    color: "var(--success)", statusClass: "status-completed" },
};

function scoreColor(s: number) {
  return s >= 7 ? "var(--success)" : s >= 5 ? "var(--warning)" : "var(--danger)";
}

function getInitials(name: string) {
  return name.split(" ").slice(0, 2).map((w) => w[0]?.toUpperCase() ?? "").join("");
}

const PAGE_SIZE = 20;

export default function MySessionsPage() {
  const [sessions, setSessions] = useState<SessionListItem[] | null>(null);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [loadingMore, setLoadingMore] = useState(false);
  const [calibration, setCalibration] = useState<Calibration | null>(null);

  useEffect(() => {
    listSessions(PAGE_SIZE, 0)
      .then((res) => { setSessions(res.sessions); setTotal(res.total); })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load sessions."));
    getCalibration().then(setCalibration).catch(() => {});
  }, []);

  const loadMore = () => {
    if (!sessions) return;
    setLoadingMore(true);
    listSessions(PAGE_SIZE, sessions.length)
      .then((res) => setSessions([...sessions, ...res.sessions]))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load more."))
      .finally(() => setLoadingMore(false));
  };

  return (
    <div className="page-stack">
      <Navbar />

      {/* ── HEADER BANNER ── */}
      <div className="sessions-header">
        <div className="shell">
          <div className="flex items-center justify-between gap-4 flex-wrap fade-up">
            <div>
              <div
                className="eyebrow mb-3"
                style={{ background: "none", border: "none", padding: 0 }}
              >
                Your Workspace
              </div>
              <h1
                className="font-bold tracking-tight mb-2"
                style={{
                  fontSize: "clamp(28px, 4vw, 42px)",
                  fontFamily: "'Outfit', sans-serif",
                  color: "var(--ink)",
                  letterSpacing: "-0.02em",
                }}
              >
                Candidate Sessions
              </h1>
              <p style={{ fontSize: "15px", color: "var(--muted)", fontFamily: "'Inter', sans-serif" }}>
                Track interview status, view completed reports, and continue in-progress sessions.
              </p>
            </div>
            <div className="flex items-center gap-3">
              {sessions !== null && (
                <span
                  className="badge"
                  style={{ fontSize: "13px", padding: "0.35rem 0.9rem" }}
                >
                  {total} session{total !== 1 ? "s" : ""}
                </span>
              )}
              <Link
                to="/interview/setup"
                className="btn btn-primary btn-sm"
                style={{ borderRadius: "999px" }}
              >
                + New session
              </Link>
            </div>
          </div>
        </div>
      </div>

      <main className="section" style={{ flex: 1 }}>
        <div className="shell">

          {error ? <div className="alert-error mb-5">{error}</div> : null}

          {calibration ? <CalibrationBanner cal={calibration} /> : null}

          {/* loading */}
          {sessions === null && !error ? (
            <div
              className="card p-12 text-center fade-in"
              style={{ borderStyle: "dashed" }}
            >
              <span
                className="w-10 h-10 border-2 rounded-full spin inline-block"
                style={{ borderColor: "var(--border-strong)", borderTopColor: "var(--brand)" }}
              />
              <p style={{ color: "var(--muted)", fontSize: "14px", marginTop: "0.8rem", fontFamily: "'Inter', sans-serif" }}>
                Loading sessions…
              </p>
            </div>
          ) : null}

          {/* empty state */}
          {sessions?.length === 0 ? (
            <div className="card p-14 text-center fade-in">
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-5"
                style={{ background: "var(--brand-soft)", border: "1px solid var(--brand-line)" }}
              >
                <svg className="w-7 h-7" style={{ color: "var(--brand)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              </div>
              <h3
                className="font-bold mb-2"
                style={{ fontSize: "20px", fontFamily: "'Outfit', sans-serif", color: "var(--ink)" }}
              >
                No sessions yet
              </h3>
              <p style={{ color: "var(--muted)", fontSize: "14px", marginBottom: "1.5rem", fontFamily: "'Inter', sans-serif" }}>
                Start your first candidate interview to see it appear here.
              </p>
              <Link to="/interview/setup" className="btn btn-primary" style={{ borderRadius: "999px" }}>
                Start session
              </Link>
            </div>
          ) : null}

          {/* sessions list */}
          {sessions && sessions.length > 0 ? (
            <div className="flex flex-col gap-3 fade-up delay-1">
              {sessions.map((s) => {
                const status = STATUS_MAP[s.status] ?? STATUS_MAP.created;
                const href =
                  s.status === "completed"
                    ? `/interview/${s.id}/report`
                    : `/interview/${s.id}`;
                return (
                  <Link
                    key={s.id}
                    to={href}
                    className={`session-card ${status.statusClass}`}
                  >
                    {/* left — avatar + info */}
                    <div className="flex items-center gap-4">
                      <div className="session-avatar">
                        {getInitials(s.candidate_name)}
                      </div>
                      <div>
                        <div
                          className="font-semibold mb-1"
                          style={{ fontSize: "16px", color: "var(--ink)", fontFamily: "'Inter', sans-serif" }}
                        >
                          {s.candidate_name}
                        </div>
                        <div
                          className="flex items-center gap-2 flex-wrap"
                          style={{ fontSize: "13px", color: "var(--muted)", fontFamily: "'Inter', sans-serif" }}
                        >
                          <span>{ROLE_LABELS[s.role] || s.role}</span>
                          <span style={{ opacity: 0.4 }}>·</span>
                          <span>
                            {new Date(s.created_at).toLocaleDateString("en-GB", {
                              day: "numeric",
                              month: "short",
                              year: "numeric",
                            })}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* right — score + status */}
                    <div className="flex items-center gap-4">
                      {s.overall_score != null ? (
                        <span
                          className="font-bold"
                          style={{
                            fontSize: "18px",
                            color: scoreColor(s.overall_score),
                            fontFamily: "'Outfit', sans-serif",
                          }}
                        >
                          {`${s.overall_score.toFixed(1)}/10`}
                        </span>
                      ) : null}
                      <span
                        className="badge"
                        style={{ color: status.color, borderColor: status.color + "44", background: status.color + "11" }}
                      >
                        {status.label}
                      </span>
                      <svg
                        className="w-4 h-4"
                        style={{ color: "var(--muted)", flexShrink: 0 }}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2}
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </Link>
                );
              })}
            </div>
          ) : null}

          {/* load more */}
          {sessions && sessions.length > 0 && sessions.length < total ? (
            <div className="flex justify-center mt-8">
              <button
                onClick={loadMore}
                disabled={loadingMore}
                className="btn btn-secondary"
                style={{ borderRadius: "999px" }}
              >
                {loadingMore ? "Loading…" : `Load more (${sessions.length} of ${total})`}
              </button>
            </div>
          ) : null}

        </div>
      </main>

      <SiteFooter />
    </div>
  );
}
