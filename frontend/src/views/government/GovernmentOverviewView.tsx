import { Activity, Database, Landmark, LockKeyhole } from "lucide-react";
import { ReactNode } from "react";

import { Panel } from "../../components/ui/Panel";
import { DashboardState } from "../../lib/useDashboard";
import { GovernmentViewId } from "../../lib/navigation";

// ╔═══ ASSET PAGE INI — ubah di sini ═══╗
// Taruh file di src/assets/ lalu uncomment import & isi nama file.
// import banner from "../../assets/gov-overview-banner.png";
const PAGE_ASSETS = {
  banner: "" as string, // banner gambar di atas halaman; "" = tidak ditampilkan
};
// ╚══════════════════════════════════════╝

export function GovernmentOverviewView({
  dashboard,
  records,
  onNavigate,
}: {
  dashboard: DashboardState;
  records: Array<Record<string, unknown>>;
  onNavigate: (view: GovernmentViewId) => void;
}) {
  const encryptedCount = records.filter((r) => r.vault_encrypted === true).length;
  const modelActive = dashboard.modelInfo.ok;

  const consoleCards: Array<{ id: GovernmentViewId; title: string; description: string; icon: ReactNode }> = [
    {
      id: "operational-zone",
      title: "Operational Zone",
      description: "Database dokumen tersensor & metadata non-privat.",
      icon: <Database size={22} />,
    },
    {
      id: "sovereign-vault",
      title: "Sovereign Vault",
      description: "Metadata vault, versi kunci, dan kebijakan DEK.",
      icon: <LockKeyhole size={22} />,
    },
    {
      id: "government-access",
      title: "Government Access",
      description: "Request, approval, token sekali pakai, secure download.",
      icon: <Landmark size={22} />,
    },
    {
      id: "audit-log",
      title: "Audit Log",
      description: "Jejak peristiwa keamanan lintas zona.",
      icon: <Activity size={22} />,
    },
  ];

  return (
    <div className="view-stack">
      {PAGE_ASSETS.banner && <img className="page-banner" src={PAGE_ASSETS.banner} alt="" />}
      <section className="hero-panel">
        <h2>Operator Console Spectre</h2>
        <p className="lead">
          Pantau Operational Zone, Sovereign Vault, otorisasi akses original, runtime policy, dan audit trail dari satu
          tempat. Console internal, bukan halaman publik.
        </p>
      </section>

      <section className="status-grid">
        <div className="metric-card">
          <span>Dokumen Diproses</span>
          <strong>{records.length}</strong>
        </div>
        <div className="metric-card">
          <span>Original Terenkripsi</span>
          <strong>{encryptedCount}</strong>
        </div>
        <div className="metric-card">
          <span>Audit Events</span>
          <strong>{dashboard.auditLogs.data?.count ?? 0}</strong>
        </div>
        <div className="metric-card">
          <span>Model AI</span>
          <strong>{modelActive ? "Aktif" : "Tidak tersedia"}</strong>
        </div>
      </section>

      <Panel title="Akses Cepat Console" eyebrow="Government Track" icon={<Landmark />}>
        <div className="console-card-grid">
          {consoleCards.map((card) => (
            <button key={card.id} type="button" className="console-card" onClick={() => onNavigate(card.id)}>
              <div className="section-icon">{card.icon}</div>
              <div>
                <strong>{card.title}</strong>
                <p>{card.description}</p>
              </div>
              <span className="console-card-cta">Buka &rarr;</span>
            </button>
          ))}
        </div>
      </Panel>
    </div>
  );
}
