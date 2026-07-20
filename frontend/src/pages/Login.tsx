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
      <div className="auth-wrap">
        <div className="auth-side">
          <div className="blob blob-1" />
          <div className="blob blob-2" />
          <div className="auth-side-inner fade-up">
            <span className="auth-side-kicker">CritiQ / Screening Engine</span>
            <p className="auth-side-quote">
              Pick up right where your last <span className="gradient-text">candidate session</span> left off.
            </p>
            <ul className="auth-side-list">
              <li><span className="dot" />Live sessions, reports, and invites in one place</li>
              <li><span className="dot" />Resume-aware, adaptive technical interviews</li>
              <li><span className="dot" />Scored reports the moment a session ends</li>
            </ul>
          </div>
        </div>

        <section className="auth-panel">
          <div className="auth-card fade-up">
            <div className="mb-6">
              <h1 className="text-[30px] font-bold tracking-tight mb-2">Welcome back</h1>
              <p className="muted text-[14px]">Sign in to continue with your candidate interviews and reports.</p>
            </div>

            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div>
                <label className="field-label">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  className="input px-4 py-2.5"
                  required
                />
              </div>
              <div>
                <label className="field-label">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="Your secure password"
                  className="input px-4 py-2.5"
                  required
                />
              </div>

              {error ? <div className="alert-error fade-in">{error}</div> : null}

              <button type="submit" disabled={loading} className="btn btn-primary w-full py-3 mt-1">
                {loading ? "Signing in..." : "Sign in"}
              </button>
            </form>

            <p className="text-[13px] mt-5 muted">
              New to CritiQ? <Link to="/register" className="text-accent font-semibold">Create an account</Link>
            </p>
          </div>
        </section>

      </div>
    </div>
  );
}
