import { Link } from "react-router-dom";

export default function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="footer-notch" aria-hidden="true" />

      <div className="shell shell-wide" style={{ position: "relative" }}>
        {/* ── TOP ROW ── */}
        <div className="footer-top">
          <div className="footer-mark" aria-hidden="true">CQ</div>

          <div className="footer-newsletter">
            <h3>Get started with CritiQ</h3>
            <p>
              Upload a resume, pick a role, and run your first AI-scored technical
              screening in minutes.
            </p>
            <Link
              to="/interview/setup"
              className="footer-subscribe"
              style={{ display: "inline-block", textDecoration: "none", textAlign: "center" }}
            >
              Start a session →
            </Link>
          </div>
        </div>

        {/* ── LINKS GRID ── */}
        <div className="footer-grid">
          <div className="footer-col">
            <h4>Product</h4>
            <ul>
              <li><Link to="/interview/setup">Start an interview</Link></li>
              <li><Link to="/sessions">My sessions</Link></li>
            </ul>
          </div>
          <div className="footer-col">
            <h4>Company</h4>
            <ul>
              <li><a href="/#about">About Us</a></li>
              <li><a href="/#mission">Mission</a></li>
            </ul>
          </div>
          <div className="footer-col">
            <h4>Account</h4>
            <ul>
              <li><Link to="/login">Log in</Link></li>
              <li><Link to="/register">Create an account</Link></li>
            </ul>
          </div>
          <div className="footer-col">
            <h4>Contact</h4>
            <ul>
              <li><a href="mailto:hello@critiq.app">hello@critiq.app</a></li>
            </ul>
          </div>
        </div>
      </div>

      {/* ── BOTTOM BAR ── */}
      <div className="footer-bottom-wrapper">
        <div className="shell shell-wide footer-bottom">
          <span>© 2026 CritiQ. All rights reserved.</span>
          <div className="footer-inline-links">
            <a href="#">Privacy</a>
            <a href="#">Terms</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
