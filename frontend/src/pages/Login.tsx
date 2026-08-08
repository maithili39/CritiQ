import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import Navbar from "@/components/Navbar";

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/sessions");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-stack">
      <Navbar />
      <div className="auth-wrap-centered">
        <section className="auth-panel">
          <div className="auth-card fade-up">
            {/* header */}
            <div className="mb-7">
              <div className="flex items-center gap-2 mb-4">
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center"
                  style={{ background: "var(--brand-soft)", border: "1px solid var(--brand-line)" }}
                >
                  <svg className="w-4 h-4" style={{ color: "var(--brand)" }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </div>
                <span
                  className="eyebrow"
                  style={{ background: "none", border: "none", padding: 0, fontSize: "10px" }}
                >
                  Welcome back
                </span>
              </div>
              <h1
                className="font-bold tracking-tight mb-2"
                style={{ fontSize: "28px", fontFamily: "'Outfit', sans-serif", color: "var(--ink)" }}
              >
                Sign in to CritiQ
              </h1>
              <p style={{ fontSize: "14px", color: "var(--muted)", fontFamily: "'Inter', sans-serif" }}>
                Continue with your candidate interviews and reports.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div>
                <label className="field-label" htmlFor="login-email">Email address</label>
                <input
                  id="login-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  className="input px-4 py-3"
                  required
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="field-label" htmlFor="login-password" style={{ marginBottom: 0 }}>Password</label>
                </div>
                <input
                  id="login-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Your secure password"
                  className="input px-4 py-3"
                  required
                />
              </div>

              {error ? <div className="alert-error fade-in">{error}</div> : null}

              <button
                id="login-submit"
                type="submit"
                disabled={loading}
                className="btn btn-primary w-full py-3 mt-1"
                style={{ borderRadius: "999px", fontSize: "15px" }}
              >
                {loading ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full spin" />
                    Signing in…
                  </>
                ) : "Sign in →"}
              </button>
            </form>

            <div
              className="mt-6 pt-5 text-center"
              style={{ borderTop: "1px solid var(--border)" }}
            >
              <p style={{ fontSize: "14px", color: "var(--muted)", fontFamily: "'Inter', sans-serif" }}>
                New to CritiQ?{" "}
                <Link to="/register" className="font-semibold" style={{ color: "var(--brand)" }}>
                  Create a free account
                </Link>
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
