import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import Navbar from "@/components/Navbar";

export default function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setLoading(true);
    try {
      await register(email, password);
      navigate("/interview/setup");
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
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                  </svg>
                </div>
                <span
                  className="eyebrow"
                  style={{ background: "none", border: "none", padding: 0, fontSize: "10px" }}
                >
                  New workspace
                </span>
              </div>
              <h1
                className="font-bold tracking-tight mb-2"
                style={{ fontSize: "28px", fontFamily: "'Outfit', sans-serif", color: "var(--ink)" }}
              >
                Create your account
              </h1>
              <p style={{ fontSize: "14px", color: "var(--muted)", fontFamily: "'Inter', sans-serif" }}>
                Set up your workspace to run and manage candidate interviews.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div>
                <label className="field-label" htmlFor="reg-email">Email address</label>
                <input
                  id="reg-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  className="input px-4 py-3"
                  required
                />
              </div>

              <div>
                <label className="field-label" htmlFor="reg-password">
                  Password
                  <span style={{ color: "var(--muted)", fontWeight: 400, marginLeft: "0.4rem", fontSize: "12px" }}>
                    (min. 8 characters)
                  </span>
                </label>
                <input
                  id="reg-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 8 characters"
                  className="input px-4 py-3"
                  required
                />
              </div>

              {error ? <div className="alert-error fade-in">{error}</div> : null}

              <button
                id="register-submit"
                type="submit"
                disabled={loading}
                className="btn btn-primary w-full py-3 mt-1"
                style={{ borderRadius: "999px", fontSize: "15px" }}
              >
                {loading ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full spin" />
                    Creating workspace…
                  </>
                ) : "Create account →"}
              </button>
            </form>

            {/* terms */}
            <p
              className="text-center mt-4"
              style={{ fontSize: "12px", color: "var(--muted)", fontFamily: "'Inter', sans-serif" }}
            >
              By registering you agree to our terms of service.
            </p>

            <div
              className="mt-5 pt-5 text-center"
              style={{ borderTop: "1px solid var(--border)" }}
            >
              <p style={{ fontSize: "14px", color: "var(--muted)", fontFamily: "'Inter', sans-serif" }}>
                Already have an account?{" "}
                <Link to="/login" className="font-semibold" style={{ color: "var(--brand)" }}>
                  Sign in
                </Link>
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
