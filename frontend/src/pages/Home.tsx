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

      {/* Hero Section */}
      <section className="relative overflow-hidden pt-12 pb-16 md:pt-20 md:pb-20">
        <div className="blob blob-1" />
        <div className="blob blob-2" />
        <div className="blob blob-3" />

        <div className="shell shell-wide relative z-10">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
            <div className="fade-up">
              <h1 className="font-extrabold leading-tight tracking-tight mb-6" style={{ fontSize: "clamp(40px, 5.5vw, 60px)", color: "var(--ink)" }}>
                Interview like it's <span className="gradient-text">already decided.</span>
              </h1>
              <p className="text-[18px] leading-relaxed mb-8" style={{ maxWidth: "540px", color: "var(--muted)" }}>
                CritiQ parses resumes, runs adaptive technical interviews, and scores every answer live — so the report writes itself.
              </p>
              <div className="flex items-center gap-3 flex-wrap">
                <Link to="/interview/setup" className="btn btn-primary" style={{ padding: "0.9rem 2.2rem", borderRadius: "999px", fontSize: "16px" }}>
                  Start a session
                </Link>
                <Link to="/register" className="btn" style={{ padding: "0.9rem 2rem", borderRadius: "999px", color: "var(--ink)", border: "1.5px solid var(--border-strong)", fontSize: "16px" }}>
                  Create free account
                </Link>
              </div>
            </div>

            <div className="fade-up delay-1 relative hidden lg:block">
              <div className="absolute -inset-4 rounded-2xl opacity-60" style={{ background: "var(--gradient-brand-soft)", filter: "blur(20px)", zIndex: 0 }} />
              <img
                src="https://images.unsplash.com/photo-1531482615713-2afd69097998?w=700&q=80&auto=format&fit=crop"
                alt="Candidate taking interview"
                className="w-full rounded-xl border border-amber-900/20 shadow-lg relative z-10"
                style={{ aspectRatio: "4/3", objectFit: "cover" }}
                loading="eager"
              />
            </div>
          </div>

          {/* Stats inline in hero */}
          <div className="grid grid-cols-3 gap-4 mt-12 md:mt-16 fade-up delay-2">
            <div className="text-center">
              <div className="text-4xl md:text-5xl font-extrabold mb-2" style={{ color: "var(--brand)" }}>8</div>
              <p className="text-sm md:text-base muted">Live questions per assessment</p>
            </div>
            <div className="text-center">
              <div className="text-4xl md:text-5xl font-extrabold mb-2" style={{ color: "var(--brand)" }}>{roles.length}</div>
              <p className="text-sm md:text-base muted">Specialized role tracks</p>
            </div>
            <div className="text-center">
              <div className="text-4xl md:text-5xl font-extrabold mb-2" style={{ color: "var(--brand)" }}>100%</div>
              <p className="text-sm md:text-base muted">Source-grounded questions</p>
            </div>
          </div>
        </div>
      </section>

      {/* How the Platform Works */}
      <section className="section section-soft">
        <div className="shell shell-wide">
          <div className="text-center mb-16 fade-up">
            <div className="inline-block mb-4 px-3 py-1 rounded-full" style={{ background: "var(--brand-soft)", border: "1px solid var(--brand-line)" }}>
              <span className="text-[12px] font-bold tracking-widest uppercase" style={{ color: "var(--brand)" }}>How the Platform Works</span>
            </div>
            <h2 className="font-bold tracking-tight mb-4" style={{ fontSize: "clamp(32px, 4.5vw, 48px)", color: "var(--ink)" }}>
              Built for hiring teams that need <span className="gradient-text">reliable interview outcomes</span>
            </h2>
            <p className="text-[17px] muted" style={{ maxWidth: "700px", margin: "0 auto" }}>
              Designed for client-facing delivery with a refined workflow, clear pacing, and consistent decision support.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {FEATURES.map((f, idx) => (
              <div key={f.tag} className={`card p-8 fade-up delay-${Math.min(idx + 1, 4)}`} style={{ transition: "all 0.3s cubic-bezier(0.22, 1, 0.36, 1)" }}>
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl mb-5" style={{ background: "var(--brand-soft)", color: "var(--brand)" }}>
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                    <path strokeLinecap="round" strokeLinejoin="round" d={f.icon} />
                  </svg>
                </div>
                <div className="text-[12px] font-bold tracking-widest uppercase mb-3" style={{ color: "var(--brand)" }}>{f.tag}</div>
                <h3 className="text-[20px] font-bold mb-3" style={{ color: "var(--ink)", lineHeight: 1.3 }}>{f.title}</h3>
                <p className="text-[15px] muted leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Role Coverage */}
      <section className="section">
        <div className="shell shell-wide">
          <div className="text-center mb-12 fade-up">
            <div className="inline-block mb-4 px-3 py-1 rounded-full" style={{ background: "var(--brand-soft)", border: "1px solid var(--brand-line)" }}>
              <span className="text-[12px] font-bold tracking-widest uppercase" style={{ color: "var(--brand)" }}>Role Coverage</span>
            </div>
            <h2 className="font-bold tracking-tight mb-3" style={{ fontSize: "clamp(32px, 4.5vw, 48px)", color: "var(--ink)" }}>
              Curated tracks for modern data and engineering hiring
            </h2>
            <p className="text-[16px] muted" style={{ maxWidth: "640px", margin: "0 auto" }}>
              Each track includes focused topic areas so assessments remain comparable across candidates.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {roles.map((r) => (
              <div key={r.slug} className="card card-hover p-7 fade-up">
                <div className="text-[12px] font-bold tracking-widest uppercase mb-3" style={{ color: "var(--brand)" }}>
                  {r.is_builtin ? "Built-in Track" : "Custom Track"}
                </div>
                <h3 className="text-[24px] font-bold mb-3" style={{ color: "var(--ink)" }}>{r.label}</h3>
                <p className="text-[14px] muted leading-relaxed mb-5">{r.description}</p>
                <div className="flex flex-wrap gap-2 mb-6">
                  {r.topics.map((topic) => <span key={topic} className="badge">{topic}</span>)}
                </div>
                <Link to="/interview/setup" className="btn btn-subtle btn-sm mt-auto">Launch this track →</Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="section section-soft">
        <div className="shell text-center">
          <h2 className="font-bold tracking-tight mb-4 fade-up" style={{ fontSize: "clamp(28px, 4.5vw, 44px)", color: "var(--ink)" }}>
            Ready to deliver a stronger hiring experience?
          </h2>
          <p className="text-[17px] muted mb-8 fade-up delay-1" style={{ maxWidth: "640px", margin: "0 auto 2rem" }}>
            Start your next candidate interview in minutes and get a scored report the moment it's done.
          </p>
          <div className="flex items-center justify-center gap-3 flex-wrap fade-up delay-2">
            <Link to="/interview/setup" className="btn btn-primary">Start interview now</Link>
            <Link to="/sessions" className="btn btn-secondary">View existing sessions</Link>
          </div>
        </div>
      </section>

      <SiteFooter />
    </div>
  );
}
