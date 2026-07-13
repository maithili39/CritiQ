import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { login, register, getMe, getAuthToken, setAuthToken, clearAuthToken } from "./api";

function mockFetchOnce(body: unknown, init: { ok?: boolean; status?: number } = {}) {
  const ok = init.ok ?? true;
  const status = init.status ?? (ok ? 200 : 400);
  return vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => body,
    statusText: "Error",
  });
}

describe("lib/api", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("stores the access token after a successful login", async () => {
    vi.stubGlobal("fetch", mockFetchOnce({ access_token: "tok-123", email: "a@b.com" }));

    await login("a@b.com", "password1");

    expect(getAuthToken()).toBe("tok-123");
  });

  it("stores the access token after a successful register", async () => {
    vi.stubGlobal("fetch", mockFetchOnce({ access_token: "tok-456", email: "new@b.com" }));

    await register("new@b.com", "password1");

    expect(getAuthToken()).toBe("tok-456");
  });

  it("attaches the Authorization header when a token is present", async () => {
    setAuthToken("saved-token");
    const fetchMock = mockFetchOnce({ id: "u1", email: "a@b.com" });
    vi.stubGlobal("fetch", fetchMock);

    await getMe();

    const [, options] = fetchMock.mock.calls[0];
    const headers = options.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer saved-token");
  });

  it("does not attach an Authorization header when no token is stored", async () => {
    clearAuthToken();
    const fetchMock = mockFetchOnce({ id: "u1", email: "a@b.com" });
    vi.stubGlobal("fetch", fetchMock);

    await getMe();

    const [, options] = fetchMock.mock.calls[0];
    const headers = options.headers as Headers;
    expect(headers.get("Authorization")).toBeNull();
  });

  it("throws with the server's error detail on a failed request", async () => {
    vi.stubGlobal("fetch", mockFetchOnce({ detail: "Incorrect email or password." }, { ok: false, status: 401 }));

    await expect(login("a@b.com", "wrong")).rejects.toThrow("Incorrect email or password.");
  });

  it("falls back to statusText when the error body isn't JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
        json: async () => {
          throw new Error("not json");
        },
      })
    );

    await expect(login("a@b.com", "x")).rejects.toThrow("Internal Server Error");
  });
});
