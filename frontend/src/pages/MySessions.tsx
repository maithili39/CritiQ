import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listSessions, SessionListItem } from "@/lib/api";
import Navbar from "@/components/Navbar";
import SiteFooter from "@/components/SiteFooter";

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

export default function MySessionsPage() {
  const [sessions, setSessions] = useState<SessionListItem[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    listSessions()
      .then((res) => setSessions(res.sessions))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load sessions."));
  }, []);

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
        </div>
      </main>

      <SiteFooter />
    </div>
  );
}
