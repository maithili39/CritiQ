import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import {
  getCandidateSession,
  startCandidateSession,
  submitCandidateAnswer,
  completeCandidateSession,
  CandidateQuestion,
  CandidateAnswerTelemetry,
} from "@/lib/api";
import Navbar from "@/components/Navbar";

const ROLE_LABELS: Record<string, string> = {
  ai_ml: "AI / ML Engineer",
  data_science: "Data Scientist",
};

const POLL_INTERVAL_MS = 1500;

// ----------- Anti-cheating constants -----------
const MAX_TAB_VIOLATIONS = 1;   // 2nd tab switch terminates the interview
const MAX_FS_VIOLATIONS  = 1;   // 2nd fullscreen exit terminates the interview

type Stage = "loading" | "rules" | "intro" | "active" | "submitting" | "grading" | "done" | "error";

// ----------- Helpers -----------



async function captureWebcamSnapshot(
  stream: MediaStream | null
): Promise<string | undefined> {
  if (!stream) return undefined;
  const track = stream.getVideoTracks()[0];
  if (!track || track.readyState !== "live") return undefined;

  const ImageCaptureClass = (window as any).ImageCapture as (new (track: MediaStreamTrack) => any) | undefined;
  if (!ImageCaptureClass) {
    // Fallback: draw to canvas from a temporary video element
    const video = document.createElement("video");
    video.srcObject = stream;
    video.autoplay = true;
    await new Promise<void>((res) => { video.onloadeddata = () => res(); });
    const canvas = document.createElement("canvas");
    canvas.width  = 320;
    canvas.height = 240;
    canvas.getContext("2d")?.drawImage(video, 0, 0, 320, 240);
    video.srcObject = null;
    return canvas.toDataURL("image/jpeg", 0.4).split(",")[1]; // strip data URI prefix
  }

  const imageCapture = new ImageCaptureClass(track);
  try {
    const blob: Blob = await imageCapture.takePhoto({ imageWidth: 320 });
    return new Promise<string>((res, rej) => {
      const reader = new FileReader();
      reader.onload = () => {
        const b64 = (reader.result as string).split(",")[1];
        res(b64);
      };
      reader.onerror = rej;
      reader.readAsDataURL(blob);
    });
  } catch {
    return undefined;
  }
}

