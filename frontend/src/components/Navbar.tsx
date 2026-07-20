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
    // Navigate away from any ProtectedRoute-wrapped page *before* clearing auth
    // state. Otherwise, if you're on a protected page, clearing auth first causes
    // that still-mounted route to re-render and redirect itself to /login before
    // this navigate("/") call resolves — a race ProtectedRoute usually wins,
    // landing you on the login page instead of home.
    navigate("/");
    logout();
    setOpen(false);
  };

  return (
    <header className={`site-nav ${scrolled ? "scrolled" : ""}`}>
      <div className="site-nav-topbar" />
      <div className="shell shell-wide site-nav-inner">
        <Brand />

        <nav className="hidden md:flex items-center gap-1">
          {isAuthenticated && (
            <Link to="/sessions" className="nav-link">My Sessions</Link>
          )}
        </nav>

        <div className="hidden md:flex items-center gap-4">
          <span className="nav-divider" />
          {isAuthenticated ? (
            <>
              <span className="nav-link" style={{ color: "var(--muted)" }}>{email}</span>
              <button onClick={handleLogout} className="nav-link nav-login" style={{ background: "none", border: "none", cursor: "pointer" }}>
                Log out
              </button>
            </>
          ) : (
            <Link to="/login" className="nav-link nav-login">
              Log In
            </Link>
          )}
          <Link to="/interview/setup" className="btn btn-primary btn-sm">
            Start a session
          </Link>
        </div>

        <button
          className="md:hidden p-2 rounded-lg"
          style={{ color: "var(--muted)", border: "1px solid var(--border)" }}
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

      {open && (
        <div className="md:hidden px-6 pb-5 pt-3 flex flex-col gap-1 fade-in" style={{ borderTop: "1px solid #f3f4f6", background: "#fff" }}>
          {isAuthenticated && (
            <Link to="/sessions" className="text-[15px] py-3 px-3 rounded-lg font-medium" style={{ color: "var(--muted)" }} onClick={() => setOpen(false)}>
              My Sessions
            </Link>
          )}

          {isAuthenticated ? (
            <>
              <span className="text-[13px] py-2 px-3" style={{ color: "var(--cyan)" }}>{email}</span>
              <button onClick={handleLogout} className="btn btn-secondary mt-2 text-[14px] py-3">
                Log out
              </button>
            </>
          ) : (
            <Link to="/login" className="btn btn-secondary mt-2 text-[14px] py-3" onClick={() => setOpen(false)}>
              Sign in
            </Link>
          )}
          <Link
            to="/interview/setup"
            className="btn btn-primary mt-3 text-[14px] py-3"
            onClick={() => setOpen(false)}
          >
            Start a session
          </Link>
        </div>
      )}
    </header>
  );
}
