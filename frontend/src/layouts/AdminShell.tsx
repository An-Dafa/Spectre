import { RefreshCw } from "lucide-react";
import { ReactNode } from "react";

import spectreLogo from "../assets/Tagline_Spectre.png";
import { ModeSwitch } from "../components/ModeSwitch";
import { AppMode, AdminViewId, adminNavItems } from "../lib/navigation";

const BRAND_LOGO = spectreLogo;

export function AdminShell({
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
  activeView: AdminViewId;
  onNavigate: (view: AdminViewId) => void;
  online: boolean;
  isLoading: boolean;
  onRefresh: () => void;
  children: ReactNode;
}) {
  const activeTitle = adminNavItems.find((item) => item.id === activeView)?.label ?? "Admin Console";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <button type="button" className="brand-card admin-brand-card" onClick={() => onNavigate("overview")}>
          <img className="admin-brand-logo" src={BRAND_LOGO} alt="Spectre Logo" />
          <small>Admin Console</small>
        </button>
        <nav>
          {adminNavItems.map((item) => (
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
