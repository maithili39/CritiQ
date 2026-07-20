import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Navbar from "@/components/Navbar";
import SiteFooter from "@/components/SiteFooter";
import { getRoles, RoleInfo } from "@/lib/api";

const FEATURES = [
  {
    tag: "Candidate Intelligence",
    title: "Assessments shaped around each profile",
    desc: "Every interview follows the candidate background, focusing on relevant strengths and coverage gaps instead of generic templates.",
    icon: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
  },
  {
    tag: "Structured Knowledge",
    title: "Question quality stays consistent under scale",
    desc: "Interview prompts are grounded in curated role tracks so recruiters get reliable depth even across large candidate batches.",
    icon: "M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253",
  },
  {
    tag: "Live Scoring",
    title: "Actionable feedback after every response",
    desc: "Recruiters see strengths, concerns, and confidence signals throughout the interview, not only at the end.",
    icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
  },
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
      .then((res) => {
        if (res.roles?.length) setRoles(res.roles);
      })
      .catch(() => {});
  }, []);

  return (
    <div className="page-stack">
      <Navbar />

      <section className="relative overflow-hidden pt-12 pb-8 md:pt-16">
        <div className="blob blob-1" />
        <div className="blob blob-2" />
        <div className="blob blob-3" />

        <div className="shell shell-wide relative z-10">
          <div className="bento-grid">
            {/* Manifesto */}
            <div className="bento-item bento-manifesto fade-up">
              <span className="text-[12px] font-bold tracking-[0.2em] uppercase" style={{ color: "rgba(255,255,255,0.6)" }}>
                CritiQ / Screening Engine
              </span>
              <h1 className="font-extrabold tracking-tight mt-4 mb-5" style={{ fontSize: "clamp(36px, 5vw, 56px)", lineHeight: 1.02, color: "#fff" }}>
                Interview
                <br />
                like it's
                <br />
                <span className="gradient-text">already decided.</span>
              </h1>
              <p className="text-[15px] leading-relaxed mb-7" style={{ maxWidth: "420px", color: "rgba(255,255,255,0.78)" }}>
                CritiQ parses resumes, runs adaptive technical interviews, and scores every answer live — so the report writes itself.
              </p>
              <div className="flex items-center gap-3 flex-wrap">
                <Link to="/interview/setup" className="btn btn-primary" style={{ padding: "0.85rem 1.9rem", borderRadius: "999px" }}>
                  Start a session
                </Link>
                <Link to="/register" className="btn" style={{ padding: "0.85rem 1.7rem", borderRadius: "999px", color: "#fff", border: "1.5px solid rgba(255,255,255,0.28)" }}>
                  Create free account
                </Link>
              </div>
            </div>

            {/* Live Assessment Visual */}
            <div className="bento-item bento-visual fade-up delay-1">
              <div className="transcript-head">
                <span className="dot-cluster"><i /><i /><i /></span>
                <span className="text-[11px] font-semibold tracking-wide uppercase" style={{ color: "var(--muted)" }}>Live Assessment</span>
              </div>
              <div className="transcript-line">
                <span className="transcript-tag">Q</span>
                <p>Walk me through how you'd validate a model that overfits during cross-validation.</p>
              </div>
              <div className="transcript-line transcript-line-muted">
                <span className="transcript-tag transcript-tag-alt">A</span>
                <p>Candidate response received — scoring in progress…</p>
              </div>
              <div className="transcript-score">
                <div className="transcript-score-num">8.4<span>/10</span></div>
                <div className="progress-track" style={{ flex: 1 }}>
                  <div className="progress-fill" style={{ width: "84%", background: "var(--gradient-brand)" }} />
                </div>
              </div>
              <div className="flex flex-wrap gap-2 mt-3">
                <span className="badge badge-brand">Strong: regularization</span>
                <span className="badge">Gap: edge cases</span>
              </div>
            </div>

            {/* Stat Tiles */}
            <article className="bento-item bento-stat fade-up delay-2" style={{ background: "var(--gradient-brand)" }}>
              <strong style={{ color: "#fff" }}>8</strong>
              <span style={{ color: "rgba(255,255,255,0.85)" }}>Live questions per assessment</span>
            </article>

            <article className="bento-item bento-stat-duo fade-up delay-2">
              <div className="bento-stat-duo-col">
                <strong className="gradient-text">{roles.length}</strong>
                <span className="muted">Specialized role tracks</span>
              </div>
              <div className="bento-stat-duo-divider" />
              <div className="bento-stat-duo-col">
                <strong className="gradient-text">100%</strong>
                <span className="muted">Source-grounded questions</span>
              </div>
            </article>

            {/* Feature Cards */}
            {FEATURES.map((f, idx) => (
              <article key={f.tag} className={`bento-item bento-feature fade-up delay-${Math.min(idx + 1, 4)}`}>
                <div className="inline-flex items-center justify-center w-11 h-11 rounded-xl mb-4" style={{ background: "var(--brand-soft)", border: "1px solid var(--brand-line)", color: "var(--brand)" }}>
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                    <path strokeLinecap="round" strokeLinejoin="round" d={f.icon} />
                  </svg>
                </div>
                <div className="text-[11px] font-bold tracking-widest uppercase mb-2" style={{ color: "var(--brand)" }}>{f.tag}</div>
                <h3 className="text-[18px] font-bold mb-2" style={{ color: "var(--ink)", lineHeight: 1.3 }}>{f.title}</h3>
                <p className="text-[14px] muted leading-relaxed mb-4">{f.desc}</p>
              </article>
            ))}

            {/* Role Cards */}
            {roles.map((r) => (
              <article key={r.slug} className="bento-item bento-role bento-role-soft fade-up">
                <div className="eyebrow mb-2">{r.is_builtin ? "Built-in Track" : "Custom Track"}</div>
                <h3 className="text-[20px] font-bold mb-2">{r.label}</h3>
                <p className="muted text-[13px] leading-relaxed mb-4">{r.description}</p>
                <div className="flex flex-wrap gap-1.5 mb-4">
                  {r.topics.map((topic) => <span key={topic} className="badge">{topic}</span>)}
                </div>
                <Link to="/interview/setup" className="btn btn-subtle btn-sm mt-auto">Launch this track →</Link>
              </article>
            ))}

            {/* About Banner */}
            <div className="bento-item bento-about fade-up">
              <div className="bento-about-text">
                <div className="eyebrow mb-3" style={{ color: "rgba(255,255,255,0.75)" }}>About Us</div>
                <h2 className="font-bold tracking-tight mb-3" style={{ fontSize: "clamp(24px, 3.2vw, 34px)", color: "#fff" }}>
                  Unbiased, skills-first technical hiring — built into the interview itself.
                </h2>
                <p className="text-[15px] leading-relaxed" style={{ color: "rgba(255,255,255,0.78)" }}>
                  CritiQ automates the technical interview with adaptive, source-grounded AI — uncovering real talent while cutting scheduling bottlenecks and first-round bias.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="section-soft" style={{ paddingBlock: "clamp(2.4rem, 5vw, 4rem)" }}>
        <div className="shell text-center">
          <h2 className="font-bold tracking-tight mb-4" style={{ fontSize: "clamp(28px, 4.5vw, 44px)", color: "var(--ink)" }}>
            Ready to deliver a stronger hiring experience?
          </h2>
          <p className="text-[16px] muted mb-7" style={{ maxWidth: "600px", margin: "0 auto 1.8rem" }}>
            Start your next candidate interview in minutes and get a scored report the moment it's done.
          </p>
          <div className="flex items-center justify-center gap-3 flex-wrap">
            <Link to="/interview/setup" className="btn btn-primary">Start interview now</Link>
            <Link to="/sessions" className="btn btn-secondary">View existing sessions</Link>
          </div>
        </div>
      </section>

      <SiteFooter />
    </div>
  );
}
