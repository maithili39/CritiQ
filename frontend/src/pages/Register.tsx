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
      <div className="auth-wrap">
        <section className="auth-panel">
          <div className="auth-card fade-up">
            <div className="mb-6">
              <h1 className="text-[30px] font-bold tracking-tight mb-2">Create your workspace</h1>
              <p className="muted text-[14px]">Set up your account to run and manage candidate interview sessions.</p>
            </div>

            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div>
                <label className="field-label">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  className="input px-3.5 py-2.5"
                  required
                />
              </div>
              <div>
                <label className="field-label">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="At least 8 characters"
                  className="input px-3.5 py-2.5"
                  required
                />
              </div>

              {error ? <div className="alert-error fade-in">{error}</div> : null}

              <button type="submit" disabled={loading} className="btn btn-primary w-full py-3 mt-1">
                {loading ? "Creating account..." : "Create account"}
              </button>
            </form>

            <p className="text-[13px] mt-5 muted">
              Already registered? <Link to="/login" className="text-accent font-semibold">Sign in</Link>
            </p>
          </div>
        </section>

      </div>
    </div>
  );
}
