import {
  Activity,
  Clock,
  Copy,
  Database,
  Filter,
  Landmark,
  LockKeyhole,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  UserRound,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Field } from "../../components/ui/Field";
import { JsonBlock } from "../../components/ui/JsonBlock";
import { NumericInput } from "../../components/ui/NumericInput";
import { Panel } from "../../components/ui/Panel";
import { ApiResult, AuditLog, AuditLogFilters, getAuditLogs, safeRequest } from "../../lib/api";
import { formatWibDate } from "../../lib/format";

const ZONE_OPTIONS = [
  "Sovereign Vault",
  "Operational Zone",
  "Government Access API",
  "Dynamic Injection",
  "AI Guardrail",
  "AI Pipeline",
];

function getZoneClass(zone?: string | null) {
  if (zone === "Sovereign Vault") return "green";
  if (zone === "Operational Zone") return "copper";
  if (zone === "Government Access API") return "danger";
  if (zone === "Dynamic Injection") return "brown";
  if (zone === "AI Guardrail" || zone === "AI Pipeline") return "dark";
  return "muted";
}

function getZoneIcon(zone?: string | null) {
  if (zone === "Sovereign Vault") return <LockKeyhole size={17} />;
  if (zone === "Operational Zone") return <Database size={17} />;
  if (zone === "Government Access API") return <Landmark size={17} />;
  if (zone === "Dynamic Injection") return <SlidersHorizontal size={17} />;
  return <Activity size={17} />;
}

function shortValue(value?: string | null, size = 12) {
  if (!value) return "-";
  return value.length > size ? `${value.substring(0, size)}...` : value;
}

