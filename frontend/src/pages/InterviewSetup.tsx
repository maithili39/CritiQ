import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { createSession, startSession, sendInvite } from "@/lib/api";
import { useInterview } from "@/context/InterviewContext";
import Navbar from "@/components/Navbar";
import SiteFooter from "@/components/SiteFooter";

const ROLES = [
  {
    id: "ai_ml",
    label: "AI / ML Engineer",
    desc: "Machine learning, deep learning, model development and deployment",
    topics: ["Neural Nets", "MLOps", "Transformers", "Model Eval"],
  },
  {
    id: "data_science",
    label: "Data Scientist",
    desc: "Applied ML, statistical modeling, data analysis and visualization",
    topics: ["Statistics", "EDA", "Regression", "A/B Testing"],
  },
];

const HOW = [
  { n: "01", title: "Resume parsed",       desc: "We extract your skills, technologies, and experience level automatically." },
  { n: "02", title: "Questions generated", desc: "Questions are created from role-specific ML knowledge, personalised to your background." },
  { n: "03", title: "Answers evaluated",   desc: "Each response is scored and reviewed in real time with targeted feedback." },
  { n: "04", title: "Report produced",     desc: "A structured hiring report with topic coverage and recommendation is generated." },
];

export default function SetupPage() {
  const navigate = useNavigate();
  const { setCandidateName, setRole, setSessionId, setCurrentQuestion, setQuestionsRemaining, setParsedResume } = useInterview();

  const [name, setName]                 = useState("");
  const [email, setEmail]               = useState("");
  const [selectedRole, setSelectedRole] = useState("");
  const [file, setFile]                 = useState<File | null>(null);
  const [dragging, setDragging]         = useState(false);
  const [loading, setLoading]           = useState(false);
  const [error, setError]               = useState("");
  const [created, setCreated] = useState<{ sessionId: string; inviteUrl: string } | null>(null);
  const [inviteStatus, setInviteStatus] = useState<"idle" | "sending" | "sent" | "copied">("idle");

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f?.type === "application/pdf") setFile(f);
    else setError("Only PDF files are supported.");
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !selectedRole || !file) { setError("Please fill in all fields and upload your resume."); return; }
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

  if (created) {
    return (
      <div className="page-stack">
        <Navbar />
        <main className="section">
          <div className="shell flex items-center justify-center">
            <div className="card p-8 max-w-lg w-full fade-up">
              <div className="eyebrow mb-3">Session created</div>
              <h1 className="text-[26px] font-bold tracking-tight mb-2">Ready to invite {name}</h1>
              <p className="muted text-[14px] leading-relaxed mb-6">
                Send this link to the candidate to let them complete the interview on their own
                time — no account required. Or preview the interview yourself first.
              </p>

              <label className="field-label">Invite link</label>
              <div className="flex gap-2 mb-4">
                <input readOnly value={created.inviteUrl} className="input px-3 py-2.5 text-[13px] flex-1" />
                <button onClick={handleCopyLink} className="btn btn-secondary btn-sm whitespace-nowrap">
                  {inviteStatus === "copied" ? "Copied!" : "Copy"}
                </button>
              </div>

              {email && (
                <button
                  onClick={handleSendInvite}
                  disabled={inviteStatus === "sending" || inviteStatus === "sent"}
                  className="btn btn-primary w-full py-3 mb-3"
                >
                  {inviteStatus === "sending" ? "Sending..." : inviteStatus === "sent" ? `Sent to ${email}` : `Email invite to ${email}`}
                </button>
              )}

              {error ? <div className="alert-error mb-3">{error}</div> : null}

              <button onClick={handlePreview} disabled={loading} className="btn btn-secondary w-full py-3">
                {loading ? "Starting..." : "Preview this interview myself"}
              </button>
            </div>
          </div>
        </main>
        <SiteFooter />
      </div>
    );
  }

  return (
    <div className="page-stack">
      <Navbar />

      <main className="section">
        <div className="shell shell-wide grid grid-cols-1 lg:grid-cols-[1.2fr_0.8fr] gap-6">
          <section className="card p-7 fade-up">
            <div className="mb-6">
              <div className="eyebrow mb-3">Step 1 of 2</div>
              <h1 className="text-[34px] font-bold tracking-tight mb-2" style={{ lineHeight: 1.08 }}>Set up the candidate interview</h1>
              <p className="muted text-[15px]">Complete the details below to generate a structured interview session.</p>
            </div>

            <form onSubmit={handleSubmit} className="flex flex-col gap-5">
              <div>
                <label className="field-label">Candidate full name</label>
                <input type="text" value={name} onChange={e => setName(e.target.value)} placeholder="Jane Smith" className="input px-4 py-2.5" />
              </div>

              <div>
                <label className="field-label">Candidate email <span className="muted text-[12px]">optional</span></label>
                <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="jane@company.com" className="input px-4 py-2.5" />
              </div>

              <div>
                <label className="field-label mb-2">Target role</label>
                <div className="grid grid-cols-1 gap-2.5">
                  {ROLES.map((r) => {
                    const active = selectedRole === r.id;
                    return (
                      <button
                        key={r.id}
                        type="button"
                        onClick={() => setSelectedRole(r.id)}
                        className="text-left p-4 rounded-xl transition-all"
                        style={{
                          border: active ? "1.5px solid var(--brand)" : "1.5px solid var(--border)",
                          background: active ? "var(--brand-soft)" : "#fff",
                          boxShadow: active ? "0 0 0 3px rgba(234,9,84,0.09)" : "none",
                        }}
                      >
                        <div className="text-[15px] font-semibold mb-1">{r.label}</div>
                        <p className="text-[13px] muted">{r.desc}</p>
                        <div className="flex flex-wrap gap-1.5 mt-3">
                          {r.topics.map((t) => <span key={t} className="badge">{t}</span>)}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <label className="field-label">Resume file</label>
                <div
                  onDragOver={e => { e.preventDefault(); setDragging(true); }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={onDrop}
                  onClick={() => document.getElementById("resume-input")?.click()}
                  className="p-7 rounded-xl cursor-pointer"
                  style={{
                    border: `1.8px dashed ${dragging || file ? "var(--brand)" : "var(--border-strong)"}`,
                    background: dragging || file ? "var(--brand-soft)" : "var(--surface-alt)",
                    textAlign: "center",
                  }}
                >
                  <input
                    id="resume-input"
                    type="file"
                    accept=".pdf"
                    className="hidden"
                    onChange={e => { const f = e.target.files?.[0]; if (f) setFile(f); }}
                  />
                  {file ? (
                    <div>
                      <div className="text-[15px] font-semibold mb-1">{file.name}</div>
                      <div className="muted text-[13px]">{(file.size / 1024).toFixed(0)} KB selected</div>
                    </div>
                  ) : (
                    <div>
                      <div className="text-[15px] font-semibold">Drop PDF here or click to browse</div>
                      <div className="muted text-[13px] mt-1">Maximum upload size: 5 MB</div>
                    </div>
                  )}
                </div>
              </div>

              {error ? <div className="alert-error">{error}</div> : null}

              <button type="submit" disabled={loading} className="btn btn-primary py-3.5 justify-center">
                {loading ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full spin" />
                    Reading candidate profile...
                  </>
                ) : "Create session"}
              </button>
            </form>
          </section>

          <aside className="card p-6 fade-up delay-1" style={{ background: "linear-gradient(180deg,#ffffff 0%, #fafbff 100%)" }}>
            <h3 className="text-[20px] font-bold mb-5">Interview flow</h3>
            <div className="flex flex-col gap-4">
              {HOW.map((item) => (
                <div key={item.n} className="p-4 rounded-xl" style={{ border: "1px solid var(--border)", background: "#fff" }}>
                  <div className="eyebrow mb-1">{item.n}</div>
                  <div className="text-[14px] font-semibold mb-1">{item.title}</div>
                  <p className="text-[13px] muted leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>
          </aside>
        </div>
      </main>

      <SiteFooter />
    </div>
  );
}
