import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listSessions, getCalibration, SessionListItem } from "@/lib/api";
import Navbar from "@/components/Navbar";
import SiteFooter from "@/components/SiteFooter";

type Calibration = Awaited<ReturnType<typeof getCalibration>>;

function CalibrationBanner({ cal }: { cal: Calibration }) {
  if (cal.total_labeled === 0) return null;
  const corr = cal.correlation;
  // Pearson r: >0.5 strong, 0.3-0.5 moderate, else weak/insufficient.
  const corrColor = corr == null ? "var(--cyan)" : corr >= 0.5 ? "#34d399" : corr >= 0.3 ? "#fbbf24" : "#f87171";
  const corrLabel = corr == null ? "Need ≥3 outcomes" : corr >= 0.5 ? "Strong" : corr >= 0.3 ? "Moderate" : "Weak";
  const { true_positive: tp, false_positive: fp, false_negative: fn, true_negative: tn } = cal.confusion;
  const decided = tp + fp + fn + tn;
  const accuracy = decided ? Math.round(((tp + tn) / decided) * 100) : null;

  const stats = [
    { label: "Labeled outcomes", value: String(cal.total_labeled) },
    { label: "Score↔hire correlation", value: corr == null ? "—" : corr.toFixed(2), sub: corrLabel, color: corrColor },
    { label: "Recommendation accuracy", value: accuracy == null ? "—" : `${accuracy}%` },
    { label: "Missed strong hires", value: String(fn), color: fn > 0 ? "#fbbf24" : undefined },
  ];

  return (
    <div className="card p-6 mb-6 fade-up">
      <div className="flex items-center justify-between mb-4">
        <div className="eyebrow">Screening Calibration</div>
        <span className="badge muted text-[11px]">validated against your real hiring outcomes</span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {stats.map((s) => (
          <div key={s.label}>
            <div className="text-[26px] font-bold leading-none mb-1" style={{ color: s.color ?? "var(--text)", fontFamily: "'Outfit', sans-serif" }}>
              {s.value}
            </div>
            <div className="text-[11px] muted">{s.label}</div>
            {s.sub ? <div className="text-[10px] font-semibold mt-0.5" style={{ color: s.color }}>{s.sub}</div> : null}
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

const STATUS_LABEL: Record<string, { label: string; color: string }> = {
  created: { label: "Not started", color: "var(--muted)" },
  active: { label: "In progress", color: "#fbbf24" },
  completed: { label: "Completed", color: "#34d399" },
};

function scoreColor(s: number) {
  return s >= 7 ? "#34d399" : s >= 5 ? "#fbbf24" : "#f87171";
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
    // Non-critical — the dashboard still renders if calibration can't load.
    getCalibration().then(setCalibration).catch(() => {});
  }, []);

  const loadMore = () => {
    if (!sessions) return;
    setLoadingMore(true);
    listSessions(PAGE_SIZE, sessions.length)
      .then((res) => setSessions([...sessions, ...res.sessions]))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load more sessions."))
      .finally(() => setLoadingMore(false));
  };

  return (
    <div className="page-stack">
      <Navbar />

      <main className="section" style={{ flex: 1 }}>
        <div className="shell">
          <div className="mb-8 fade-up">
            <div className="eyebrow mb-3">Your Workspace</div>
            <h1 className="text-[36px] font-bold tracking-tight mb-2">Candidate sessions</h1>
            <p className="muted text-[15px]">Track interview status, view completed reports, and continue in-progress sessions.</p>
          </div>

          {error ? <div className="alert-error mb-4">{error}</div> : null}

          {calibration ? <CalibrationBanner cal={calibration} /> : null}

          {sessions === null && !error ? (
            <div className="card p-10 text-center">
              <span className="w-8 h-8 border-2 rounded-full spin inline-block" style={{ borderColor: "var(--border)", borderTopColor: "var(--brand)" }} />
              <p className="muted text-[14px] mt-3">Loading sessions</p>
            </div>
          ) : null}

          {sessions?.length === 0 ? (
            <div className="card p-10 text-center">
              <p className="muted text-[15px] mb-4">No sessions yet. Start your first candidate interview.</p>
              <Link to="/interview/setup" className="btn btn-primary">Start session</Link>
            </div>
          ) : null}

          {sessions && sessions.length > 0 ? (
            <div className="grid grid-cols-1 gap-3 fade-up delay-1">
              {sessions.map((s) => {
                const status = STATUS_LABEL[s.status] ?? STATUS_LABEL.created;
                const href = s.status === "completed" ? `/interview/${s.id}/report` : `/interview/${s.id}`;
                return (
                  <Link key={s.id} to={href} className="card card-hover p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                    <div>
                      <div className="text-[17px] font-semibold mb-1.5">{s.candidate_name}</div>
                      <div className="flex items-center gap-2 text-[13px] muted flex-wrap">
                        <span>{ROLE_LABELS[s.role] || s.role}</span>
                        <span>•</span>
                        <span>{new Date(s.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      {s.overall_score != null ? (
                        <span className="text-[16px] font-bold" style={{ color: scoreColor(s.overall_score) }}>
                          {s.overall_score.toFixed(1)}/10
                        </span>
                      ) : null}
                      <span className="badge" style={{ color: status.color }}>{status.label}</span>
                    </div>
                  </Link>
                );
              })}
            </div>
          ) : null}

          {sessions && sessions.length > 0 && sessions.length < total ? (
            <div className="flex justify-center mt-6">
              <button onClick={loadMore} disabled={loadingMore} className="btn btn-secondary text-[14px] px-6 py-2.5">
                {loadingMore ? "Loading..." : `Load more (${sessions.length} of ${total})`}
              </button>
            </div>
          ) : null}
        </div>
      </main>

      <SiteFooter />
    </div>
  );
}
