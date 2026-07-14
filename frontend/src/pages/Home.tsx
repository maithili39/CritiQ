import { Link } from "react-router-dom";
import Navbar from "@/components/Navbar";
import SiteFooter from "@/components/SiteFooter";

const STATS = [
  { num: "8", label: "Questions per assessment, generated live" },
  { num: "2", label: "Specialized role tracks" },
  { num: "100%", label: "Questions grounded in cited source material" },
];

const FEATURES = [
  {
    tag: "Candidate Intelligence",
    title: "Assessments shaped around each profile",
    desc: "Every interview follows the candidate background, focusing on relevant strengths and coverage gaps instead of generic templates.",
    icon: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
    bullets: [
      "Role-relevant prompt progression",
      "Automatic experience calibration",
      "Reusable candidate context across the full session",
    ],
  },
  {
    tag: "Structured Knowledge",
    title: "Question quality stays consistent under scale",
    desc: "Interview prompts are grounded in curated role tracks so recruiters get reliable depth even across large candidate batches.",
    icon: "M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253",
    bullets: [
      "Role-specific content tracks",
      "Context-aware questioning sequence",
      "Clear source-backed evaluation narrative",
    ],
  },
  {
    tag: "Live Scoring",
    title: "Actionable feedback after every response",
    desc: "Recruiters see strengths, concerns, and confidence signals throughout the interview, not only at the end.",
    icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
    bullets: [
      "Per-answer scoring as soon as you submit",
      "Transparent rationale with strengths and gaps",
      "Final recommendation with topic-by-topic breakdown",
    ],
  },
];

const ROLES = [
  {
    id:     "ai_ml",
    label:  "AI / ML Engineer",
    desc: "Machine learning depth, model strategy, and practical engineering fluency.",
    topics: ["Neural Networks", "Model Evaluation", "Feature Engineering", "MLOps", "PyTorch / TF", "Transformers"],
  },
  {
    id:     "data_science",
    label:  "Data Scientist",
    desc: "Statistical judgement, experimental rigor, and clear analysis communication.",
    topics: ["Statistical Inference", "EDA", "Classification & Regression", "A/B Testing", "SQL & Pandas", "Visualisation"],
  },
];

