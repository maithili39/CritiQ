import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Navbar from "@/components/Navbar";
import SiteFooter from "@/components/SiteFooter";
import { getRoles, RoleInfo } from "@/lib/api";

const FEATURES = [
  {
    icon: "M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12a9 9 0 11-18 0 9 9 0 0118 0m3.6-9h.01",
    title: "Instant Insights",
    desc: "Real-time analysis of candidate responses with AI-powered scoring.",
  },
  {
    icon: "M13 10V3L4 14h7v7l9-11h-7z",
    title: "Structured Process",
    desc: "Consistent evaluation criteria across all candidates, every time.",
  },
  {
    icon: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
    title: "Bias-Free Hiring",
    desc: "Focus on skills and experience, remove subjective decision-making.",
  },
  {
    icon: "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
    title: "Cost Efficient",
    desc: "Save hours of manual screening per hire, without the overhead.",
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
      .then((res) => { if (res.roles?.length) setRoles(res.roles); })
      .catch(() => {});
  }, []);

  return (
    <div className="page-stack">
      <Navbar />

      {/* ── HERO WITH GRADIENT ───────────────────────────────────────────── */}
      <section style={{ background: "linear-gradient(135deg, #09080a 0%, #111014 100%)", paddingTop: "clamp(4rem, 8vw, 6rem)", paddingBottom: "clamp(3.5rem, 7vw, 5.5rem)", position: "relative", overflow: "hidden" }}>
        <div style={{ position: "absolute", top: 0, right: 0, width: "40%", height: "100%", background: "radial-gradient(circle at top right, rgba(239,68,68,0.15) 0%, transparent 70%)", pointerEvents: "none" }} />
        <div className="shell" style={{ position: "relative", zIndex: 1 }}>
          <div style={{ maxWidth: 800, margin: "0 auto", textAlign: "center" }}>
            <div style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem", padding: "0.5rem 1.2rem", borderRadius: 999, border: "1.5px solid rgba(239,68,68,0.35)", background: "rgba(239,68,68,0.1)", marginBottom: "1.5rem" }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#ef4444" }} />
              <span style={{ fontSize: 12, fontWeight: 700, color: "#ef4444", letterSpacing: "0.06em", textTransform: "uppercase", fontFamily: "'Outfit', sans-serif" }}>
                Revolutionizing hiring
              </span>
            </div>

            <h1 style={{ fontFamily: "'Outfit', sans-serif", fontWeight: 900, fontSize: "clamp(42px, 5.5vw, 72px)", lineHeight: 1.1, letterSpacing: "-0.02em", color: "#f0eef4", margin: "0 0 1rem", background: "linear-gradient(135deg, #f0eef4 0%, #ef4444 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text" }}>
              Interview Smarter, Hire Faster
            </h1>

            <p style={{ fontSize: "clamp(17px, 2vw, 22px)", fontWeight: 500, color: "#c4c0cc", maxWidth: 700, margin: "0 auto 2rem", lineHeight: 1.5, fontFamily: "'Inter', sans-serif" }}>
              CritiQ uses AI to run structured candidate interviews, parse resume details, generate role-specific questions, and score responses in real-time. Get a comprehensive hiring report instantly.
            </p>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "1rem", flexWrap: "wrap", marginBottom: "2.5rem" }}>
              <Link to="/interview/setup" style={{ borderRadius: 999, gap: "0.5rem", background: "#ef4444", color: "#ffffff", fontWeight: 700, padding: "1rem 2.5rem", fontSize: 16, display: "inline-flex", alignItems: "center", textDecoration: "none", transition: "all 0.2s", boxShadow: "0 12px 32px rgba(239,68,68,0.3)", fontFamily: "'Outfit', sans-serif" }} onMouseEnter={(e) => e.currentTarget.style.background = "#dc2626"} onMouseLeave={(e) => e.currentTarget.style.background = "#ef4444"}>
                Start Free Session
                <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </Link>
              <Link to="/register" style={{ borderRadius: 999, background: "#16141a", color: "#f0eef4", border: "1.5px solid rgba(255,255,255,0.13)", padding: "1rem 2.2rem", fontSize: 16, display: "inline-flex", alignItems: "center", textDecoration: "none", transition: "all 0.2s", fontWeight: 600, fontFamily: "'Outfit', sans-serif" }} onMouseEnter={(e) => { e.currentTarget.style.background = "#1e1c23"; e.currentTarget.style.borderColor = "rgba(255,255,255,0.2)"; }} onMouseLeave={(e) => { e.currentTarget.style.background = "#16141a"; e.currentTarget.style.borderColor = "rgba(255,255,255,0.13)"; }}>
                Create Account
              </Link>
            </div>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "2rem", flexWrap: "wrap", fontSize: 14, color: "#7a748a" }}>
              {[
                { icon: "M9 12l2 2 4-4", label: "No credit card required" },
                { icon: "M13 10V3L4 14h7v7l9-11h-7z", label: "Instant reports" },
                { icon: "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2", label: "Free forever" },
              ].map((item) => (
                <div key={item.label} style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                  <svg width="16" height="16" fill="none" stroke="#ef4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                    <path d={item.icon} />
                  </svg>
                  {item.label}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── FEATURES SPOTLIGHT ───────────────────────────────────────────── */}
      <section style={{ background: "#111014", paddingTop: "clamp(3.5rem, 7vw, 5.5rem)", paddingBottom: "clamp(3.5rem, 7vw, 5.5rem)", borderTop: "1px solid rgba(255,255,255,0.07)" }}>
        <div className="shell">
          <div style={{ textAlign: "center", marginBottom: "3rem" }}>
            <h2 style={{ fontFamily: "'Outfit', sans-serif", fontWeight: 800, fontSize: "clamp(32px, 3.5vw, 48px)", color: "#f0eef4", margin: 0, lineHeight: 1.2 }}>Why recruiters love CritiQ</h2>
            <p style={{ fontSize: 18, color: "#7a748a", margin: "1rem 0 0", maxWidth: 600, marginLeft: "auto", marginRight: "auto", fontFamily: "'Inter', sans-serif" }}>A smarter way to evaluate every candidate fairly and consistently.</p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "2rem" }}>
            {FEATURES.map((f) => (
              <div key={f.title} style={{ padding: "2rem", borderRadius: "1rem", background: "#16141a", border: "1px solid rgba(255,255,255,0.07)", transition: "all 0.3s", cursor: "pointer" }} onMouseEnter={(e) => { e.currentTarget.style.background = "#1e1c23"; e.currentTarget.style.borderColor = "rgba(239,68,68,0.35)"; e.currentTarget.style.boxShadow = "0 10px 30px rgba(239,68,68,0.2)"; }} onMouseLeave={(e) => { e.currentTarget.style.background = "#16141a"; e.currentTarget.style.borderColor = "rgba(255,255,255,0.07)"; e.currentTarget.style.boxShadow = "none"; }}>
                <svg width="32" height="32" fill="none" stroke="#ef4444" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" style={{ marginBottom: "1rem" }}>
                  <path d={f.icon} />
                </svg>
                <h3 style={{ fontFamily: "'Outfit', sans-serif", fontWeight: 700, fontSize: 18, color: "#f0eef4", margin: "0.5rem 0" }}>{f.title}</h3>
                <p style={{ fontSize: 14, color: "#7a748a", margin: 0, lineHeight: 1.6, fontFamily: "'Inter', sans-serif" }}>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS (SIMPLIFIED) ───────────────────────────────────── */}
      <section style={{ background: "#09080a", paddingTop: "clamp(3.5rem, 7vw, 5.5rem)", paddingBottom: "clamp(3.5rem, 7vw, 5.5rem)", borderTop: "1px solid rgba(255,255,255,0.07)" }}>
        <div className="shell">
          <div style={{ textAlign: "center", marginBottom: "3rem" }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: "#ef4444", textTransform: "uppercase", letterSpacing: "0.08em", fontFamily: "'Outfit', sans-serif" }}>Simple process</span>
            <h2 style={{ fontFamily: "'Outfit', sans-serif", fontWeight: 800, fontSize: "clamp(32px, 3.5vw, 48px)", color: "#f0eef4", margin: "0.5rem 0 0" }}>Four steps to great hires</h2>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "2rem" }}>
            {[
              { num: "1", title: "Upload Resume", desc: "Candidate shares their resume in seconds" },
              { num: "2", title: "Auto Generate", desc: "AI creates role-specific interview questions" },
              { num: "3", title: "Conduct & Score", desc: "Interview happens, answers scored in real-time" },
              { num: "4", title: "Get Report", desc: "Comprehensive hiring report with recommendation" },
            ].map((step) => (
              <div key={step.num} style={{ position: "relative" }}>
                <div style={{ display: "flex", alignItems: "flex-start", gap: "1.2rem" }}>
                  <div style={{ width: 48, height: 48, borderRadius: "50%", background: "linear-gradient(135deg, #ef4444, #dc2626)", display: "flex", alignItems: "center", justifyContent: "center", color: "#ffffff", fontWeight: 800, fontSize: 18, flexShrink: 0, fontFamily: "'Outfit', sans-serif" }}>
                    {step.num}
                  </div>
                  <div>
                    <h3 style={{ fontFamily: "'Outfit', sans-serif", fontWeight: 700, fontSize: 16, color: "#f0eef4", margin: "0 0 0.5rem" }}>{step.title}</h3>
                    <p style={{ fontSize: 14, color: "#7a748a", margin: 0, lineHeight: 1.5, fontFamily: "'Inter', sans-serif" }}>{step.desc}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── ROLE TRACKS ────────────────────────────────────────────────── */}
      <section style={{ background: "#111014", paddingTop: "clamp(3.5rem, 7vw, 5.5rem)", paddingBottom: "clamp(3.5rem, 7vw, 5.5rem)", borderTop: "1px solid rgba(255,255,255,0.07)" }}>
        <div className="shell">
          <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: "3rem", flexWrap: "wrap", gap: "1.5rem" }}>
            <div>
              <span style={{ fontSize: 13, fontWeight: 700, color: "#ef4444", textTransform: "uppercase", letterSpacing: "0.08em", fontFamily: "'Outfit', sans-serif" }}>Available tracks</span>
              <h2 style={{ fontFamily: "'Outfit', sans-serif", fontWeight: 800, fontSize: "clamp(32px, 3.5vw, 48px)", color: "#f0eef4", margin: "0.5rem 0 0" }}>Start with a role track</h2>
            </div>
            <Link to="/interview/setup" style={{ fontSize: 14, fontWeight: 600, color: "#ef4444", textDecoration: "none", transition: "all 0.2s" }} onMouseEnter={(e) => e.currentTarget.style.color = "#dc2626"} onMouseLeave={(e) => e.currentTarget.style.color = "#ef4444"}>
              View all →
            </Link>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "2rem" }}>
            {roles.map((r) => (
              <div key={r.slug} style={{ padding: "2rem", borderRadius: "1.2rem", background: "#16141a", border: "1.5px solid rgba(255,255,255,0.07)", display: "flex", flexDirection: "column", gap: "1rem", transition: "all 0.3s", cursor: "pointer" }} onMouseEnter={(e) => { e.currentTarget.style.borderColor = "rgba(239,68,68,0.35)"; e.currentTarget.style.boxShadow = "0 12px 32px rgba(239,68,68,0.2)"; }} onMouseLeave={(e) => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.07)"; e.currentTarget.style.boxShadow = "none"; }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: "#ef4444", textTransform: "uppercase", letterSpacing: "0.06em", fontFamily: "'Outfit', sans-serif" }}>
                  {r.is_builtin ? "✓ Built-in" : "Custom"}
                </div>
                <div>
                  <h3 style={{ fontFamily: "'Outfit', sans-serif", fontWeight: 700, fontSize: 20, color: "#f0eef4", margin: 0 }}>{r.label}</h3>
                  <p style={{ fontSize: 14, color: "#7a748a", margin: "0.5rem 0 0", lineHeight: 1.5, fontFamily: "'Inter', sans-serif" }}>{r.description}</p>
                </div>
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "#7a748a", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "0.6rem", fontFamily: "'Outfit', sans-serif" }}>Topics</div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                    {r.topics.map((t) => (
                      <span key={t} style={{ fontSize: 12, padding: "0.4rem 0.8rem", borderRadius: 999, background: "#1e1c23", color: "#c4c0cc", border: "1px solid rgba(255,255,255,0.07)", fontFamily: "'Inter', sans-serif" }}>{t}</span>
                    ))}
                  </div>
                </div>
                <Link to="/interview/setup" style={{ marginTop: "auto", fontSize: 14, fontWeight: 600, color: "#ef4444", textDecoration: "none", transition: "all 0.2s" }} onMouseEnter={(e) => e.currentTarget.style.color = "#dc2626"} onMouseLeave={(e) => e.currentTarget.style.color = "#ef4444"}>
                  Launch track →
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FINAL CTA ────────────────────────────────────────────────────── */}
      <section style={{ background: "linear-gradient(135deg, #ef4444, #dc2626)", paddingTop: "clamp(3.5rem, 7vw, 5.5rem)", paddingBottom: "clamp(3.5rem, 7vw, 5.5rem)", position: "relative", overflow: "hidden" }}>
        <div style={{ position: "absolute", inset: 0, background: "url('data:image/svg+xml,%3Csvg width=\"60\" height=\"60\" viewBox=\"0 0 60 60\" xmlns=\"http://www.w3.org/2000/svg\"%3E%3Cg fill=\"none\" fill-rule=\"evenodd\"%3E%3Cg fill=\"%23ffffff\" fill-opacity=\"0.1\"%3E%3Cpath d=\"M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\"/%3E%3C/g%3E%3C/g%3E%3C/svg%3E')", pointerEvents: "none" }} />
        <div className="shell" style={{ position: "relative", zIndex: 1 }}>
          <div style={{ maxWidth: 900, margin: "0 auto", textAlign: "center" }}>
            <h2 style={{ fontFamily: "'Outfit', sans-serif", fontWeight: 800, fontSize: "clamp(36px, 4.5vw, 56px)", color: "#ffffff", margin: 0, lineHeight: 1.2 }}>
              Ready to hire smarter?
            </h2>
            <p style={{ fontSize: "clamp(16px, 1.8vw, 20px)", color: "rgba(255,255,255,0.9)", margin: "1.5rem 0 2.5rem", lineHeight: 1.5, fontFamily: "'Inter', sans-serif" }}>
              Join hundreds of hiring teams using CritiQ for structured, bias-free candidate evaluation. Start your first interview today.
            </p>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "1rem", flexWrap: "wrap" }}>
              <Link to="/interview/setup" style={{ borderRadius: 999, gap: "0.5rem", background: "#ffffff", color: "#ef4444", fontWeight: 700, padding: "1rem 2.5rem", fontSize: 16, display: "inline-flex", alignItems: "center", textDecoration: "none", transition: "all 0.2s", fontFamily: "'Outfit', sans-serif" }} onMouseEnter={(e) => e.currentTarget.style.transform = "translateY(-2px)"} onMouseLeave={(e) => e.currentTarget.style.transform = "translateY(0)"}>
                Start Free Session
                <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </Link>
              <Link to="/register" style={{ borderRadius: 999, background: "rgba(255,255,255,0.15)", color: "#ffffff", border: "1.5px solid rgba(255,255,255,0.3)", padding: "1rem 2.2rem", fontSize: 16, display: "inline-flex", alignItems: "center", textDecoration: "none", transition: "all 0.2s", fontWeight: 600, fontFamily: "'Outfit', sans-serif" }} onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(255,255,255,0.25)"; e.currentTarget.style.borderColor = "rgba(255,255,255,0.4)"; }} onMouseLeave={(e) => { e.currentTarget.style.background = "rgba(255,255,255,0.15)"; e.currentTarget.style.borderColor = "rgba(255,255,255,0.3)"; }}>
                Create Account
              </Link>
            </div>
          </div>
        </div>
      </section>

      <SiteFooter />
    </div>
  );
}
