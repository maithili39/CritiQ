import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Navbar from "@/components/Navbar";
import SiteFooter from "@/components/SiteFooter";
import { getRoles, RoleInfo } from "@/lib/api";

/* ─── static data ─── */
const FEATURES = [
  {
    tag: "01",
    title: "Questions match the resume",
    desc: "Each interview is generated from the candidate's actual background — their stack, their projects, their stated experience level — instead of a fixed question bank.",
    icon: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
  },
  {
    tag: "02",
    title: "Role tracks stay consistent",
    desc: "Every track is backed by a curated topic list, so two candidates on the same track get comparable coverage instead of drifting question quality.",
    icon: "M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253",
  },
  {
    tag: "03",
    title: "Scoring happens as they answer",
    desc: "Each response is scored the moment it's submitted, with a note on what was strong and what was missing — not batched into a report at the end.",
    icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
  },
];

const HOW = [
  { n: "01", title: "Resume parsed",       desc: "Skills, tech stack, and experience level extracted from the uploaded resume." },
  { n: "02", title: "Questions generated", desc: "Role-specific prompts assembled around that candidate's background." },
  { n: "03", title: "Answers evaluated",   desc: "Every response scored against the topic it targets, with a short justification." },
  { n: "04", title: "Report produced",     desc: "A hiring report covering topic coverage, scores, and a recommendation." },
];

const FALLBACK_ROLES: RoleInfo[] = [
  {
    slug: "ai_ml",
    label: "AI / ML Engineer",
    description: "Machine learning depth, model strategy, and practical engineering fluency.",
    topics: ["Neural Networks", "Model Evaluation", "MLOps", "Transformers"],
    is_builtin: true,
  },
  {
    slug: "data_science",
    label: "Data Scientist",
    description: "Statistical judgement, experimental rigor, and clear analysis communication.",
    topics: ["Statistical Inference", "A/B Testing", "SQL & Pandas", "EDA"],
    is_builtin: true,
  },
];

export default function Home() {
  const [roles, setRoles] = useState<RoleInfo[]>(FALLBACK_ROLES);

  useEffect(() => {
    getRoles()
      .then((res) => { if (res.roles?.length) setRoles(res.roles); })
      .catch(() => {});
  }, []);

  return (
    <div className="page-stack">
      <Navbar />

      {/* ── HERO ───────────────────────────────────────────── */}
      <section className="hero-section">
        <div className="shell hero-grid-single hero-center relative z-10">
          <div className="fade-up">
            <span className="hero-kicker">Technical screening</span>

            <h1 className="hero-title">
              A technical interview that reads the resume first.
            </h1>

            <p className="hero-sub">
              CritiQ parses the candidate's resume, builds a set of questions
              around what they actually claim to know, and scores each answer
              as it comes in — so the report is ready the moment the
              interview ends.
            </p>

            <div className="flex items-center justify-center gap-3 flex-wrap">
              <Link to="/interview/setup" className="btn btn-primary btn-lg">
                Start a session
              </Link>
              <Link to="/register" className="btn btn-secondary btn-lg">
                Create free account
              </Link>
            </div>

            <ul className="hero-facts">
              <li>Questions are grounded in the parsed resume — nothing invented</li>
              <li>Scoring runs live, per answer, not as a single end-of-interview pass</li>
            </ul>
          </div>
        </div>
      </section>

      {/* ── STATS STRIP ────────────────────────────────────── */}
      <div className="shell">
        <div className="stats-strip">
          {[
            { value: "8", label: "Live questions per assessment" },
            { value: String(roles.length), label: "Specialized role tracks" },
            { value: "100%", label: "Source-grounded questions" },
            { value: "< 60s", label: "Setup time before first question" },
          ].map((s, i) => (
            <div key={i} className="stats-strip-item">
              <span className="stats-strip-value">{s.value}</span>
              <span className="stats-strip-label">{s.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── HOW IT WORKS ───────────────────────────────────── */}
      <section className="section" style={{ background: "var(--bg-soft)" }}>
        <div className="shell">
          <div className="section-head fade-up">
            <span className="section-kicker">How it works</span>
            <h2 className="section-title">From resume to scored report</h2>
          </div>

          <div className="steps-grid fade-up delay-1">
            {HOW.map((h) => (
              <div key={h.n} className="step-item">
                <div className="step-num">{parseInt(h.n)}</div>
                <div className="step-title">{h.title}</div>
                <p className="step-desc">{h.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FEATURES ───────────────────────────────────────── */}
      <section className="section">
        <div className="shell">
          <div className="section-head fade-up">
            <span className="section-kicker">Platform</span>
            <h2 className="section-title">What actually happens during a session</h2>
          </div>

          <div className="feature-grid fade-up delay-1">
            {FEATURES.map((f) => (
              <div key={f.tag} className="feature-card">
                <div className="feature-icon">
                  <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.6}>
                    <path strokeLinecap="round" strokeLinejoin="round" d={f.icon} />
                  </svg>
                </div>
                <div className="feature-tag">{f.tag}</div>
                <h3 className="feature-title">{f.title}</h3>
                <p className="feature-desc">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── ROLE TRACKS ────────────────────────────────────── */}
      <section className="section" style={{ background: "var(--bg-soft)" }}>
        <div className="shell">
          <div className="section-head-row fade-up">
            <div>
              <span className="section-kicker">Role tracks</span>
              <h2 className="section-title">Pick a track and start immediately</h2>
            </div>
            <Link to="/interview/setup" className="btn btn-secondary btn-sm">
              View all tracks
            </Link>
          </div>

          <div className="role-grid fade-up delay-1">
            {roles.map((r) => (
              <div key={r.slug} className="role-card">
                <div className="feature-tag">
                  {r.is_builtin ? "Built-in track" : "Custom track"}
                </div>
                <h3 className="role-card-title">{r.label}</h3>
                <p className="role-card-desc">{r.description}</p>
                <div className="role-card-topics-label">Topics covered</div>
                <div className="role-card-topics">
                  {r.topics.map((t) => (
                    <span key={t} className="badge">{t}</span>
                  ))}
                </div>
                <Link
                  to="/interview/setup"
                  className="btn btn-ghost-brand btn-sm mt-auto"
                  style={{ alignSelf: "flex-start" }}
                >
                  Launch track →
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CLOSING BANNER ─────────────────────────────────── */}
      <section className="section closing-banner">
        <div className="shell text-center relative fade-up" style={{ zIndex: 1 }}>
          <span className="section-kicker">Why it exists</span>
          <h2 className="closing-title">
            First-round technical screening shouldn't depend on
            who's free to run it.
          </h2>
          <p className="closing-sub">
            CritiQ runs the same structured interview for every candidate on
            a track — same topic coverage, same scoring criteria — so the
            first read on a candidate isn't shaped by which interviewer they
            happened to get.
          </p>
          <div className="flex items-center justify-center gap-3 flex-wrap">
            <Link to="/interview/setup" className="btn btn-primary btn-lg">
              Start your first session
            </Link>
            <Link to="/register" className="btn btn-subtle btn-lg">
              Create free account
            </Link>
          </div>
        </div>
      </section>

      <SiteFooter />
    </div>
  );
}
