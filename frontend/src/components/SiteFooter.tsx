import { Link } from "react-router-dom";

export default function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="footer-notch" aria-hidden="true" />
      <div className="shell shell-wide" style={{ position: "relative" }}>
        <div className="footer-top">
          <div className="footer-mark" aria-hidden="true">
            c
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2c.6 3.4 1.4 5.6 2.6 6.9 1.2 1.3 3.3 2.1 6.4 2.6-3.1.5-5.2 1.3-6.4 2.6-1.2 1.3-2 3.5-2.6 6.9-.6-3.4-1.4-5.6-2.6-6.9-1.2-1.3-3.3-2.1-6.4-2.6 3.1-.5 5.2-1.3 6.4-2.6C10.6 7.6 11.4 5.4 12 2z" />
            </svg>
          </div>

          <div className="footer-newsletter">
            <h3>Get started with CritiQ</h3>
            <p>Upload a resume, pick a role, and run your first AI-scored technical screening in minutes.</p>
            <Link to="/interview/setup" className="footer-subscribe" style={{ display: "inline-block", textDecoration: "none", textAlign: "center" }}>
              Start a session
            </Link>
          </div>
        </div>

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
      <div className="footer-bottom-wrapper">
        <div className="shell shell-wide footer-bottom">
          <span>© 2026 CritiQ. All rights reserved.</span>
        </div>
      </div>
    </footer>
  );
}
