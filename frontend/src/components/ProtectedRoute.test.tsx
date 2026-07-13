import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import ProtectedRoute from "./ProtectedRoute";
import { AuthProvider } from "@/context/AuthContext";
import * as api from "@/lib/api";

function renderProtected(initialPath = "/private") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<div>Login page</div>} />
          <Route
            path="/private"
            element={
              <ProtectedRoute>
                <div>Secret content</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </MemoryRouter>
  );
}

describe("ProtectedRoute", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("redirects to /login when not authenticated", async () => {
    renderProtected();
    await waitFor(() => expect(screen.getByText("Login page")).toBeInTheDocument());
    expect(screen.queryByText("Secret content")).not.toBeInTheDocument();
  });

  it("renders the protected content when authenticated", async () => {
    api.setAuthToken("valid-token");
    vi.spyOn(api, "getMe").mockResolvedValue({ id: "u1", email: "a@b.com" });

    renderProtected();

    await waitFor(() => expect(screen.getByText("Secret content")).toBeInTheDocument());
  });
});
