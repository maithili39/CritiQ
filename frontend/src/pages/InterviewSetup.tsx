import { useState, useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { createSession, startSession, sendInvite, getRoles, RoleInfo } from "@/lib/api";
import { useInterview } from "@/context/InterviewContext";
import Navbar from "@/components/Navbar";
import SiteFooter from "@/components/SiteFooter";

const HOW = [
  { n: "01", title: "Resume parsed",       desc: "We extract your skills, technologies, and experience level automatically." },
  { n: "02", title: "Questions generated", desc: "Questions are created from role-specific knowledge, personalised to your background." },
  { n: "03", title: "Answers evaluated",   desc: "Each response is scored and reviewed in real time with targeted feedback." },
  { n: "04", title: "Report produced",     desc: "A structured hiring report with topic coverage and recommendation is generated." },
];

export default function SetupPage() {
  const navigate = useNavigate();
  const { setCandidateName, setRole, setSessionId, setCurrentQuestion, setQuestionsRemaining, setParsedResume } = useInterview();

  const [roles, setRoles]               = useState<RoleInfo[]>([]);
  const [rolesLoading, setRolesLoading] = useState(true);
  const [name, setName]                 = useState("");
  const [email, setEmail]               = useState("");
  const [selectedRole, setSelectedRole] = useState("");
  const [file, setFile]                 = useState<File | null>(null);
  const [dragging, setDragging]         = useState(false);
  const [loading, setLoading]           = useState(false);
  const [error, setError]               = useState("");
  const [created, setCreated] = useState<{ sessionId: string; inviteUrl: string } | null>(null);
  const [inviteStatus, setInviteStatus] = useState<"idle" | "sending" | "sent" | "copied">("idle");

  useEffect(() => {
    getRoles()
      .then((res) => setRoles(res.roles))
      .catch(() => {
        setError("Failed to load available roles. Please refresh the page and try again.");
      })
      .finally(() => setRolesLoading(false));
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f?.type === "application/pdf") setFile(f);
    else setError("Only PDF files are supported.");
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !selectedRole || !file) {
      setError("Please fill in all fields and upload your resume.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append("candidate_name", name);
      fd.append("role", selectedRole);
      if (email) fd.append("candidate_email", email);
      fd.append("resume", file);
      const result = await createSession(fd);
      setCandidateName(name);
      setRole(selectedRole);
      setSessionId(result.session_id);
      setParsedResume(result.parsed_resume as never);
      setCreated({ sessionId: result.session_id, inviteUrl: result.invite_url });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  const handlePreview = async () => {
    if (!created) return;
    setLoading(true);
    setError("");
    try {
      const started = await startSession(created.sessionId);
      setCurrentQuestion(started.question);
      setQuestionsRemaining(started.questions_remaining);
      navigate(`/interview/${created.sessionId}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start the interview.");
      setLoading(false);
    }
  };

  const handleCopyLink = async () => {
    if (!created) return;
    await navigator.clipboard.writeText(created.inviteUrl);
    setInviteStatus("copied");
    setTimeout(() => setInviteStatus("idle"), 2000);
  };

  const handleSendInvite = async () => {
    if (!created) return;
    setInviteStatus("sending");
    setError("");
    try {
      await sendInvite(created.sessionId);
      setInviteStatus("sent");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to send invite email.");
      setInviteStatus("idle");
    }
  };

  /* ── SESSION CREATED STATE ── */
  if (created) {
    return (
      <div className="page-stack">
        <Navbar />
        <main
          className="section flex-1 flex items-center justify-center"
          style={{ background: "var(--bg-mid)" }}
        >
          <div
            className="card p-8 w-full fade-up"
            style={{ maxWidth: "520px", borderColor: "rgba(245,158,11,0.2)" }}
          >
            {/* success icon */}
            <div
              className="w-12 h-12 rounded-2xl flex items-center justify-center mb-5"
              style={{ background: "rgba(52,211,153,0.12)", border: "1px solid rgba(52,211,153,0.3)" }}
            >
              <svg className="w-6 h-6" style={{ color: "var(--success)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>

            <div
              className="eyebrow mb-2"
              style={{ background: "none", border: "none", padding: 0, color: "var(--success)" }}
            >
              Session created
            </div>
            <h1
              className="font-bold tracking-tight mb-2"
              style={{ fontSize: "26px", fontFamily: "'Outfit', sans-serif", color: "var(--ink)" }}
            >
              Ready to invite {name}
            </h1>
            <p style={{ fontSize: "14px", color: "var(--muted)", lineHeight: 1.7, marginBottom: "1.75rem", fontFamily: "'Inter', sans-serif" }}>
              Send this link to the candidate — no account required. Or preview the interview yourself first.
            </p>

            <div className="mb-5">
              <label className="field-label">Invite link</label>
              <div className="flex gap-2">
                <input
                  readOnly
                  value={created.inviteUrl}
                  className="input px-3 py-2.5 flex-1"
                  style={{ fontSize: "13px" }}
                />
                <button
                  onClick={handleCopyLink}
                  className="btn btn-secondary btn-sm whitespace-nowrap"
                >
                  {inviteStatus === "copied" ? "✓ Copied!" : "Copy"}
                </button>
              </div>
            </div>

            {email && (
              <button
                onClick={handleSendInvite}
                disabled={inviteStatus === "sending" || inviteStatus === "sent"}
                className="btn btn-primary w-full py-3 mb-3"
                style={{ borderRadius: "999px" }}
              >
                {inviteStatus === "sending"
                  ? (<><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full spin" />Sending…</>)
                  : inviteStatus === "sent"
                  ? `✓ Sent to ${email}`
                  : `Email invite to ${email}`}
              </button>
            )}

            {error ? <div className="alert-error mb-3">{error}</div> : null}

            <button
              onClick={handlePreview}
              disabled={loading}
              className="btn btn-secondary w-full py-3"
              style={{ borderRadius: "999px" }}
            >
              {loading ? "Starting…" : "Preview this interview myself →"}
            </button>
          </div>
        </main>
        <SiteFooter />
      </div>
    );
  }

  /* ── SETUP FORM ── */
  return (
    <div className="page-stack">
      <Navbar />

      <main className="section flex-1" style={{ background: "var(--bg-mid)" }}>
        <div className="shell shell-wide grid grid-cols-1 lg:grid-cols-[1.3fr_0.7fr] gap-6">

          {/* ── MAIN FORM CARD ── */}
          <section className="card p-8 fade-up">
            {/* progress bar */}
            <div className="setup-step-bar mb-7">
              <div className="setup-step-dot active" />
              <div className="setup-step-dot" />
              <span
                style={{
                  marginLeft: "0.4rem",
                  fontSize: "12px",
                  color: "var(--muted)",
                  fontFamily: "'Inter', sans-serif",
                }}
              >
                Step 1 of 2
              </span>
            </div>

            <div className="mb-7">
              <div
                className="eyebrow mb-3"
                style={{ background: "none", border: "none", padding: 0 }}
              >
                Interview Setup
              </div>
              <h1
                className="font-bold tracking-tight mb-2"
                style={{
                  fontSize: "clamp(26px, 3.5vw, 34px)",
                  fontFamily: "'Outfit', sans-serif",
                  color: "var(--ink)",
                  letterSpacing: "-0.02em",
                  lineHeight: 1.1,
                }}
              >
                Set up the candidate interview
              </h1>
              <p style={{ fontSize: "15px", color: "var(--muted)", fontFamily: "'Inter', sans-serif" }}>
                Complete the details below to generate a structured interview session.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="flex flex-col gap-6">
              {/* name */}
              <div>
                <label className="field-label" htmlFor="setup-name">Candidate full name</label>
                <input
                  id="setup-name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Jane Smith"
                  className="input px-4 py-3"
                />
              </div>

              {/* email */}
              <div>
                <label className="field-label" htmlFor="setup-email">
                  Candidate email
                  <span style={{ color: "var(--muted)", fontWeight: 400, marginLeft: "0.4rem", fontSize: "12px" }}>
                    optional
                  </span>
                </label>
                <input
                  id="setup-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="jane@company.com"
                  className="input px-4 py-3"
                />
              </div>

              {/* role selection */}
              <div>
                <label className="field-label">Target role</label>
                {rolesLoading ? (
                  <div className="flex items-center gap-2 py-5" style={{ color: "var(--muted)", fontSize: "14px", fontFamily: "'Inter', sans-serif" }}>
                    <span className="w-4 h-4 border-2 border-t-transparent rounded-full spin" style={{ borderColor: "var(--brand)" }} />
                    Loading roles…
                  </div>
                ) : (
                  <div className="grid grid-cols-1 gap-3">
                    {roles.map((r) => {
                      const active = selectedRole === r.slug;
                      return (
                        <button
                          key={r.slug}
                          type="button"
                          onClick={() => setSelectedRole(r.slug)}
                          className="text-left rounded-xl transition-all"
                          style={{
                            padding: "1rem 1.25rem",
                            border: active ? "1.5px solid var(--brand)" : "1.5px solid var(--border-strong)",
                            background: active ? "rgba(245,158,11,0.07)" : "var(--surface-alt)",
                            boxShadow: active ? "var(--ring)" : "none",
                          }}
                        >
                          <div className="flex items-center justify-between mb-1.5">
                            <div className="flex items-center gap-2">
                              <div
                                className="font-semibold"
                                style={{ fontSize: "15px", color: active ? "var(--ink)" : "var(--ink-2)", fontFamily: "'Inter', sans-serif" }}
                              >
                                {r.label}
                              </div>
                              {!r.is_builtin && (
                                <span
                                  className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded"
                                  style={{ background: "var(--accent-soft)", color: "var(--accent)" }}
                                >
                                  Custom
                                </span>
                              )}
                            </div>
                            {active && (
                              <div
                                className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0"
                                style={{ background: "var(--brand)" }}
                              >
                                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="#fff" strokeWidth={3}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                </svg>
                              </div>
                            )}
                          </div>
                          <p style={{ fontSize: "13px", color: "var(--muted)", marginBottom: r.topics.length > 0 ? "0.75rem" : 0, fontFamily: "'Inter', sans-serif" }}>
                            {r.description}
                          </p>
                          {r.topics.length > 0 && (
                            <div className="flex flex-wrap gap-1.5">
                              {r.topics.map((t) => (
                                <span key={t} className="badge">{t}</span>
                              ))}
                            </div>
                          )}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* resume upload */}
              <div>
                <label className="field-label">Resume file</label>
                <div
                  onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={onDrop}
                  onClick={() => document.getElementById("resume-input")?.click()}
                  className="rounded-2xl cursor-pointer transition-all"
                  style={{
                    padding: "2.5rem 2rem",
                    border: `1.8px dashed ${dragging ? "var(--brand)" : file ? "rgba(52,211,153,0.5)" : "var(--border-strong)"}`,
                    background: dragging
                      ? "rgba(245,158,11,0.05)"
                      : file
                      ? "rgba(52,211,153,0.05)"
                      : "var(--surface-alt)",
                    textAlign: "center",
                  }}
                >
                  <input
                    id="resume-input"
                    type="file"
                    accept=".pdf"
                    className="hidden"
                    onChange={(e) => { const f = e.target.files?.[0]; if (f) setFile(f); }}
                  />
                  {file ? (
                    <div>
                      <div
                        className="w-10 h-10 rounded-xl flex items-center justify-center mx-auto mb-3"
                        style={{ background: "rgba(52,211,153,0.12)", border: "1px solid rgba(52,211,153,0.3)" }}
                      >
                        <svg className="w-5 h-5" style={{ color: "var(--success)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                      <div className="font-semibold mb-1" style={{ color: "var(--ink)", fontFamily: "'Inter', sans-serif" }}>{file.name}</div>
                      <div style={{ color: "var(--muted)", fontSize: "13px", fontFamily: "'Inter', sans-serif" }}>{(file.size / 1024).toFixed(0)} KB · PDF</div>
                    </div>
                  ) : (
                    <div>
                      <div
                        className="w-10 h-10 rounded-xl flex items-center justify-center mx-auto mb-3"
                        style={{ background: "var(--brand-soft)", border: "1px solid var(--brand-line)" }}
                      >
                        <svg className="w-5 h-5" style={{ color: "var(--brand)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                        </svg>
                      </div>
                      <div className="font-semibold mb-1" style={{ color: "var(--ink)", fontFamily: "'Inter', sans-serif" }}>
                        Drop PDF here or click to browse
                      </div>
                      <div style={{ color: "var(--muted)", fontSize: "13px", fontFamily: "'Inter', sans-serif" }}>
                        Maximum upload size: 5 MB
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {error ? <div className="alert-error">{error}</div> : null}

              <button
                id="create-session-btn"
                type="submit"
                disabled={loading}
                className="btn btn-primary py-3.5 justify-center"
                style={{ borderRadius: "999px", fontSize: "15px" }}
              >
                {loading ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full spin" />
                    Reading candidate profile…
                  </>
                ) : "Create session →"}
              </button>
            </form>
          </section>

          {/* ── RIGHT SIDEBAR ── */}
          <aside
            className="card p-6 fade-up delay-1 self-start"
            style={{ position: "sticky", top: "88px" }}
          >
            <h3
              className="font-bold mb-5"
              style={{ fontSize: "18px", fontFamily: "'Outfit', sans-serif", color: "var(--ink)" }}
            >
              Interview flow
            </h3>
            <div className="flex flex-col gap-3">
              {HOW.map((item) => (
                <div key={item.n} className="setup-flow-item">
                  <div className="setup-flow-num">{parseInt(item.n)}</div>
                  <div>
                    <div
                      className="font-semibold mb-1"
                      style={{ fontSize: "14px", color: "var(--ink)", fontFamily: "'Inter', sans-serif" }}
                    >
                      {item.title}
                    </div>
                    <p style={{ fontSize: "13px", color: "var(--muted)", lineHeight: 1.6, fontFamily: "'Inter', sans-serif" }}>
                      {item.desc}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            {/* tip */}
            <div
              className="mt-5 p-4 rounded-xl"
              style={{
                background: "var(--brand-soft)",
                border: "1px solid var(--brand-line)",
              }}
            >
              <div
                className="font-semibold mb-1"
                style={{ fontSize: "13px", color: "var(--brand)", fontFamily: "'Inter', sans-serif" }}
              >
                💡 Tip
              </div>
              <p style={{ fontSize: "12px", color: "var(--muted)", lineHeight: 1.6, fontFamily: "'Inter', sans-serif" }}>
                Adding the candidate's email lets you send them a direct invite link with one click after setup.
              </p>
            </div>
          </aside>

        </div>
      </main>

      <SiteFooter />
    </div>
  );
}
