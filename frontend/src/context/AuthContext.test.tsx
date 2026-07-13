import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthProvider, useAuth } from "./AuthContext";
import * as api from "@/lib/api";

function TestConsumer() {
  const { email, isAuthenticated, isLoading, login, logout } = useAuth();
  return (
    <div>
      <span data-testid="loading">{String(isLoading)}</span>
      <span data-testid="authed">{String(isAuthenticated)}</span>
      <span data-testid="email">{email ?? "none"}</span>
      <button onClick={() => login("a@b.com", "password1")}>login</button>
      <button onClick={logout}>logout</button>
    </div>
  );
}

describe("AuthContext", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("starts unauthenticated with no stored token", async () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => expect(screen.getByTestId("loading").textContent).toBe("false"));
    expect(screen.getByTestId("authed").textContent).toBe("false");
  });

  it("becomes authenticated after login() resolves", async () => {
    vi.spyOn(api, "login").mockResolvedValue({ access_token: "tok", email: "a@b.com" });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );
    await waitFor(() => expect(screen.getByTestId("loading").textContent).toBe("false"));

    await userEvent.click(screen.getByText("login"));

    await waitFor(() => expect(screen.getByTestId("authed").textContent).toBe("true"));
    expect(screen.getByTestId("email").textContent).toBe("a@b.com");
  });

  it("restores the session on mount when a token already exists (e.g. page refresh)", async () => {
    api.setAuthToken("existing-token");
    vi.spyOn(api, "getMe").mockResolvedValue({ id: "u1", email: "existing@b.com" });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => expect(screen.getByTestId("authed").textContent).toBe("true"));
    expect(screen.getByTestId("email").textContent).toBe("existing@b.com");
  });

  it("clears the stored token if it turns out to be invalid/expired", async () => {
    api.setAuthToken("stale-token");
    vi.spyOn(api, "getMe").mockRejectedValue(new Error("Invalid or expired token."));

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => expect(screen.getByTestId("loading").textContent).toBe("false"));
    expect(screen.getByTestId("authed").textContent).toBe("false");
    expect(api.getAuthToken()).toBeNull();
  });

  it("logs out and clears the token", async () => {
    vi.spyOn(api, "login").mockResolvedValue({ access_token: "tok", email: "a@b.com" });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );
    await waitFor(() => expect(screen.getByTestId("loading").textContent).toBe("false"));
    await userEvent.click(screen.getByText("login"));
    await waitFor(() => expect(screen.getByTestId("authed").textContent).toBe("true"));

    await userEvent.click(screen.getByText("logout"));

    expect(screen.getByTestId("authed").textContent).toBe("false");
    expect(api.getAuthToken()).toBeNull();
  });
});
