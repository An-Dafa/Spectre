import { RefreshCw } from "lucide-react";
import { ReactNode } from "react";

import aiConnectLogo from "../assets/AiConnect.png";
import dtetiLogo from "../assets/DTETI.png";
import finditLogo from "../assets/FINDIT.png";
import spectreLogo from "../assets/Spectre_logo.svg";
import ugmLogo from "../assets/ugm.png";
import { ModeSwitch } from "../components/ModeSwitch";
import { AppMode, GovernmentViewId, governmentNavItems } from "../lib/navigation";

const BRAND_LOGO = spectreLogo;
const PARTNER_LOGOS = [
  { src: ugmLogo, alt: "UGM" },
  { src: dtetiLogo, alt: "DTETI" },
  { src: finditLogo, alt: "FIND IT" },
  { src: aiConnectLogo, alt: "AI Connect" },
];

export function GovernmentShell({
  appMode,
  onModeChange,
  activeView,
  onNavigate,
  isLoading,
  onRefresh,
  children,
}: {
  appMode: AppMode;
  onModeChange: (mode: AppMode) => void;
  activeView: GovernmentViewId;
  onNavigate: (view: GovernmentViewId) => void;
  online: boolean;
  isLoading: boolean;
  onRefresh: () => void;
  children: ReactNode;
}) {
  const activeTitle = governmentNavItems.find((item) => item.id === activeView)?.label ?? "Operator Console";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <button type="button" className="brand-card government-brand-card" onClick={() => onNavigate("overview")}>
          <img className="government-brand-logo" src={BRAND_LOGO} alt="Spectre Logo" />
          <small>Operator Console</small>
        </button>
        <nav>
          {governmentNavItems.map((item) => (
            <button
              key={item.id}
              type="button"
              className={activeView === item.id ? "nav-item active" : "nav-item"}
              onClick={() => onNavigate(item.id)}
            >
              {item.icon}
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div className="title-group">
            <h1>{activeTitle}</h1>
          </div>
          <div className="topbar-actions">
            <ModeSwitch appMode={appMode} onModeChange={onModeChange} />
            <div className="government-topbar-logo-strip" aria-label="Partner logos">
              {PARTNER_LOGOS.map((logo) => (
                <img key={logo.alt} src={logo.src} alt={logo.alt} />
              ))}
            </div>
            <button className="primary-button secondary-button" onClick={onRefresh} disabled={isLoading}>
              <RefreshCw className={isLoading ? "spin" : ""} size={16} />
              Refresh
            </button>
          </div>
        </header>

        {children}
      </main>
    </div>
  );
}
