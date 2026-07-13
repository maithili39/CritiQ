import { createContext, useContext, useState, ReactNode } from "react";
import { Question, SessionSummary } from "@/lib/api";

interface InterviewState {
  sessionId: string | null;
  candidateName: string;
  role: string;
  currentQuestion: Question | null;
  questionsRemaining: number;
  isComplete: boolean;
  lastScore: number | null;
  lastFeedback: { rationale: string; strengths: string; gaps: string } | null;
  parsedResume: SessionSummary["parsed_resume"] | null;
}

interface InterviewContextValue extends InterviewState {
  setSessionId: (id: string) => void;
  setCandidateName: (name: string) => void;
  setRole: (role: string) => void;
  setCurrentQuestion: (q: Question | null) => void;
  setQuestionsRemaining: (n: number) => void;
  setIsComplete: (v: boolean) => void;
  setLastScore: (s: number | null) => void;
  setLastFeedback: (f: InterviewState["lastFeedback"]) => void;
  setParsedResume: (r: SessionSummary["parsed_resume"]) => void;
  reset: () => void;
}

const defaultState: InterviewState = {
  sessionId: null,
  candidateName: "",
  role: "",
  currentQuestion: null,
  questionsRemaining: 0,
  isComplete: false,
  lastScore: null,
  lastFeedback: null,
  parsedResume: null,
};

const InterviewContext = createContext<InterviewContextValue | null>(null);

export function InterviewProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<InterviewState>(defaultState);

  const update = (patch: Partial<InterviewState>) =>
    setState((s) => ({ ...s, ...patch }));

  return (
    <InterviewContext.Provider
      value={{
        ...state,
        setSessionId: (id) => update({ sessionId: id }),
        setCandidateName: (name) => update({ candidateName: name }),
        setRole: (role) => update({ role }),
        setCurrentQuestion: (q) => update({ currentQuestion: q }),
        setQuestionsRemaining: (n) => update({ questionsRemaining: n }),
        setIsComplete: (v) => update({ isComplete: v }),
        setLastScore: (s) => update({ lastScore: s }),
        setLastFeedback: (f) => update({ lastFeedback: f }),
        setParsedResume: (r) => update({ parsedResume: r }),
        reset: () => setState(defaultState),
      }}
    >
      {children}
    </InterviewContext.Provider>
  );
}

export function useInterview() {
  const ctx = useContext(InterviewContext);
  if (!ctx) throw new Error("useInterview must be used within InterviewProvider");
  return ctx;
}