export default function CandidateInterview() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [stage, setStage] = useState<Stage>("loading");
  const [error, setError] = useState("");
  const [candidateName, setCandidateName] = useState("");
  const [role, setRole] = useState("");
  const [maxQuestions, setMaxQuestions] = useState(0);
  const [question, setQuestion] = useState<CandidateQuestion | null>(null);
  const [answer, setAnswer] = useState("");
  const [pasteWarning, setPasteWarning] = useState(false);
  const [fsWarning, setFsWarning]       = useState(false);
  const [tabWarning, setTabWarning]     = useState(false);
  const [violationMsg, setViolationMsg] = useState("");

  // Anti-cheating state refs (avoid stale closures in event handlers)
  const pollRef          = useRef<ReturnType<typeof setInterval> | null>(null);
  const cameraStream     = useRef<MediaStream | null>(null);
  const pasteDetected    = useRef(false);
  const tabSwitchCount   = useRef(0);
  const tabViolations    = useRef(0);     // strikes (each switch = 1 strike for now)
  const fsViolations     = useRef(0);
  const questionStartRef = useRef<number>(Date.now());
  const stageRef         = useRef<Stage>("loading");

  // Keep stageRef in sync so event handlers can read latest value
  useEffect(() => { stageRef.current = stage; }, [stage]);

  // Cleanup on unmount
  useEffect(() => () => {
    if (pollRef.current) clearInterval(pollRef.current);
    cameraStream.current?.getTracks().forEach((t) => t.stop());
  }, []);

  // ----------- Tab-switch / visibility detection -----------

  const handleTerminate = useCallback(async (reason: string) => {
    setViolationMsg(reason);
    setStage("done");
    if (sessionId) {
      try { await completeCandidateSession(sessionId, token); } catch { /* best-effort */ }
    }
  }, [sessionId, token]);

  const handleVisibilityChange = useCallback(() => {
    if (document.hidden && stageRef.current === "active") {
      tabSwitchCount.current += 1;
      tabViolations.current  += 1;
      if (tabViolations.current > MAX_TAB_VIOLATIONS) {
        handleTerminate("Interview terminated: tab switching detected twice.");
      } else {
        setTabWarning(true);
        setTimeout(() => setTabWarning(false), 4000);
      }
    }
  }, [handleTerminate]);

  // ----------- Fullscreen management -----------

  const requestFullscreen = useCallback(async () => {
    try {
      await document.documentElement.requestFullscreen();
    } catch { /* browser may deny silently */ }
  }, []);

  const handleFullscreenChange = useCallback(() => {
    if (!document.fullscreenElement && stageRef.current === "active") {
      fsViolations.current += 1;
      if (fsViolations.current > MAX_FS_VIOLATIONS) {
        handleTerminate("Interview terminated: fullscreen exited twice.");
      } else {
        setFsWarning(true);
        // Attempt to re-enter fullscreen
        requestFullscreen().then(() => {
          setTimeout(() => setFsWarning(false), 5000);
        });
      }
    }
  }, [handleTerminate, requestFullscreen]);

  useEffect(() => {
    document.addEventListener("visibilitychange", handleVisibilityChange);
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
    };
  }, [handleVisibilityChange, handleFullscreenChange]);

  // ----------- Camera setup -----------

  const initCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      cameraStream.current = stream;
    } catch {
      // Camera denied or unavailable — graceful degradation, not a blocker
      cameraStream.current = null;
    }
  }, []);

  // ----------- Polling -----------

  const pollUntilDone = useCallback((submittedQuestionOrder: number) => {
    if (!sessionId) return;
    pollRef.current = setInterval(async () => {
      try {
        const s = await getCandidateSession(sessionId, token);
        if (s.is_processing) return;

        if (pollRef.current) clearInterval(pollRef.current);

        if (s.processing_error) {
          setError("Something went wrong grading your answer. Please contact support — your answer was saved.");
          setStage("error");
          return;
        }
        if (s.status === "completed") {
          setStage("done");
          return;
        }
        if (s.question && s.question.order > submittedQuestionOrder) {
          setQuestion(s.question);
          setAnswer("");
          pasteDetected.current = false;
          questionStartRef.current = Date.now();
          setStage("active");
          return;
        }
        setStage("active");
      } catch (err: unknown) {
        if (pollRef.current) clearInterval(pollRef.current);
        setError(err instanceof Error ? err.message : "Lost connection while waiting for your result.");
        setStage("error");
      }
    }, POLL_INTERVAL_MS);
  }, [sessionId, token]);

  // ----------- Load session -----------

  const loadSession = useCallback(async () => {
    if (!sessionId || !token) {
      setError("This invite link is missing or invalid.");
      setStage("error");
      return;
    }
    try {
      const s = await getCandidateSession(sessionId, token);
      setCandidateName(s.candidate_name);
      setRole(s.role);
      setMaxQuestions(s.max_questions);
      if (s.status === "completed") {
        setStage("done");
      } else if (s.status === "active" && s.question) {
        setQuestion(s.question);
        if (s.is_processing) {
          setStage("grading");
          pollUntilDone(s.question.order);
        } else {
          // Returning candidate: show rules before resuming
          setStage("rules");
        }
      } else {
        setStage("rules");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "This invite link is no longer valid.");
      setStage("error");
    }
  }, [sessionId, token, pollUntilDone]);

  useEffect(() => { loadSession(); }, [loadSession]);

  // ----------- Handlers -----------

  const handleAcceptRules = async () => {
    await initCamera();
    await requestFullscreen();
    setStage("intro");
  };

  const handleStart = async () => {
    if (!sessionId) return;
    setStage("loading");
    try {
      const started = await startCandidateSession(sessionId, token);
      setQuestion(started.question);
      pasteDetected.current = false;
      questionStartRef.current = Date.now();
      setStage("active");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start the interview.");
      setStage("error");
    }
  };

  // Starts fresh when a question already exists (returning candidate resume)
  const handleStartFromRules = async () => {
    if (question) {
      // Already in active state — just resume
      await initCamera();
      await requestFullscreen();
      pasteDetected.current = false;
      questionStartRef.current = Date.now();
      setStage("active");
    } else {
      await handleAcceptRules();
    }
  };

  const handleSubmit = async () => {
    if (!sessionId || !question || !answer.trim()) return;
    setStage("submitting");
    setError("");

    const responseMs = Date.now() - questionStartRef.current;
    const snapshot   = await captureWebcamSnapshot(cameraStream.current);

    const telemetry: CandidateAnswerTelemetry = {
      response_time_ms: responseMs,
      paste_detected:   pasteDetected.current,
      tab_switch_count: tabSwitchCount.current,
      camera_snapshot:  snapshot,
    };

    try {
      await submitCandidateAnswer(sessionId, token, question.id, answer, telemetry);
      setStage("grading");
      pollUntilDone(question.order);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to submit your answer.");
      setStage("active");
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    pasteDetected.current = true;
    setPasteWarning(true);
    setTimeout(() => setPasteWarning(false), 3500);
  };

  const handleCopy = (e: React.ClipboardEvent) => {
    e.preventDefault();
  };

  // ============================================================
  // Renders
  // ============================================================

  if (stage === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg-soft)" }}>
        <span className="w-8 h-8 border-2 rounded-full spin" style={{ borderColor: "#e5e7eb", borderTopColor: "#0d9488" }} />
      </div>
    );
  }

  if (stage === "error") {
    return (
      <div className="page-stack" style={{ background: "var(--bg-soft)" }}>
        <Navbar />
        <main className="section flex-1 flex items-center justify-center">
          <div className="card p-8 max-w-md text-center">
            <h1 className="text-[22px] font-bold mb-3">Something went wrong</h1>
            <p className="muted text-[14px]">{error}</p>
          </div>
        </main>
      </div>
    );
  }

  // Rules / pre-exam briefing
  if (stage === "rules") {
    const RULES = [
      { icon: "⛶", label: "Fullscreen required", desc: "The interview runs in fullscreen. Exiting twice will terminate the session." },
      { icon: "🚫", label: "No tab switching", desc: "Switching tabs or windows is detected. Two violations will end your interview." },
      { icon: "📋", label: "No copy & paste", desc: "Copying or pasting text in the answer box is blocked and flagged." },
      { icon: "📷", label: "Camera access", desc: "We capture a single photo at each answer submission to verify your identity." },
      { icon: "⏱", label: "Response timing", desc: "Time taken per answer is recorded as part of the integrity audit trail." },
    ];
    return (
      <div className="page-stack" style={{ background: "var(--bg-soft)" }}>
        <Navbar />
        <main className="section flex-1 flex items-center justify-center">
          <div className="card p-8 max-w-xl w-full fade-up">
            <div
              className="inline-flex items-center gap-2 text-[11px] font-bold uppercase tracking-widest mb-4 px-3 py-1.5 rounded-full"
              style={{ background: "rgba(239,68,68,0.08)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.2)" }}
            >
              🔒 Proctored Assessment
            </div>
            <h1 className="text-[26px] font-bold tracking-tight mb-2">Exam Rules</h1>
            <p className="muted text-[14px] mb-6">
              This is a proctored technical interview. Read the rules carefully before starting.
            </p>

            <div className="flex flex-col gap-3 mb-7">
              {RULES.map((r) => (
                <div
                  key={r.label}
                  className="flex items-start gap-3 p-4 rounded-xl"
                  style={{ background: "#f9fafb", border: "1px solid #e5e7eb" }}
                >
                  <span className="text-[20px] mt-0.5 flex-shrink-0">{r.icon}</span>
                  <div>
                    <div className="text-[13px] font-semibold mb-0.5">{r.label}</div>
                    <p className="text-[12px] muted leading-relaxed">{r.desc}</p>
                  </div>
                </div>
              ))}
            </div>

            <button
              onClick={question ? handleStartFromRules : handleAcceptRules}
              className="btn btn-primary w-full py-3.5 text-[15px]"
            >
              I understand — {question ? "Resume" : "Start"} the interview
            </button>
          </div>
        </main>
      </div>
    );
  }

  if (stage === "intro") {
    return (
      <div className="page-stack" style={{ background: "var(--bg-soft)" }}>
        <Navbar />
        <main className="section flex-1 flex items-center justify-center">
          <div className="card p-8 max-w-lg text-center fade-up">
            <div className="eyebrow mb-3">You've been invited</div>
            <h1 className="text-[28px] font-bold tracking-tight mb-3">Hi {candidateName}</h1>
            <p className="muted text-[15px] leading-relaxed mb-6">
              You're being screened for a <strong>{ROLE_LABELS[role] || role}</strong> role.
              This is a proctored technical interview — you'll answer {maxQuestions} questions
              generated from your resume, one at a time.
            </p>
            <button onClick={handleStart} className="btn btn-primary px-8 py-3">
              Start the interview
            </button>
          </div>
        </main>
      </div>
    );
  }

  if (stage === "done") {
    const terminated = violationMsg !== "";
    return (
      <div className="page-stack" style={{ background: "var(--bg-soft)" }}>
        <Navbar />
        <main className="section flex-1 flex items-center justify-center">
          <div className="card p-8 max-w-md text-center fade-up">
            <div
              className="w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-5"
              style={{ background: terminated ? "rgba(239,68,68,0.1)" : "rgba(16,185,129,0.1)" }}
            >
              {terminated ? (
                <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="#ef4444" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="#16a34a" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              )}
            </div>
            <h1 className="text-[22px] font-bold mb-3">
              {terminated ? "Interview Terminated" : "All done, thank you"}
            </h1>
            <p className="muted text-[14px] leading-relaxed">
              {terminated
                ? violationMsg
                : "Your responses have been submitted for review. The hiring team will follow up with next steps."}
            </p>
          </div>
        </main>
      </div>
    );
  }

  // active / submitting / grading
  return (
    <div className="page-stack" style={{ background: "var(--bg-soft)", position: "relative" }}>
      <Navbar />

      {/* ---- Violation overlays ---- */}
      {(tabWarning || fsWarning) && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center"
          style={{ background: "rgba(0,0,0,0.75)", backdropFilter: "blur(4px)" }}
        >
          <div className="card p-8 max-w-md text-center fade-up" style={{ border: "2px solid #ef4444" }}>
            <div className="text-[40px] mb-3">⚠️</div>
            <h2 className="text-[22px] font-bold mb-3" style={{ color: "#ef4444" }}>
              {tabWarning ? "Tab Switch Detected" : "Fullscreen Exited"}
            </h2>
            <p className="muted text-[14px] leading-relaxed mb-2">
              {tabWarning
                ? "Switching tabs is not allowed. This is your first warning. A second violation will terminate the interview."
                : "You exited fullscreen mode. Re-entering now. A second violation will terminate the interview."}
            </p>
            <p className="text-[12px] font-semibold" style={{ color: "#ef4444" }}>
              ⚠️ Warning 1 of 2
            </p>
          </div>
        </div>
      )}

      {pasteWarning && (
        <div
          className="fixed top-5 left-1/2 z-50 -translate-x-1/2 px-5 py-3 rounded-xl shadow-lg text-[13px] font-semibold fade-in"
          style={{ background: "#fef2f2", border: "1px solid #fecaca", color: "#dc2626" }}
        >
          🚫 Paste is disabled during the exam — this action has been flagged.
        </div>
      )}

      <main className="interview-grid">
        {question && (
          <div className="card p-7 fade-up">
            <div className="flex items-center gap-2 mb-5 flex-wrap">
              {question.topic && <span className="badge badge-brand">{question.topic}</span>}
              <span className="ml-auto text-[12px] font-medium muted">
                Question {question.order} of {maxQuestions}
              </span>
              {/* Live response-time indicator */}
              <span className="text-[11px] muted" id="elapsed-timer" />
            </div>
            <p className="text-[20px] leading-relaxed font-semibold">{question.text}</p>
          </div>
        )}

        <div className="flex flex-col gap-3 fade-up delay-1">
          <label className="field-label">Your answer</label>
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            onPaste={handlePaste}
            onCopy={handleCopy}
            onCut={handleCopy}
            onContextMenu={(e) => e.preventDefault()}
            placeholder="Type your answer here..."
            rows={8}
            disabled={stage !== "active"}
            className="input px-4 py-3.5 text-[14px] resize-none"
            style={{ borderRadius: "12px", lineHeight: "1.7", userSelect: "none" }}
          />

          {error && <div className="alert-error fade-in">{error}</div>}

          <div className="flex items-center justify-between pt-1">
            <span className="text-[12px] muted">
              {stage === "grading"
                ? "Grading your answer and preparing the next question…"
                : answer.length > 0 ? `${answer.length} characters` : "Type your answer — copy/paste is disabled"}
            </span>
            <button
              onClick={handleSubmit}
              disabled={stage !== "active" || !answer.trim()}
              className="btn btn-primary text-[14px] px-6 py-2.5"
            >
              {stage === "submitting" || stage === "grading" ? (
                <>
                  <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full spin" />
                  {stage === "grading" ? "Grading..." : "Submitting..."}
                </>
              ) : "Submit answer"}
            </button>
          </div>

          {/* Integrity status bar */}
          <div
            className="flex items-center gap-4 pt-2 text-[11px] muted border-t"
            style={{ borderColor: "#f3f4f6" }}
          >
            <span title="Camera status">
              📷 {cameraStream.current ? "Camera active" : "Camera unavailable"}
            </span>
            <span title="Tab violations">
              🔍 Tab switches: {tabSwitchCount.current}
            </span>
            <span title="Fullscreen status">
              ⛶ {document.fullscreenElement ? "Fullscreen" : "Windowed"}
            </span>
          </div>
        </div>
      </main>
    </div>
  );
}
