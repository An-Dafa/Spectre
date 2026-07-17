import { ReactNode } from "react";

import aiConnectLogo from "../assets/AiConnect.png";
import dtetiLogo from "../assets/DTETI.png";
import finditLogo from "../assets/FINDIT.png";
import brandLogo from "../assets/Spectre_logo.svg";
import ugmLogo from "../assets/ugm.png";
import { ModeSwitch } from "../components/ModeSwitch";
import { AppMode, UserViewId, userNavItems } from "../lib/navigation";

const BRAND_LOGO = brandLogo;
const PARTNER_LOGOS = [
  { src: ugmLogo, alt: "UGM" },
  { src: dtetiLogo, alt: "DTETI" },
  { src: finditLogo, alt: "FIND IT" },
  { src: aiConnectLogo, alt: "AI Connect" },
];

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
          <img className="user-brand-logo" src={BRAND_LOGO} alt="Spectre" />
        </button>

        <div className="user-navbar-right">
          <ModeSwitch appMode={appMode} onModeChange={onModeChange} />
          <div className="partner-logo-strip" aria-label="Partner logos">
            {PARTNER_LOGOS.map((logo) => (
              <img key={logo.alt} src={logo.src} alt={logo.alt} />
            ))}
          </div>
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