export function AuditLogView({
  initialLogs,
}: {
  initialLogs: ApiResult<{ logs: AuditLog[]; count: number }>;
}) {
  const [filters, setFilters] = useState<
    Required<Pick<AuditLogFilters, "limit" | "recordId" | "zone" | "eventType">>
  >({ limit: 50, recordId: "", zone: "", eventType: "" });
  const [result, setResult] = useState(initialLogs);
  const [selectedLogId, setSelectedLogId] = useState<number | null>(null);
  const [copiedRecordId, setCopiedRecordId] = useState("");
  const [isFiltering, setIsFiltering] = useState(false);

  useEffect(() => {
    setResult(initialLogs);
  }, [initialLogs]);

  const logs = result.data?.logs ?? [];
  const selectedLog = logs.find((log) => log.id === selectedLogId) ?? logs[0] ?? null;

  useEffect(() => {
    if (logs.length && !logs.some((log) => log.id === selectedLogId)) {
      setSelectedLogId(logs[0].id);
    }
  }, [logs, selectedLogId]);

  const summary = useMemo(() => {
    const uniqueActors = new Set(logs.map((log) => log.actor).filter(Boolean));
    const uniqueZones = new Set(logs.map((log) => log.zone).filter(Boolean));
    const sensitiveEvents = logs.filter((log) =>
      ["Government Access API", "Sovereign Vault"].includes(String(log.zone ?? "")),
    ).length;

    return {
      total: logs.length,
      actors: uniqueActors.size,
      zones: uniqueZones.size,
      sensitiveEvents,
    };
  }, [logs]);

  async function applyFilters(nextFilters = filters) {
    setIsFiltering(true);
    const response = await safeRequest(() => getAuditLogs(nextFilters));
    setResult(response);
    setIsFiltering(false);
  }

  function updateFilter(next: Partial<typeof filters>) {
    setFilters((current) => ({ ...current, ...next }));
  }

  async function selectZone(zone: string) {
    const nextFilters = { ...filters, zone: filters.zone === zone ? "" : zone };
    setFilters(nextFilters);
    await applyFilters(nextFilters);
  }

  async function copyRecordId(recordId?: string | null) {
    if (!recordId) return;
    try {
      await navigator.clipboard.writeText(recordId);
      setCopiedRecordId(recordId);
      window.setTimeout(() => setCopiedRecordId((current) => (current === recordId ? "" : current)), 1300);
    } catch {
      setCopiedRecordId("");
    }
  }

  return (
    <div className="view-stack audit-log-view">
      <section className="audit-hero-card">
        <div className="audit-hero-icon">
          <Activity size={32} />
        </div>
        <div className="audit-hero-copy">
          <span>Security Audit Trail</span>
          <h2>Trace every sensitive action across Spectre zones.</h2>
          <p>
            Audit Log membantu investigator melihat siapa melakukan apa, kapan, pada zone mana, dan record mana yang
            terdampak tanpa membuka data privat.
          </p>
        </div>
        <div className="audit-live-pill">
          <span /> {isFiltering ? "Filtering logs" : "Audit stream ready"}
        </div>
      </section>

      <section className="audit-metric-grid">
        <div className="audit-metric-card dark">
          <span>Events Loaded</span>
          <strong>{summary.total}</strong>
          <small>Current query window</small>
        </div>
        <div className="audit-metric-card">
          <span>Sensitive Events</span>
          <strong>{summary.sensitiveEvents}</strong>
          <small>Vault and government access events</small>
        </div>
        <div className="audit-metric-card">
          <span>Actors</span>
          <strong>{summary.actors}</strong>
          <small>Unique actors in result</small>
        </div>
        <div className="audit-metric-card">
          <span>Zones</span>
          <strong>{summary.zones}</strong>
          <small>Subsystems represented</small>
        </div>
      </section>

      <Panel title="Investigation Filters" eyebrow="Audit Query" icon={<Filter />}>
        <div className="audit-filter-grid">
          <Field label="Limit Maksimal">
            <NumericInput
              min={1}
              max={200}
              value={filters.limit}
              fallbackValue={50}
              onValueChange={(value) => updateFilter({ limit: value })}
            />
          </Field>
          <Field label="Record ID">
            <label className="audit-search-field">
              <Search size={17} />
              <input
                value={filters.recordId}
                onChange={(event) => updateFilter({ recordId: event.target.value })}
                placeholder="Cari record spesifik"
              />
            </label>
          </Field>
          <Field label="Zone">
            <select value={filters.zone} onChange={(event) => updateFilter({ zone: event.target.value })}>
              <option value="">Semua Zone</option>
              {ZONE_OPTIONS.map((zone) => (
                <option key={zone} value={zone}>{zone}</option>
              ))}
            </select>
          </Field>
          <Field label="Event Type">
            <input
              value={filters.eventType}
              onChange={(event) => updateFilter({ eventType: event.target.value })}
              placeholder="Contoh: access_request_created"
            />
          </Field>
        </div>

        <div className="audit-zone-chip-row">
          {ZONE_OPTIONS.map((zone) => (
            <button
              key={zone}
              type="button"
              className={`audit-zone-chip ${filters.zone === zone ? "active" : ""}`}
              onClick={() => void selectZone(zone)}
            >
              {getZoneIcon(zone)}
              {zone}
            </button>
          ))}
        </div>

        <div className="audit-filter-actions">
          <button type="button" className="primary-button" onClick={() => void applyFilters()} disabled={isFiltering}>
            {isFiltering ? "Memuat Log..." : "Terapkan Filter"}
          </button>
          <button
            type="button"
            className="primary-button secondary-button"
            onClick={() => {
              const reset = { limit: 50, recordId: "", zone: "", eventType: "" };
              setFilters(reset);
              void applyFilters(reset);
            }}
            disabled={isFiltering}
          >
            Reset
          </button>
        </div>
      </Panel>

      <section className="audit-console-grid">
        <Panel title="Event Timeline" eyebrow={`Menampilkan ${logs.length} event`} icon={<ShieldCheck />}>
          {logs.length === 0 ? (
            <div className="empty-state">Tidak ada event audit yang sesuai filter.</div>
          ) : (
            <div className="audit-timeline-list">
              {logs.map((log) => {
                const selected = selectedLog?.id === log.id;
                const zoneClass = getZoneClass(log.zone);

                return (
                  <button
                    key={log.id}
                    type="button"
                    className={`audit-event-card ${selected ? "active" : ""}`}
                    onClick={() => setSelectedLogId(log.id)}
                  >
                    <div className={`audit-event-icon ${zoneClass}`}>{getZoneIcon(log.zone)}</div>
                    <div className="audit-event-body">
                      <div className="audit-event-head">
                        <strong>{log.event_type}</strong>
                        <span className={`badge ${zoneClass}`}>{log.zone || "Unknown Zone"}</span>
                      </div>
                      <p>{log.action || "No action detail provided."}</p>
                      <div className="audit-event-meta">
                        <span><UserRound size={13} /> {log.actor || "system"}</span>
                        <span><Database size={13} /> {shortValue(log.record_id, 14)}</span>
                        <span><Clock size={13} /> {formatWibDate(log.created_at)} WIB</span>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </Panel>

        <aside className="audit-detail-card">
          {selectedLog ? (
            <>
              <div className="audit-detail-head">
                <div className={`audit-event-icon ${getZoneClass(selectedLog.zone)}`}>{getZoneIcon(selectedLog.zone)}</div>
                <div>
                  <span>Selected Event</span>
                  <strong>{selectedLog.event_type}</strong>
                </div>
              </div>

              <div className="audit-detail-grid">
                <div>
                  <span>Zone</span>
                  <strong>{selectedLog.zone || "-"}</strong>
                </div>
                <div>
                  <span>Actor</span>
                  <strong>{selectedLog.actor || "system"}</strong>
                </div>
                <div>
                  <span>Created At</span>
                  <strong>{formatWibDate(selectedLog.created_at)} WIB</strong>
                </div>
                <div>
                  <span>Record ID</span>
                  <strong>{selectedLog.record_id || "-"}</strong>
                  {selectedLog.record_id && (
                    <button type="button" className="text-button" onClick={() => void copyRecordId(selectedLog.record_id)}>
                      {copiedRecordId === selectedLog.record_id ? "Copied" : "Copy Record ID"}
                    </button>
                  )}
                </div>
              </div>

              <div className="audit-action-box">
                <span>Action</span>
                <p>{selectedLog.action || "No action detail provided."}</p>
              </div>

              <div className="audit-json-shell">
                <div className="audit-json-head">Details JSON</div>
                <JsonBlock data={selectedLog.details ?? {}} />
              </div>
            </>
          ) : (
            <div className="audit-detail-empty">
              <ShieldCheck size={30} />
              <strong>Pilih event audit</strong>
              <span>Detail event dan JSON metadata akan tampil di panel ini.</span>
            </div>
          )}
        </aside>
      </section>
    </div>
  );
}