export default function Home() {
  return (
    <div className="page-stack">
      <Navbar />

      <section className="relative pt-10 pb-16 md:pt-16 md:pb-24 overflow-hidden">
        
        <div className="shell shell-wide relative z-10 flex flex-col items-center justify-center">
          <div className="fade-up text-center flex flex-col items-center justify-center">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full mb-6" style={{ background: "var(--surface-alt)", border: "1px solid var(--border-strong)" }}>
              <span className="w-2 h-2 rounded-full" style={{ background: "var(--brand)", boxShadow: "0 0 10px rgba(234,9,84,0.6)" }} />
              <span className="text-[12px] font-semibold tracking-wide uppercase" style={{ color: "var(--ink)" }}>The New Standard for Technical Hiring</span>
            </div>
            
            <h1 className="font-extrabold leading-[1.05] tracking-tight mb-5" style={{ fontSize: "clamp(36px, 6vw, 64px)", maxWidth: "800px", color: "var(--ink)" }}>
              AI-powered candidate screening for <span style={{ color: "var(--brand)" }}>technical teams</span>.
            </h1>
            
            <p className="text-[17px] md:text-[19px] leading-relaxed mb-8" style={{ maxWidth: "700px", color: "var(--muted)" }}>
              CritiQ instantly parses resumes, conducts adaptive technical interviews, and delivers comprehensive, scored reports to help you make confident hiring decisions.
            </p>
            
            <div className="flex items-center justify-center gap-4 flex-wrap fade-up delay-1">
              <Link to="/interview/setup" className="btn btn-primary" style={{ padding: "1rem 2.6rem", fontSize: "17px", borderRadius: "999px" }}>
                Start a session
              </Link>
              <Link to="/register" className="btn btn-secondary" style={{ padding: "1rem 2.6rem", fontSize: "17px", borderRadius: "999px", background: "#fff" }}>
                Create a free account
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="section section-soft">
        <div className="shell shell-wide stat-grid">
          {STATS.map((s) => (
            <article key={s.label} className="stat-card fade-up">
              <strong>{s.num}</strong>
              <span>{s.label}</span>
            </article>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="shell shell-wide">
          <div className="text-center mb-16 flex flex-col items-center">
            <span 
              className="inline-flex items-center px-4 py-1.5 rounded-full mb-6 font-bold tracking-widest uppercase text-[11px]" 
              style={{ background: "var(--brand-soft)", color: "var(--brand)", border: "1px solid var(--brand-line)" }}
            >
              How The Platform Works
            </span>
            <h2 className="font-bold tracking-tight mb-5" style={{ fontSize: "clamp(36px, 5vw, 52px)", lineHeight: "1.15", color: "var(--ink)", maxWidth: "800px" }}>
              Built for hiring teams that need <span style={{ color: "var(--brand)" }}>reliable interview outcomes</span>
            </h2>
            <p className="muted text-[19px] leading-relaxed" style={{ maxWidth: "700px" }}>
              Designed for client-facing delivery with a refined workflow, clear pacing, and consistent decision support.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {FEATURES.map((f, idx) => (
              <article 
                key={f.tag} 
                className={`card group p-8 fade-up delay-${Math.min(idx + 1, 4)}`} 
                style={{ transition: "all 0.3s cubic-bezier(0.22, 1, 0.36, 1)", position: "relative", overflow: "hidden" }}
              >
                <div className="absolute top-0 right-0 w-40 h-40 bg-[radial-gradient(circle_at_top_right,var(--brand-soft),transparent_70%)] opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
                
                <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl mb-6 shadow-sm relative z-10" style={{ background: "linear-gradient(135deg, rgba(234,9,84,0.12), rgba(234,9,84,0.02))", border: "1px solid var(--brand-line)", color: "var(--brand)" }}>
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                    <path strokeLinecap="round" strokeLinejoin="round" d={f.icon} />
                  </svg>
                </div>
                
                <div className="text-[12px] font-bold tracking-widest uppercase mb-3 relative z-10" style={{ color: "var(--brand)" }}>{f.tag}</div>
                <h3 className="text-[22px] font-bold mb-3 relative z-10" style={{ color: "var(--ink)", lineHeight: 1.25 }}>{f.title}</h3>
                <p className="text-[15px] muted leading-relaxed mb-6 relative z-10">{f.desc}</p>
                
                <div className="w-full h-px mb-5 relative z-10" style={{ background: "linear-gradient(90deg, var(--border) 0%, transparent 100%)" }} />
                
                <ul className="flex flex-col gap-3 text-[14px] font-medium relative z-10" style={{ color: "var(--ink)" }}>
                  {f.bullets.map((item) => (
                    <li key={item} className="flex items-start gap-3">
                      <svg className="w-5 h-5 flex-shrink-0 mt-[2px]" fill="none" viewBox="0 0 24 24" stroke="var(--brand)" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                      <span style={{ color: "var(--muted)", lineHeight: 1.5 }}>{item}</span>
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="section section-soft">
        <div className="shell">
          <div className="text-center mb-12">
            <div className="eyebrow mb-4">Role Coverage</div>
            <h2 className="font-bold tracking-tight" style={{ fontSize: "clamp(28px, 4vw, 40px)", marginBottom: "0.8rem" }}>
              Curated tracks for modern data and engineering hiring
            </h2>
            <p className="muted text-[16px]" style={{ maxWidth: "640px", margin: "0 auto" }}>
              Each track includes focused topic areas so assessments remain comparable across candidates.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {ROLES.map((r) => (
              <article key={r.id} className="card card-hover p-7">
                <div className="eyebrow mb-3">{r.id === "ai_ml" ? "AI / ML Track" : "Data Science Track"}</div>
                <h3 className="text-[24px] font-bold mb-2.5">{r.label}</h3>
                <p className="muted text-[14px] leading-relaxed mb-5">{r.desc}</p>
                <div className="flex flex-wrap gap-2 mb-5">
                  {r.topics.map((topic) => <span key={topic} className="badge">{topic}</span>)}
                </div>
                <Link to="/interview/setup" className="btn btn-subtle btn-sm">Launch this track</Link>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="about" className="section" style={{ background: "var(--bg)" }}>
        <div className="shell text-center">
          <div className="eyebrow mb-4">About Us</div>
          <h2 className="font-bold tracking-tight mb-6" style={{ fontSize: "clamp(30px, 5vw, 42px)", color: "var(--ink)", maxWidth: "800px", margin: "0 auto 1.5rem" }}>
            We're building the future of unbiased, skills-first technical hiring.
          </h2>
          <p className="text-[17px] leading-relaxed muted" style={{ maxWidth: "760px", margin: "0 auto" }}>
            CritiQ is an AI-powered screening platform designed to give engineering teams high-signal, objective candidate assessments. By automating the technical interview process with adaptive, source-grounded AI, we help you uncover true talent while eliminating scheduling bottlenecks and human bias from the first-round screening process.
          </p>
        </div>
      </section>

      <section className="section section-soft">
        <div className="shell text-center">
          <h2 className="font-bold tracking-tight mb-4" style={{ fontSize: "clamp(30px, 5vw, 48px)", color: "var(--ink)" }}>
            Ready to deliver a stronger hiring experience?
          </h2>
          <p className="text-[17px] muted" style={{ maxWidth: "640px", margin: "0 auto 2rem" }}>
            Start your next candidate interview in minutes and get a scored report the moment it's done.
          </p>
          <div className="flex items-center justify-center gap-3 flex-wrap">
            <Link to="/interview/setup" className="btn btn-primary">Start interview now</Link>
            <Link to="/sessions" className="btn btn-secondary">
              View existing sessions
            </Link>
          </div>
        </div>
      </section>

      <SiteFooter />
    </div>
  );
}
