import { Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import Brand from "@/components/Brand";
import { useAuth } from "@/context/AuthContext";

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const { isAuthenticated, email, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const handleLogout = () => {
    navigate("/");
    logout();
    setOpen(false);
  };

  return (
    <header className={`site-nav ${scrolled ? "scrolled" : ""}`}>
      <div className="site-nav-topbar" />
      <div className="shell shell-wide site-nav-inner">
        <Brand />

        {/* desktop nav */}
        <nav className="hidden md:flex items-center gap-6">
          {isAuthenticated && (
            <Link to="/sessions" className="nav-link">
              My Sessions
            </Link>
          )}
        </nav>

        <div className="hidden md:flex items-center gap-4">
          <span className="nav-divider" />
          {isAuthenticated ? (
            <>
              <span
                className="text-[13px] font-medium"
                style={{
                  color: "var(--muted)",
                  fontFamily: "'Inter', sans-serif",
                  maxWidth: 220,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {email}
              </span>
              <button
                onClick={handleLogout}
                className="nav-link nav-login"
                style={{ color: "var(--muted)" }}
              >
                Log out
              </button>
            </>
          ) : (
            <Link to="/login" className="nav-link nav-login">
              Log in
            </Link>
          )}
          <Link
            to="/interview/setup"
            className="btn btn-primary btn-sm"
            style={{ borderRadius: "999px", paddingInline: "1.2rem" }}
          >
            Start a session
          </Link>
        </div>

        {/* mobile hamburger */}
        <button
          className="md:hidden flex items-center justify-center w-9 h-9 rounded-lg"
          style={{
            color: "var(--ink-2)",
            background: "var(--surface-alt)",
            border: "1px solid var(--border)",
          }}
          aria-label="Toggle menu"
          onClick={() => setOpen((o) => !o)}
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            {open
              ? <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              : <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            }
          </svg>
        </button>
      </div>

      {/* mobile menu */}
      {open && (
        <div
          className="md:hidden px-5 pb-5 pt-3 flex flex-col gap-1 fade-in"
          style={{
            borderTop: "1px solid var(--border)",
            background: "var(--surface)",
          }}
        >
          {isAuthenticated && (
            <Link
              to="/sessions"
              className="text-[15px] py-3 px-3 rounded-xl font-medium"
              style={{ color: "var(--ink-2)", fontFamily: "'Inter', sans-serif" }}
              onClick={() => setOpen(false)}
            >
              My Sessions
            </Link>
          )}

          {isAuthenticated ? (
            <>
              <span
                className="text-[13px] py-2 px-3"
                style={{ color: "var(--muted)", fontFamily: "'Inter', sans-serif" }}
              >
                {email}
              </span>
              <button onClick={handleLogout} className="btn btn-secondary mt-2 py-3">
                Log out
              </button>
            </>
          ) : (
            <Link
              to="/login"
              className="btn btn-secondary mt-2 py-3"
              onClick={() => setOpen(false)}
            >
              Sign in
            </Link>
          )}
          <Link
            to="/interview/setup"
            className="btn btn-primary mt-2 py-3"
            style={{ borderRadius: "999px" }}
            onClick={() => setOpen(false)}
          >
            Start a session
          </Link>
        </div>
      )}
    </header>
  );
}
