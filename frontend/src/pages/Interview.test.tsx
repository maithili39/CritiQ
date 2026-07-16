import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { useEffect } from "react";
import InterviewPage from "./Interview";
import { AuthProvider } from "@/context/AuthContext";
import { InterviewProvider, useInterview } from "@/context/InterviewContext";
import * as api from "@/lib/api";
import type { Question } from "@/lib/api";

const QUESTION: Question = {
  id: "q1",
  text: "Explain the bias-variance tradeoff",
  topic: "Generalization",
  difficulty: "mid",
  order: 1,
};

/** Seeds interview context the way InterviewSetup would before navigating here. */
function Seed({ question, remaining }: { question: Question; remaining: number }) {
  const { currentQuestion, setCurrentQuestion, setQuestionsRemaining } = useInterview();
  useEffect(() => {
    setCurrentQuestion(question);
    setQuestionsRemaining(remaining);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  // Mount the page only once the context is seeded, else its no-question
  // redirect fires before the seed effect runs.
  return currentQuestion ? <InterviewPage /> : null;
}

function renderInterview(seed?: { question: Question; remaining: number }) {
  return render(
    <MemoryRouter initialEntries={["/interview/sess-1"]}>
      <AuthProvider>
        <InterviewProvider>
          <Routes>
            <Route path="/" element={<div>Home page</div>} />
            <Route
              path="/interview/:id"
              element={seed ? <Seed question={seed.question} remaining={seed.remaining} /> : <InterviewPage />}
            />
            <Route path="/interview/:id/report" element={<div>Report page</div>} />
          </Routes>
        </InterviewProvider>
      </AuthProvider>
    </MemoryRouter>
  );
}

describe("InterviewPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("redirects home when there is no active question (e.g. direct URL hit)", async () => {
    renderInterview();
    await waitFor(() => expect(screen.getByText("Home page")).toBeInTheDocument());
  });

  it("renders the current question from interview context", async () => {
    renderInterview({ question: QUESTION, remaining: 7 });
    await waitFor(() => expect(screen.getByText("Explain the bias-variance tradeoff")).toBeInTheDocument());
  });

  it("submits an answer and shows the live evaluation feedback", async () => {
    const submit = vi.spyOn(api, "submitAnswer").mockResolvedValue({
      answer_id: "a1",
      score: 8.5,
      rationale: "Accurate and well structured.",
      strengths: "Solid fundamentals",
      gaps: "Could mention regularization",
      next_question: { ...QUESTION, id: "q2", text: "Next Q", order: 2 },
      is_complete: false,
      questions_remaining: 6,
    });

    renderInterview({ question: QUESTION, remaining: 7 });
    await waitFor(() => expect(screen.getByText("Explain the bias-variance tradeoff")).toBeInTheDocument());

    await userEvent.type(screen.getByRole("textbox"), "High bias underfits; high variance overfits.");
    await userEvent.click(screen.getByRole("button", { name: /Submit answer/ }));

    await waitFor(() => expect(screen.getByText("8.5")).toBeInTheDocument());
    expect(screen.getByText("Accurate and well structured.")).toBeInTheDocument();
    expect(screen.getByText("Solid fundamentals")).toBeInTheDocument();
    expect(submit).toHaveBeenCalledWith("sess-1", "q1", "High bias underfits; high variance overfits.");
  });

  it("completes the session before navigating to the report on the final answer", async () => {
    vi.spyOn(api, "submitAnswer").mockResolvedValue({
      answer_id: "a1",
      score: 7.0,
      rationale: "Fine.",
      strengths: "s",
      gaps: "g",
      next_question: null,
      is_complete: true,
      questions_remaining: 0,
    });
    const complete = vi.spyOn(api, "completeSession").mockResolvedValue({
      session_id: "sess-1",
      report: {
        summary: "s", overall_score: 7, topic_coverage: {}, strengths: "", gaps: "", recommendation: "yes",
      },
    });

    renderInterview({ question: QUESTION, remaining: 0 });
    await waitFor(() => expect(screen.getByText("Explain the bias-variance tradeoff")).toBeInTheDocument());

    await userEvent.type(screen.getByRole("textbox"), "Final answer.");
    await userEvent.click(screen.getByRole("button", { name: /Submit answer/ }));

    // The report must exist before the report page fetches it — complete first, then navigate.
    await waitFor(() => expect(screen.getByText("Report page")).toBeInTheDocument());
    expect(complete).toHaveBeenCalledWith("sess-1");
  });
});
