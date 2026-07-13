import { Link } from "react-router-dom";
import { ReactNode } from "react";
import Brand from "@/components/Brand";

type AppHeaderProps = {
  right?: ReactNode;
  mutedText?: string;
};

export default function AppHeader({ right, mutedText }: AppHeaderProps) {
  return (
    <header className="app-header">
      <div className="site-nav-topbar" />
      <div className="shell shell-wide app-header-inner">
        <div className="app-header-left">
          <Brand />
          {mutedText ? <span className="app-header-meta">{mutedText}</span> : null}
        </div>

        <div className="app-header-actions">
          {right}
          <Link to="/" className="btn btn-subtle">
            Home
          </Link>
        </div>
      </div>
    </header>
  );
}
