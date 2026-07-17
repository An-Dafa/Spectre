import {
  ArrowRight,
  CheckCircle2,
  Copy,
  Database,
  Fingerprint,
  KeyRound,
  LockKeyhole,
  RotateCw,
  Search,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ApiResult, getVaultRecord, rotateVaultKey, safeRequest } from "../../lib/api";
import { formatWibDate } from "../../lib/format";

const ROTATION_STEPS = [
  "Generate new RSA key version",
  "Mark public key active for new uploads",
  "Retain old key for historical bundles",
  "Write rotation audit event",
];

type RotationPhase = "idle" | "rotating" | "success" | "error";

function readString(value: unknown, fallback = "-") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function shortId(value: unknown, size = 10) {
  const text = readString(value, "");
  return text ? `${text.substring(0, size)}${text.length > size ? "..." : ""}` : "-";
}

function nestedRecord(value: unknown) {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function formatKeyVersion(value: unknown) {
  const text = readString(value, "");
  return text ? `v${text}` : "-";
}

function nextVersionLabel(value: unknown) {
  const numeric = Number(value);
  if (Number.isFinite(numeric) && numeric > 0) return `v${numeric + 1}`;
  return "next";
}

function simulationDelay(ms = 1550) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export function SovereignVaultView({
  records,
  keyInfo,
}: {
  records: Array<Record<string, unknown>>;
  keyInfo: ApiResult<Record<string, unknown>>;
}) {
  const [recordId, setRecordId] = useState(String(records[0]?.record_id ?? ""));
  const [cryptoAdminToken, setCryptoAdminToken] = useState("spectre-crypto-admin-demo-token");
  const [vaultResult, setVaultResult] = useState<ApiResult<Record<string, unknown>> | null>(null);
  const [rotateResult, setRotateResult] = useState<ApiResult<Record<string, unknown>> | null>(null);
  const [rotationPhase, setRotationPhase] = useState<RotationPhase>("idle");
  const [rotationStep, setRotationStep] = useState(0);
  const [search, setSearch] = useState("");
  const [copiedValue, setCopiedValue] = useState("");

  const kInfo = keyInfo.data as Record<string, unknown> | undefined;
  const activeKey = nestedRecord(kInfo?.active_key);
  const rotatedKey = rotateResult?.ok ? nestedRecord(rotateResult.data?.new_key) : {};
  const activeKeyVersion = readString(rotatedKey.key_version ?? activeKey.key_version ?? kInfo?.active_version ?? kInfo?.key_version);
  const activeKeyId = readString(rotatedKey.key_id ?? activeKey.key_id ?? kInfo?.key_id);
  const activeFingerprint = readString(
    rotatedKey.public_key_fingerprint ?? activeKey.public_key_fingerprint ?? kInfo?.public_fingerprint ?? kInfo?.public_key_fingerprint,
  );
  const activeKeyCreatedAt = readString(rotatedKey.created_at ?? activeKey.created_at ?? kInfo?.created_at, "");
  const encryptedCount = records.filter((record) => record.vault_encrypted === true).length;
  const selectedRecord = records.find((record) => String(record.record_id ?? "") === recordId);
  const vaultData = vaultResult?.ok ? vaultResult.data : null;
  const metadataSource = vaultData ?? selectedRecord ?? null;
  const metadataRecordId = readString(metadataSource?.record_id, "");
  const isRotating = rotationPhase === "rotating";

  useEffect(() => {
    if (!recordId && records[0]?.record_id) setRecordId(String(records[0].record_id));
  }, [recordId, records]);

  useEffect(() => {
    if (!isRotating) return;

    const timer = window.setInterval(() => {
      setRotationStep((current) => (current + 1) % ROTATION_STEPS.length);
    }, 420);

    return () => window.clearInterval(timer);
  }, [isRotating]);

  const filteredRecords = useMemo(() => {
    const s = search.trim().toLowerCase();
    if (!s) return records;

    return records.filter((record) => {
      const searchable = [
        record.record_id,
        record.upload_session_id,
        record.original_filename,
        record.redacted_filename,
        record.vault_key_id,
        record.vault_key_version,
      ]
        .map((value) => String(value ?? "").toLowerCase())
        .join(" ");
      return searchable.includes(s);
    });
  }, [records, search]);

  async function copyValue(value: unknown) {
    const text = readString(value, "");
    if (!text) return;

    try {
      await navigator.clipboard.writeText(text);
      setCopiedValue(text);
      window.setTimeout(() => setCopiedValue((current) => (current === text ? "" : current)), 1400);
    } catch {
      setCopiedValue("");
    }
  }

  async function loadVaultRecord(id: string) {
    if (!id.trim()) return;
    setRecordId(id);
    const result = await safeRequest(() => getVaultRecord(id));
    setVaultResult(result);
  }

  async function handleRecordSelect(id: string) {
    await loadVaultRecord(id);
  }

  async function handleRotateKey() {
    setRotateResult(null);
    setRotationPhase("rotating");
    setRotationStep(0);

    const [result] = await Promise.all([safeRequest(() => rotateVaultKey(cryptoAdminToken)), simulationDelay()]);
    setRotateResult(result);
    setRotationPhase(result.ok ? "success" : "error");
  }

  return (
    <div className="view-stack sovereign-vault-view">
      <section className="vault-hero-card">
        <div className="vault-hero-icon">
          <LockKeyhole size={32} />
        </div>
        <div className="vault-hero-copy">
          <span>Sovereign Vault</span>
          <h2>Encrypted original custody with visible key movement simulation.</h2>
          <p>
            Originals are stored as encrypted bundles. This page shows metadata, wrapping key status, and key rotation
            simulation without exposing plaintext or private keys.
          </p>
        </div>
        <div className={`vault-security-pill ${isRotating ? "running" : ""}`}>
          {isRotating ? <RotateCw className="spin" size={16} /> : <ShieldCheck size={16} />}
          {isRotating ? "Rotating key" : "Vault sealed"}
        </div>
      </section>

      <section className="vault-command-board">
        <div className="vault-active-summary">
          <div className="vault-card-heading">
            <span>Active Wrapping Key</span>
            <strong>{formatKeyVersion(activeKeyVersion)}</strong>
          </div>
          <div className="vault-key-id-box">
            <small>Key ID</small>
            <strong>{activeKeyId}</strong>
            <button type="button" className="text-button" onClick={() => void copyValue(activeKeyId)}>
              {copiedValue === activeKeyId ? "Copied" : "Copy key id"}
            </button>
          </div>
          <div className="vault-fingerprint-row">
            <Fingerprint size={18} />
            <div>
              <span>Public fingerprint</span>
              <strong>{activeFingerprint}</strong>
            </div>
            <button type="button" className="icon-button" onClick={() => void copyValue(activeFingerprint)} title="Copy fingerprint">
              <Copy size={15} />
            </button>
          </div>
          <div className="vault-policy-mini-grid">
            <div>
              <span>Encrypted Records</span>
              <strong>{encryptedCount}</strong>
            </div>
            <div>
              <span>Created</span>
              <strong>{activeKeyCreatedAt ? `${formatWibDate(activeKeyCreatedAt)} WIB` : "Current active key"}</strong>
            </div>
          </div>
        </div>

        <div className="vault-rotation-stage">
          <div className="vault-stage-head">
            <div>
              <span>Key Rotation Simulation</span>
              <strong>{rotationPhase === "success" ? "Rotation complete" : rotationPhase === "error" ? "Rotation blocked" : "Versioned key handoff"}</strong>
            </div>
            <div className={`vault-phase-chip ${rotationPhase}`}>
              {isRotating ? <RotateCw className="spin" size={15} /> : rotationPhase === "success" ? <CheckCircle2 size={15} /> : <KeyRound size={15} />}
              {rotationPhase === "idle" && "Idle"}
              {rotationPhase === "rotating" && "Processing"}
              {rotationPhase === "success" && "New key active"}
              {rotationPhase === "error" && "Failed"}
            </div>
          </div>

          <div className={`vault-key-lane ${rotationPhase}`}>
            <div className="vault-key-node current">
              <KeyRound size={24} />
              <span>Current</span>
              <strong>{formatKeyVersion(activeKeyVersion)}</strong>
            </div>
            <div className="vault-transfer-track">
              <div className="vault-transfer-line" />
              <div className="vault-key-packet">
                <KeyRound size={16} />
              </div>
              <ArrowRight size={20} />
            </div>
            <div className="vault-key-node next">
              <LockKeyhole size={24} />
              <span>Next Active</span>
              <strong>{rotationPhase === "success" ? formatKeyVersion(activeKeyVersion) : nextVersionLabel(activeKeyVersion)}</strong>
            </div>
          </div>

          <div className="vault-step-strip">
            {ROTATION_STEPS.map((step, index) => {
              const status = rotationPhase === "success" || (isRotating && index <= rotationStep) ? "active" : "";
              return (
                <div key={step} className={`vault-step-chip ${status}`}>
                  <span>{index + 1}</span>
                  {step}
                </div>
              );
            })}
          </div>

          <div className="vault-rotation-controls">
            <input
              value={cryptoAdminToken}
              onChange={(event) => setCryptoAdminToken(event.target.value)}
              type="password"
              placeholder="Crypto Admin Token"
            />
            <button type="button" className="primary-button" onClick={() => void handleRotateKey()} disabled={isRotating}>
              <RotateCw className={isRotating ? "spin" : ""} size={16} />
              {isRotating ? "Rotating" : "Rotate Vault Key"}
            </button>
          </div>

          {rotateResult && (
            <div className={`vault-rotation-result ${rotateResult.ok ? "success" : "error"}`}>
              {rotateResult.ok
                ? "Key rotation succeeded. New uploads use the latest active key, while old keys remain available for older bundles."
                : rotateResult.error?.message || "Gagal merotasi key."}
            </div>
          )}
        </div>
      </section>

      <section className="vault-record-workbench">
        <aside className="vault-record-browser">
          <div className="vault-browser-head">
            <div>
              <span>Encrypted Original Index</span>
              <strong>Vault Records</strong>
            </div>
          </div>
          <label className="vault-search-field" aria-label="Search vault records">
            <Search size={18} />
            <input
              type="text"
              placeholder="Search record ID, filename, session, or key..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>

          {records.length === 0 ? (
            <div className="vault-empty-detail">No encrypted originals in the vault yet.</div>
          ) : filteredRecords.length === 0 ? (
            <div className="vault-empty-detail">No ada record vault yang sesuai pencarian.</div>
          ) : (
            <div className="vault-record-list-clean">
              {filteredRecords.map((record) => {
                const id = readString(record.record_id, "");
                const isSelected = id === recordId;
                const encrypted = record.vault_encrypted === true;

                return (
                  <button
                    key={id || readString(record.original_filename)}
                    type="button"
                    className={`vault-record-row ${isSelected ? "active" : ""}`}
                    onClick={() => void handleRecordSelect(id)}
                  >
                    <div className="vault-record-row-icon">
                      <Database size={18} />
                    </div>
                    <div>
                      <strong>{readString(record.original_filename)}</strong>
                      <small>{shortId(id, 14)}</small>
                    </div>
                    <div className="vault-record-row-meta">
                      <span className={encrypted ? "badge dark" : "badge muted"}>{encrypted ? "Encrypted" : "Missing"}</span>
                      <small>{formatKeyVersion(record.vault_key_version)}</small>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </aside>

        <section className="vault-metadata-panel">
          <div className="vault-metadata-panel-head">
            <div>
              <span>Metadata Inspector</span>
              <strong>{shortId(metadataRecordId, 18)}</strong>
            </div>
            {metadataRecordId && (
              <button type="button" className="icon-button" onClick={() => void copyValue(metadataRecordId)} title="Copy Record ID">
                <Copy size={15} />
              </button>
            )}
          </div>

          <div className="vault-lookup-box clean">
            <label className="vault-search-field" aria-label="Lookup vault record">
              <Search size={18} />
              <input value={recordId} onChange={(event) => setRecordId(event.target.value)} placeholder="Enter Record ID" />
            </label>
            <button type="button" className="primary-button" onClick={() => void loadVaultRecord(recordId)}>
              Search Metadata
            </button>
          </div>

          {vaultResult && !vaultResult.ok && (
            <div className="result-box error-box">{vaultResult.error?.message || "Vault metadata was not found."}</div>
          )}

          {metadataSource ? (
            <div className="vault-metadata-clean-card">
              <div className="vault-metadata-seal">
                <LockKeyhole size={22} />
                <div>
                  <span>{readString(vaultData?.access_level, "metadata_only")}</span>
                  <strong>Plaintext original is not returned here.</strong>
                </div>
              </div>
              <div className="vault-metadata-grid">
                <div>
                  <span>Record ID</span>
                  <strong>{readString(metadataSource.record_id)}</strong>
                </div>
                <div>
                  <span>Original Filename</span>
                  <strong>{readString(metadataSource.original_filename)}</strong>
                </div>
                <div>
                  <span>Encryption Algorithm</span>
                  <strong>{readString(vaultData?.encryption_algorithm, "AES-256-GCM + RSA-OAEP-SHA256")}</strong>
                </div>
                <div>
                  <span>Key Version</span>
                  <strong>{formatKeyVersion(vaultData?.key_version ?? metadataSource.vault_key_version)}</strong>
                </div>
                <div>
                  <span>Ciphertext SHA-256</span>
                  <strong>{readString(vaultData?.ciphertext_sha256, "Load metadata to view hash")}</strong>
                </div>
                <div>
                  <span>Retention</span>
                  <strong>{readString(vaultData?.retention_status, metadataSource.vault_encrypted ? "encrypted_bundle_available" : "unknown")}</strong>
                </div>
              </div>
            </div>
          ) : (
            <div className="vault-empty-detail large">
              <LockKeyhole size={30} />
              <strong>Select a vault record</strong>
              <span>Encrypted metadata will appear here without opening the original plaintext.</span>
            </div>
          )}
        </section>
      </section>
    </div>
  );
}
