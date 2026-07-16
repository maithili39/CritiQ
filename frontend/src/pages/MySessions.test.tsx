import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import MySessionsPage from "./MySessions";
import { AuthProvider } from "@/context/AuthContext";
import * as api from "@/lib/api";
import type { SessionListItem } from "@/lib/api";

const emptyCalibration = {
  total_labeled: 0,
  correlation: null,
  confusion: { true_positive: 0, false_positive: 0, false_negative: 0, true_negative: 0 },
} as Awaited<ReturnType<typeof api.getCalibration>>;

function makeSession(overrides: Partial<SessionListItem> = {}): SessionListItem {
  return {
    id: "s1",
    candidate_name: "Jane Doe",
    role: "ai_ml",
    status: "completed",
    created_at: "2026-07-01T10:00:00Z",
    overall_score: 8.2,
    ...overrides,
  } as SessionListItem;
}

function listResult(sessions: SessionListItem[], total = sessions.length) {
  return { sessions, total, limit: 20, offset: 0 };
}

function renderPage() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <MySessionsPage />
      </AuthProvider>
    </MemoryRouter>
  );
}

describe("MySessionsPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("renders sessions with role label, score, and report link for completed ones", async () => {
    vi.spyOn(api, "listSessions").mockResolvedValue(listResult([makeSession()]));
    vi.spyOn(api, "getCalibration").mockResolvedValue(emptyCalibration);

    renderPage();

    await waitFor(() => expect(screen.getByText("Jane Doe")).toBeInTheDocument());
    expect(screen.getByText("AI / ML Engineer")).toBeInTheDocument();
    expect(screen.getByText("8.2/10")).toBeInTheDocument();
    expect(screen.getByText("Completed")).toBeInTheDocument();
    // Completed sessions must deep-link to the report, not the interview.
    expect(screen.getByText("Jane Doe").closest("a")).toHaveAttribute("href", "/interview/s1/report");
  });

  it("links in-progress sessions to the interview, without a score", async () => {
    vi.spyOn(api, "listSessions").mockResolvedValue(
      listResult([makeSession({ id: "s2", status: "active", overall_score: null })])
    );
    vi.spyOn(api, "getCalibration").mockResolvedValue(emptyCalibration);

    renderPage();

    await waitFor(() => expect(screen.getByText("In progress")).toBeInTheDocument());
    expect(screen.queryByText(/\/10/)).not.toBeInTheDocument();
    expect(screen.getByText("Jane Doe").closest("a")).toHaveAttribute("href", "/interview/s2");
  });

  it("shows the empty state when there are no sessions", async () => {
    vi.spyOn(api, "listSessions").mockResolvedValue(listResult([]));
    vi.spyOn(api, "getCalibration").mockResolvedValue(emptyCalibration);

    renderPage();

    await waitFor(() => expect(screen.getByText(/No sessions yet/)).toBeInTheDocument());
    expect(screen.getByText("Start session")).toBeInTheDocument();
  });

  it("surfaces a load error instead of an infinite spinner", async () => {
    vi.spyOn(api, "listSessions").mockRejectedValue(new Error("Session expired"));
    vi.spyOn(api, "getCalibration").mockResolvedValue(emptyCalibration);

    renderPage();

    await waitFor(() => expect(screen.getByText("Session expired")).toBeInTheDocument());
    expect(screen.queryByText("Loading sessions")).not.toBeInTheDocument();
  });

  it("still renders sessions when the calibration call fails (non-critical)", async () => {
    vi.spyOn(api, "listSessions").mockResolvedValue(listResult([makeSession()]));
    vi.spyOn(api, "getCalibration").mockRejectedValue(new Error("500"));

    renderPage();

    await waitFor(() => expect(screen.getByText("Jane Doe")).toBeInTheDocument());
    expect(screen.queryByText("Screening Calibration")).not.toBeInTheDocument();
  });

  it("shows the calibration banner with correlation and accuracy when labeled outcomes exist", async () => {
    vi.spyOn(api, "listSessions").mockResolvedValue(listResult([makeSession()]));
    vi.spyOn(api, "getCalibration").mockResolvedValue({
      ...emptyCalibration,
      total_labeled: 6,
      correlation: 0.72,
      confusion: { true_positive: 3, false_positive: 1, false_negative: 0, true_negative: 2 },
    });

    renderPage();

    await waitFor(() => expect(screen.getByText("Screening Calibration")).toBeInTheDocument());
    expect(screen.getByText("0.72")).toBeInTheDocument();
    expect(screen.getByText("Strong")).toBeInTheDocument();
    expect(screen.getByText("83%")).toBeInTheDocument(); // (3+2)/6 rounded
  });
});
