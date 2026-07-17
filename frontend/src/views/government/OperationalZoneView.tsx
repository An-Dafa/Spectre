import { Copy, Database, Eye, FileCheck2, Filter, Search, ShieldCheck } from "lucide-react";
import { useMemo, useState } from "react";

import { Panel } from "../../components/ui/Panel";
import { SecureViewer } from "../../components/ui/SecureViewer";
import { ApiResult, buildBackendFileUrl } from "../../lib/api";
import { formatWibDate } from "../../lib/format";

function shortValue(value: unknown, size = 10) {
  const text = value === null || value === undefined ? "" : String(value);
  return text ? `${text.substring(0, size)}${text.length > size ? "..." : ""}` : "-";
}

function getRedactedUrl(record: Record<string, unknown>) {
  return buildBackendFileUrl(String(record.redacted_url ?? record.redacted_file_url ?? ""));
}

export function OperationalZoneView({
  recordsResult,
}: {
  recordsResult: ApiResult<{ records: Array<Record<string, unknown>> } & Record<string, unknown>>;
}) {
  const records = recordsResult.data?.records ?? [];
  const [viewerUrl, setViewerUrl] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [modeFilter, setModeFilter] = useState("all");
  const [fileFilter, setFileFilter] = useState("all");
  const [copiedRecordId, setCopiedRecordId] = useState("");

  const modeOptions = useMemo(() => {
    return Array.from(
      new Set(
        records
          .map((record) => String(record.redaction_mode ?? "").trim())
          .filter(Boolean),
      ),
    ).sort((a, b) => a.localeCompare(b));
  }, [records]);

  const filteredRecords = useMemo(() => {
    const normalizedQuery = searchQuery.trim().toLowerCase();

    return records.filter((record) => {
      const redactedUrl = getRedactedUrl(record);
      const redactionMode = String(record.redaction_mode ?? "");
      const searchableText = [
        record.record_id,
        record.upload_session_id,
        record.original_filename,
        record.redacted_filename,
        record.redaction_mode,
      ]
        .map((value) => String(value ?? "").toLowerCase())
        .join(" ");

      const matchesSearch = !normalizedQuery || searchableText.includes(normalizedQuery);
      const matchesMode = modeFilter === "all" || redactionMode === modeFilter;
      const matchesFile =
        fileFilter === "all" ||
        (fileFilter === "available" && Boolean(redactedUrl)) ||
        (fileFilter === "missing" && !redactedUrl);

      return matchesSearch && matchesMode && matchesFile;
    });
  }, [fileFilter, modeFilter, records, searchQuery]);

  const privateOriginalCount = useMemo(
    () => records.filter((record) => record.stores_private_original_in_operational_zone === true).length,
    [records],
  );
  const hasActiveFilters = Boolean(searchQuery || modeFilter !== "all" || fileFilter !== "all");

  async function copyRecordId(recordId: string) {
    if (!recordId) return;

    try {
      await navigator.clipboard.writeText(recordId);
      setCopiedRecordId(recordId);
      window.setTimeout(() => setCopiedRecordId((current) => (current === recordId ? "" : current)), 1400);
    } catch {
      setCopiedRecordId("");
    }
  }

  function resetFilters() {
    setSearchQuery("");
    setModeFilter("all");
    setFileFilter("all");
  }

  return (
    <div className="view-stack operational-zone-view">
      {viewerUrl && (
        <SecureViewer
          url={viewerUrl}
          title="Pratinjau Dokumen Tersensor"
          onClose={() => setViewerUrl("")}
          isSensitive={false}
        />
      )}

      <section className="operational-hero-card">
        <div className="operational-hero-icon">
          <Database size={32} />
        </div>
        <div className="operational-hero-copy">
          <span>Operational Zone</span>
          <h2>Redacted outputs and non-private metadata only.</h2>
          <p>
            Zona ini dibuat untuk kebutuhan operasional frontend: melihat hasil redaksi, metadata proses, dan status output
            tanpa pernah menyimpan plaintext original.
          </p>
        </div>
        <div className="operational-safe-pill">
          <span />
          Original isolated in Vault
        </div>
      </section>

      <section className="operational-registry-section">
        <Panel title="Redacted Registry" eyebrow="Operational Data" icon={<FileCheck2 />}>

          {privateOriginalCount > 0 && (
            <div className="result-box error-box">
              Terdeteksi {privateOriginalCount} record dengan flag original tersimpan di operational zone. Periksa pipeline
              backend sebelum demo.
            </div>
          )}

          <div className="operational-table-toolbar">
            <label className="operational-search-field" aria-label="Cari record operational zone">
              <Search size={18} />
              <input
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Cari record ID, filename, session, atau mode..."
              />
            </label>

            <div className="operational-filter-group" aria-label="Filter tabel operational zone">
              <Filter size={16} />
              <select value={modeFilter} onChange={(event) => setModeFilter(event.target.value)}>
                <option value="all">Semua mode</option>
                {modeOptions.map((mode) => (
                  <option key={mode} value={mode}>
                    {mode}
                  </option>
                ))}
              </select>
              <select value={fileFilter} onChange={(event) => setFileFilter(event.target.value)}>
                <option value="all">Semua file</option>
                <option value="available">Preview tersedia</option>
                <option value="missing">Preview tidak tersedia</option>
              </select>
            </div>
          </div>

          {hasActiveFilters && (
            <div className="operational-table-summary">
              <button type="button" className="text-button" onClick={resetFilters}>
                Reset filter
              </button>
            </div>
          )}

          {records.length === 0 ? (
            <div className="empty-state">Belum ada dokumen yang diproses.</div>
          ) : filteredRecords.length === 0 ? (
            <div className="empty-state">Tidak ada record yang sesuai search atau filter.</div>
          ) : (
            <div className="table-wrap operational-table-wrap">
              <table className="operational-table">
                <thead>
                  <tr>
                    <th>Record ID</th>
                    <th>Dokumen Redacted</th>
                    <th>Mode</th>
                    <th>Dibuat Pada</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRecords.map((record) => {
                    const recordId = String(record.record_id ?? "");
                    const redactedUrl = getRedactedUrl(record);
                    const redactedFilename = String(record.redacted_filename ?? "");
                    const originalFilename = String(record.original_filename ?? "-");
                    const redactionMode = String(record.redaction_mode ?? "-");
                    const copied = copiedRecordId === recordId;

                    return (
                      <tr key={recordId || originalFilename}>
                        <td>
                          <div className="record-id-cell">
                            <strong>{shortValue(recordId)}</strong>
                            <button
                              type="button"
                              className={`icon-button copy-record-button ${copied ? "copied" : ""}`}
                              onClick={() => void copyRecordId(recordId)}
                              disabled={!recordId}
                              title={copied ? "Record ID disalin" : "Copy Record ID"}
                              aria-label="Copy Record ID"
                            >
                              <Copy size={15} />
                            </button>
                          </div>
                          {copied && <small className="copy-feedback">Copied</small>}
                        </td>
                        <td>
                          <div className="document-cell">
                            <div>
                              <strong>{originalFilename}</strong>
                              <small>{redactedFilename ? `Redacted: ${redactedFilename}` : "Redacted output belum tersedia"}</small>
                            </div>
                            {redactedUrl ? (
                              <button
                                type="button"
                                className="icon-button preview-eye-button"
                                onClick={() => setViewerUrl(redactedUrl)}
                                title="Preview dokumen redacted"
                                aria-label="Preview dokumen redacted"
                              >
                                <Eye size={18} />
                              </button>
                            ) : (
                              <span className="badge muted">No Preview</span>
                            )}
                          </div>
                        </td>
                        <td>
                          <span className="badge mode-badge">{redactionMode}</span>
                        </td>
                        <td>
                          <small>{formatWibDate(record.created_at)} WIB</small>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      </section>
    </div>
  );
}
