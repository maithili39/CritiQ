import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import ReportPage from "./Report";
import { AuthProvider } from "@/context/AuthContext";
import * as api from "@/lib/api";
import type { SessionSummary } from "@/lib/api";

function makeSummary(overrides: Partial<SessionSummary> = {}): SessionSummary {
  return {
    id: "sess-1",
    candidate_name: "Jane Doe",
    candidate_email: null,
    role: "ai_ml",
    status: "completed",
    current_question_index: 2,
    max_questions: 2,
    parsed_resume: {
      skills: ["PyTorch", "NLP"],
      technologies: ["Python"],
      experience_level: "senior",
      domains: ["ml"],
      summary: "Senior ML engineer",
    },
    questions: [
      {
        id: "q1",
        text: "Explain overfitting",
        topic: "Generalization",
        difficulty: "senior",
        order: 1,
        source_context: "Retrieved textbook chunk about bias-variance.",
        answer: {
          id: "a1",
          text: "Overfitting is when the model memorizes noise.",
          score: 8.5,
          rationale: "Clear and correct.",
          strengths: "Good grasp",
          gaps: "None",
          submitted_at: "2026-07-01T10:05:00Z",
          response_time_ms: 45_000,
          paste_detected: false,
          tab_switch_count: 0,
          integrity_flags: { suspicious: false, reasons: [] },
          has_camera_snapshot: true,
        },
      },
    ],
    report: {
      summary: "Strong candidate overall.",
      overall_score: 8.2,
      topic_coverage: { Generalization: 8.5 },
      strengths: "Deep ML knowledge",
      gaps: "Limited MLOps",
      recommendation: "yes",
      integrity_summary: { confidence: 100, risk_level: "low", signals: [], answers_analyzed: 1 },
    },
    outcome: null,
    outcome_note: null,
    outcome_at: null,
    invite_url: "http://x/candidate/sess-1?token=t",
    created_at: "2026-07-01T09:00:00Z",
    completed_at: "2026-07-01T10:30:00Z",
    ...overrides,
  };
}

function renderReport() {
  return render(
    <MemoryRouter initialEntries={["/interview/sess-1/report"]}>
      <AuthProvider>
        <Routes>
          <Route path="/interview/:id/report" element={<ReportPage />} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>
  );
}

describe("ReportPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("shows a fallback when the report is not ready", async () => {
    vi.spyOn(api, "getSession").mockResolvedValue(makeSummary({ report: null }));
    renderReport();
    await waitFor(() => expect(screen.getByText("Report not available yet.")).toBeInTheDocument());
  });

  it("renders score, recommendation, summary, topic coverage, and integrity confidence", async () => {
    vi.spyOn(api, "getSession").mockResolvedValue(makeSummary());
    renderReport();

    await waitFor(() => expect(screen.getByText("Jane Doe")).toBeInTheDocument());
    expect(screen.getByText("8.2")).toBeInTheDocument(); // overall score
    expect(screen.getByText("Hire")).toBeInTheDocument(); // recommendation: yes
    expect(screen.getByText("Strong candidate overall.")).toBeInTheDocument();
    // Topic appears in both the coverage chart and the transcript badge.
    expect(screen.getAllByText("Generalization").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Integrity Confidence")).toBeInTheDocument();
    expect(screen.getByText("low risk")).toBeInTheDocument();
  });

  it("expands a transcript question to reveal the answer and its RAG grounding", async () => {
    vi.spyOn(api, "getSession").mockResolvedValue(makeSummary());
    renderReport();

    await waitFor(() => expect(screen.getByText("Explain overfitting")).toBeInTheDocument());
    // Answer body hidden until the row is expanded
    expect(screen.queryByText(/memorizes noise/)).not.toBeInTheDocument();

    await userEvent.click(screen.getByText("Explain overfitting"));
    expect(screen.getByText(/memorizes noise/)).toBeInTheDocument();
    expect(screen.getByText(/Clear and correct./)).toBeInTheDocument();
    // Traceability: the exact retrieved chunk the question was grounded in
    expect(screen.getByText("📎 Grounded in knowledge base")).toBeInTheDocument();
    expect(screen.getByText(/bias-variance/)).toBeInTheDocument();
  });

  it("records a hiring outcome and shows the recorded date", async () => {
    vi.spyOn(api, "getSession").mockResolvedValue(makeSummary());
    const record = vi
      .spyOn(api, "recordOutcome")
      .mockResolvedValue({ session_id: "sess-1", outcome: "hired", outcome_at: "2026-07-16T00:00:00Z" });

    renderReport();
    await waitFor(() => expect(screen.getByText("Hired")).toBeInTheDocument());

    await userEvent.click(screen.getByText("Hired"));
    expect(record).toHaveBeenCalledWith("sess-1", "hired");
    await waitFor(() => expect(screen.getByText(/Recorded/)).toBeInTheDocument());
  });
});
