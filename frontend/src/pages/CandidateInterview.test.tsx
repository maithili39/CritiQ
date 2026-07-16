import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import CandidateInterview from "./CandidateInterview";
import { AuthProvider } from "@/context/AuthContext";
import * as api from "@/lib/api";

type CandidateSession = Awaited<ReturnType<typeof api.getCandidateSession>>;

function makeCandidateSession(overrides: Partial<CandidateSession> = {}): CandidateSession {
  return {
    session_id: "sess-1",
    candidate_name: "Jane Doe",
    role: "ai_ml",
    status: "created",
    question: null,
    questions_answered: 0,
    max_questions: 8,
    is_processing: false,
    processing_error: null,
    ...overrides,
  };
}

function renderCandidate(path = "/candidate/sess-1?token=tok123") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <Routes>
          <Route path="/candidate/:sessionId" element={<CandidateInterview />} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>
  );
}

describe("CandidateInterview", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("rejects a link without a token before calling the API", async () => {
    const get = vi.spyOn(api, "getCandidateSession");
    renderCandidate("/candidate/sess-1"); // no ?token=
    await waitFor(() => expect(screen.getByText("This invite link is missing or invalid.")).toBeInTheDocument());
    expect(get).not.toHaveBeenCalled();
  });

  it("shows the proctoring rules before a new interview starts", async () => {
    vi.spyOn(api, "getCandidateSession").mockResolvedValue(makeCandidateSession());
    renderCandidate();
    await waitFor(() => expect(screen.getByText("Exam Rules")).toBeInTheDocument());
    expect(screen.getByText("No tab switching")).toBeInTheDocument();
    expect(screen.getByText("No copy & paste")).toBeInTheDocument();
  });

  it("moves from rules to the intro after acceptance, then starts the interview", async () => {
    vi.spyOn(api, "getCandidateSession").mockResolvedValue(makeCandidateSession());
    vi.spyOn(api, "startCandidateSession").mockResolvedValue({
      session_id: "sess-1",
      status: "active",
      question: { id: "q1", text: "Explain gradient descent", topic: "Optimization", difficulty: "mid", order: 1 },
    });

    renderCandidate();
    await waitFor(() => expect(screen.getByText("Exam Rules")).toBeInTheDocument());

    // Camera/fullscreen APIs don't exist in jsdom — the page must degrade gracefully.
    await userEvent.click(screen.getByText(/I understand — Start the interview/));
    await waitFor(() => expect(screen.getByText("Hi Jane Doe")).toBeInTheDocument());

    await userEvent.click(screen.getByText("Start the interview"));
    await waitFor(() => expect(screen.getByText("Explain gradient descent")).toBeInTheDocument());
    expect(screen.getByText("Question 1 of 8")).toBeInTheDocument();
  });

  it("shows the done screen for an already-completed session (never scores or reports)", async () => {
    vi.spyOn(api, "getCandidateSession").mockResolvedValue(makeCandidateSession({ status: "completed" }));
    renderCandidate();
    await waitFor(() => expect(screen.getByText("All done, thank you")).toBeInTheDocument());
    // Confidentiality: the candidate view must never leak evaluation artifacts.
    expect(screen.queryByText(/score/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/recommendation/i)).not.toBeInTheDocument();
  });

  it("surfaces an invalid/expired invite link as an error", async () => {
    vi.spyOn(api, "getCandidateSession").mockRejectedValue(new Error("Invalid or expired invite token"));
    renderCandidate();
    await waitFor(() => expect(screen.getByText("Invalid or expired invite token")).toBeInTheDocument());
  });

  it("disables submit until the candidate types an answer", async () => {
    vi.spyOn(api, "getCandidateSession").mockResolvedValue(makeCandidateSession());
    vi.spyOn(api, "startCandidateSession").mockResolvedValue({
      session_id: "sess-1",
      status: "active",
      question: { id: "q1", text: "Explain gradient descent", topic: null, difficulty: null, order: 1 },
    });

    renderCandidate();
    await waitFor(() => expect(screen.getByText("Exam Rules")).toBeInTheDocument());
    await userEvent.click(screen.getByText(/I understand — Start the interview/));
    await waitFor(() => expect(screen.getByText("Hi Jane Doe")).toBeInTheDocument());
    await userEvent.click(screen.getByText("Start the interview"));
    await waitFor(() => expect(screen.getByText("Explain gradient descent")).toBeInTheDocument());

    const submit = screen.getByRole("button", { name: /Submit answer/ });
    expect(submit).toBeDisabled();
    await userEvent.type(screen.getByPlaceholderText("Type your answer here..."), "It minimizes loss iteratively.");
    expect(submit).toBeEnabled();
  });
});
