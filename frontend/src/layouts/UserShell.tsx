import { ReactNode } from "react";

import brandLogo from "../assets/Logo_Spectre.jpeg";
import brandName from "../assets/Name_Spectre.jpeg";
import { ModeSwitch } from "../components/ModeSwitch";
import { AppMode, UserViewId, userNavItems } from "../lib/navigation";

const BRAND_LOGO = brandLogo;
const BRAND_NAME = brandName;

export function UserShell({
  appMode,
  onModeChange,
  activeView,
  onNavigate,
  children,
}: {
  appMode: AppMode;
  onModeChange: (mode: AppMode) => void;
  activeView: UserViewId;
  onNavigate: (view: UserViewId) => void;
  children: ReactNode;
}) {
  const navActiveId: UserViewId =
    activeView === "document-upload" || activeView === "live-filter" ? "home" : activeView;

  return (
    <div className="user-shell">
      <header className="user-navbar">
        <nav className="user-nav-links">
          {userNavItems.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`user-nav-link ${navActiveId === item.id ? "active" : ""}`}
              onClick={() => onNavigate(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>

        <button type="button" className="user-brand" onClick={() => onNavigate("home")}>
          <span className="user-brand-mark-frame" aria-hidden="true">
            <img className="user-brand-logo-mark" src={BRAND_LOGO} alt="" />
          </span>
          <img className="user-brand-logo-name" src={BRAND_NAME} alt="Spectre" />
        </button>

        <div className="user-navbar-right">
          <ModeSwitch appMode={appMode} onModeChange={onModeChange} />
        </div>
      </header>

      <main className="user-main">{children}</main>

      <footer className="user-footer">
        <span>Spectre &mdash; Visual Privacy &amp; Safety Middleware</span>
        <span>Data invisible &middot; Privacy intact</span>
      </footer>
    </div>
  );
}
