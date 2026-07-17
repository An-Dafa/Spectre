import { Activity, Database, Landmark, LockKeyhole } from "lucide-react";
import { ReactNode } from "react";

import { Panel } from "../../components/ui/Panel";
import { DashboardState } from "../../lib/useDashboard";
import { AdminViewId } from "../../lib/navigation";

// import banner from "../../assets/gov-overview-banner.png";
const PAGE_ASSETS = {
  banner: "" as string,
};

export function AdminOverviewView({
  dashboard,
  records,
  onNavigate,
}: {
  dashboard: DashboardState;
  records: Array<Record<string, unknown>>;
  onNavigate: (view: AdminViewId) => void;
}) {
  const encryptedCount = records.filter((r) => r.vault_encrypted === true).length;
  const modelActive = dashboard.modelInfo.ok;

  const consoleCards: Array<{ id: AdminViewId; title: string; description: string; icon: ReactNode }> = [
    {
      id: "operational-zone",
      title: "Operational Zone",
      description: "Redacted document database and non-private metadata.",
      icon: <Database size={22} />,
    },
    {
      id: "sovereign-vault",
      title: "Sovereign Vault",
      description: "Vault metadata, key versions, and DEK policy.",
      icon: <LockKeyhole size={22} />,
    },
    {
      id: "admin-access",
      title: "Admin Access",
      description: "Request, approval, one-time token, secure download.",
      icon: <Landmark size={22} />,
    },
    {
      id: "audit-log",
      title: "Audit Log",
      description: "Cross-zone security event trail.",
      icon: <Activity size={22} />,
    },
  ];

  return (
    <div className="view-stack">
      {PAGE_ASSETS.banner && <img className="page-banner" src={PAGE_ASSETS.banner} alt="" />}
      <section className="hero-panel">
        <h2>Admin Console Spectre</h2>
        <p className="lead">
          Monitor the Operational Zone, Sovereign Vault, original access authorization, runtime policy, and audit trail
          from one place. This is an internal console, not a public page.
        </p>
      </section>

      <section className="status-grid">
        <div className="metric-card">
          <span>Processed Documents</span>
          <strong>{records.length}</strong>
        </div>
        <div className="metric-card">
          <span>Encrypted Originals</span>
          <strong>{encryptedCount}</strong>
        </div>
        <div className="metric-card">
          <span>Audit Events</span>
          <strong>{dashboard.auditLogs.data?.count ?? 0}</strong>
        </div>
        <div className="metric-card">
          <span>Model AI</span>
          <strong>{modelActive ? "Active" : "Unavailable"}</strong>
        </div>
      </section>

      <Panel title="Quick Console Access" eyebrow="Admin Track" icon={<Landmark />}>
        <div className="console-card-grid">
          {consoleCards.map((card) => (
            <button key={card.id} type="button" className="console-card" onClick={() => onNavigate(card.id)}>
              <div className="section-icon">{card.icon}</div>
              <div>
                <strong>{card.title}</strong>
                <p>{card.description}</p>
              </div>
              <span className="console-card-cta">Open &rarr;</span>
            </button>
          ))}
        </div>
      </Panel>
    </div>
  );
}
