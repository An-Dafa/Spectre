import { Activity, Cpu, Database, LockKeyhole } from "lucide-react";

import { Collapsible } from "../../components/ui/Collapsible";
import { JsonBlock } from "../../components/ui/JsonBlock";
import { Panel } from "../../components/ui/Panel";
import { DashboardState } from "../../lib/useDashboard";

export function MetricsView({ dashboard }: { dashboard: DashboardState }) {
  const records = dashboard.storageRecords.data?.records ?? [];
  const encryptedCount = records.filter((r) => r.vault_encrypted === true).length;
  const totalDetections = records.reduce((sum, r) => sum + Number(r.detection_count ?? 0), 0);
  const totalRedacted = records.reduce((sum, r) => sum + Number(r.redacted_count ?? 0), 0);
  const latencies = records
    .map((r) => Number(r.latency_ms ?? 0))
    .filter((v) => Number.isFinite(v) && v > 0);
  const avgLatency = latencies.length ? latencies.reduce((a, b) => a + b, 0) / latencies.length : 0;

  const health = dashboard.health.data;
  const modelInfo = dashboard.modelInfo.data;
  const keyInfo = dashboard.cryptoKeyInfo.data;

  const statusRows: Array<{ label: string; value: string; ok: boolean }> = [
    { label: "Backend Health", value: dashboard.health.ok ? "Online" : "Offline", ok: dashboard.health.ok },
    {
      label: "Model AI",
      value: dashboard.modelInfo.ok ? "Loaded" : "Unavailable",
      ok: dashboard.modelInfo.ok,
    },
    {
      label: "Redaction Config",
      value: dashboard.redactionConfig.ok ? "Available" : "Unavailable",
      ok: dashboard.redactionConfig.ok,
    },
    {
      label: "Sovereign Vault Key",
      value: dashboard.cryptoKeyInfo.ok ? "Active" : "Unavailable",
      ok: dashboard.cryptoKeyInfo.ok,
    },
  ];

  return (
    <div className="view-stack">
      <section className="hero-panel">
        <h2>System Metrics</h2>
        <p className="lead">
          Backend health, model status, vault state, and document processing aggregates in the Operational Zone.
        </p>
      </section>

      <section className="status-grid">
        <div className="metric-card">
          <span>Processed Documents</span>
          <strong>{records.length}</strong>
        </div>
        <div className="metric-card">
          <span>Total Detections</span>
          <strong>{totalDetections}</strong>
        </div>
        <div className="metric-card">
          <span>Total Redacted Areas</span>
          <strong>{totalRedacted}</strong>
        </div>
        <div className="metric-card">
          <span>Average Latency</span>
          <strong>{avgLatency ? `${avgLatency.toFixed(0)} ms` : "-"}</strong>
        </div>
        <div className="metric-card">
          <span>Encrypted Originals</span>
          <strong>{encryptedCount}</strong>
        </div>
        <div className="metric-card">
          <span>Audit Events</span>
          <strong>{dashboard.auditLogs.data?.count ?? 0}</strong>
        </div>
      </section>

      <div className="two-column">
        <Panel title="Component Status" eyebrow="Backend" icon={<Activity />}>
          <div className="key-value-list">
            {statusRows.map((row) => (
              <div className="key-value-item" key={row.label}>
                <span>{row.label}</span>
                <strong>
                  <span className={`badge ${row.ok ? "green" : "danger"}`}>{row.value}</span>
                </strong>
              </div>
            ))}
            <div className="key-value-item">
              <span>Device</span>
              <strong>{String(health?.device ?? "-")}</strong>
            </div>
          </div>
        </Panel>

        <Panel title="Model & Vault" eyebrow="Detail" icon={<Cpu />}>
          <div className="key-value-list">
            <div className="key-value-item">
              <span>Model Loaded</span>
              <strong>{health?.model_loaded ? "Yes" : "No"}</strong>
            </div>
            <div className="key-value-item">
              <span>Model Exists</span>
              <strong>{health?.model_exists ? "Yes" : "No"}</strong>
            </div>
            <div className="key-value-item">
              <span>Active Key Version</span>
              <strong>{String(keyInfo?.active_version ?? "-")}</strong>
            </div>
            <div className="key-value-item">
              <span>Key ID</span>
              <strong>{String(keyInfo?.key_id ?? "-")}</strong>
            </div>
          </div>
        </Panel>
      </div>

      <Panel title="Raw Diagnostics" eyebrow="JSON" icon={<Database />}>
        <Collapsible title="Health Response">
          <JsonBlock data={health ?? dashboard.health.error} />
        </Collapsible>
        <Collapsible title="Model Info">
          <JsonBlock data={modelInfo ?? dashboard.modelInfo.error} />
        </Collapsible>
        <Collapsible title="Crypto Key Info">
          <JsonBlock data={keyInfo ?? dashboard.cryptoKeyInfo.error} />
        </Collapsible>
      </Panel>

      <div className="alert-card success">
        <LockKeyhole size={24} color="var(--success)" />
        <div>
          <strong>Privacy Preserved</strong>
          <p>Metrics hanya mengagregasi metadata non-privat. No ada konten original yang diekspos di view ini.</p>
        </div>
      </div>
    </div>
  );
}
