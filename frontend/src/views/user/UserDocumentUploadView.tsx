import { Copy, EyeOff, FileText, LockKeyhole, RefreshCw, ShieldCheck, SlidersHorizontal } from "lucide-react";
import { ChangeEvent, DragEvent, FormEvent, useEffect, useState } from "react";

import { ClassSelectionGrid } from "../../components/ui/ClassSelectionGrid";
import { Collapsible } from "../../components/ui/Collapsible";
import { Field } from "../../components/ui/Field";
import { JsonBlock } from "../../components/ui/JsonBlock";
import { ApiResult, RedactionConfigResponse, buildBackendFileUrl, redactImage, safeRequest } from "../../lib/api";
import { PERFORMANCE_MODES, PRIVACY_CLASSES } from "../../lib/constants";
import { formatMs, readNestedString } from "../../lib/format";
import { getDisabledPrivacyClasses } from "../../lib/policy";

const PAGE_ASSETS = {
  banner: "" as string,
};

export function UserDocumentUploadView({
  redactionConfig,
  onRefresh,
}: {
  redactionConfig: RedactionConfigResponse | null;
  onRefresh: () => Promise<void>;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [fileError, setFileError] = useState("");
  const [isDraggingFile, setIsDraggingFile] = useState(false);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.35);
  const [profile, setProfile] = useState("government");
  const [redactionMode, setRedactionMode] = useState("default");

  const availableClasses = PRIVACY_CLASSES;
  const [activeClasses, setActiveClasses] = useState<string[]>(availableClasses);
  const disabledClasses = getDisabledPrivacyClasses(activeClasses);

  const [useRuntimePolicy, setUseRuntimePolicy] = useState(false);
  const [performanceMode, setPerformanceMode] = useState("fast");
  const [authenticityOcr, setAuthenticityOcr] = useState(false);
  const [result, setResult] = useState<ApiResult<Record<string, unknown>> | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const selectedPerformanceMode = PERFORMANCE_MODES.find((item) => item.value === performanceMode) ?? PERFORMANCE_MODES[0];

  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview);
    };
  }, [preview]);

  useEffect(() => {
    if (performanceMode !== "robust" && authenticityOcr) {
      setAuthenticityOcr(false);
    }
  }, [performanceMode, authenticityOcr]);

  function selectFile(nextFile: File | null) {
    setResult(null);
    setFileError("");

    if (!nextFile) {
      setFile(null);
      setPreview("");
      return;
    }

    const isSupportedDocument =
      nextFile.type.startsWith("image/") ||
      nextFile.type === "application/pdf" ||
      /\.(jpe?g|png|webp|pdf)$/i.test(nextFile.name);
    if (!isSupportedDocument) {
      setFile(null);
      setPreview("");
      setFileError("File harus berupa JPG, PNG, WEBP, atau PDF satu halaman.");
      return;
    }

    setFile(nextFile);
    setPreview(URL.createObjectURL(nextFile));
  }

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    const nextFile = event.target.files?.[0] ?? null;
    selectFile(nextFile);
    event.target.value = "";
  }

  function onFileDrag(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    event.stopPropagation();
  }

  function onFileDragEnter(event: DragEvent<HTMLLabelElement>) {
    onFileDrag(event);
    setIsDraggingFile(true);
  }

  function onFileDragLeave(event: DragEvent<HTMLLabelElement>) {
    onFileDrag(event);
    setIsDraggingFile(false);
  }

  function onFileDrop(event: DragEvent<HTMLLabelElement>) {
    onFileDrag(event);
    setIsDraggingFile(false);
    const nextFile = event.dataTransfer.files?.[0] ?? null;
    selectFile(nextFile);
    event.dataTransfer.clearData();
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    setIsSubmitting(true);
    const nextResult = await safeRequest(() =>
      redactImage({
        file,
        confidenceThreshold,
        profile,
        redactionMode,
        activeClasses: activeClasses.join(","),
        disabledClasses: disabledClasses.join(","),
        useRuntimePolicy,
        performanceMode,
        authenticityOcr: performanceMode === "robust" && authenticityOcr,
      }),
    );
    setResult(nextResult);
    setIsSubmitting(false);
    if (nextResult.ok) await onRefresh();
  }

  const redactedUrl = buildBackendFileUrl(readNestedString(result?.data, ["operational_zone", "redacted_file", "url"]));
  const isPdf = file?.type === "application/pdf" || /\.pdf$/i.test(file?.name ?? "");
  const detectionCount = result?.ok ? (result.data?.detections as unknown[])?.length ?? 0 : 0;
  const redactedCount = result?.ok ? Number(result.data?.redacted_count ?? 0) : 0;
  const performance = result?.ok ? ((result.data?.performance as Record<string, unknown> | undefined) ?? null) : null;
  const timing = result?.ok ? ((result.data?.timing as Record<string, unknown> | undefined) ?? null) : null;
  const latency = result?.ok
    ? Number(timing?.total_ms ?? result.data?.total_latency_ms ?? result.data?.latency_ms ?? 0)
    : 0;
  const detectorLatency = result?.ok ? Number(performance?.detector_latency_ms ?? result.data?.latency_ms ?? 0) : 0;
  const recordId = result?.ok ? String(result.data?.record_id ?? "") : "";
  const rejectedDetections = result?.ok ? ((result.data?.rejected_detections as unknown[]) ?? []) : [];
  const validationSummary = result?.ok
    ? ((result.data?.validation_summary as Record<string, unknown> | undefined) ?? null)
    : null;
  const rejectedCount = Number(validationSummary?.rejected_count ?? rejectedDetections.length);
  const timingItems = timing
    ? [
        ["Total", timing.total_ms],
        ["Inference", timing.inference_ms],
        ["Guardrail", timing.guardrail_ms],
        ["Redaction", timing.redaction_ms],
        ["Storage", timing.storage_ms],
        ["Vault", timing.vault_ms],
      ]
    : [];

  return (
    <div className="view-stack user-upload-page">
      {PAGE_ASSETS.banner && <img className="page-banner" src={PAGE_ASSETS.banner} alt="" />}

      <section className="user-hero user-hero-compact upload-hero">
        <div className="user-hero-copy">
          <h1>Document Privacy Shield.</h1>
          <p>
            Upload dokumen identitas, biarkan Spectre melindungi area sensitif, lalu bagikan hanya output yang sudah
            aman.
          </p>
        </div>
      </section>

      <form className="user-upload-form" onSubmit={submit}>
        <div className="upload-workbench">
          <section className="upload-viewer-card upload-source-card">
            <div className="upload-card-header">
              <div>
                <p className="eyebrow">Document Privacy Shield</p>
                <h3>Original Document</h3>
              </div>
              <details className="upload-settings-dropdown">
                <summary>
                  <SlidersHorizontal size={16} /> Settings
                </summary>
                <div className="upload-settings-menu">
                  <div className="form-grid compact-form-grid">
                    <Field label={`Confidence (${confidenceThreshold})`}>
                      <input
                        type="range"
                        min="0.01"
                        max="0.99"
                        step="0.01"
                        value={confidenceThreshold}
                        onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
                      />
                    </Field>
                    <Field label="Performance Mode">
                      <select value={performanceMode} onChange={(e) => setPerformanceMode(e.target.value)}>
                        {PERFORMANCE_MODES.map((item) => (
                          <option key={item.value} value={item.value}>
                            {item.label}
                          </option>
                        ))}
                      </select>
                      <small className="field-hint">{selectedPerformanceMode.description}</small>
                    </Field>
                    <Field label="Profile">
                      <select value={profile} onChange={(e) => setProfile(e.target.value)}>
                        {Object.keys(redactionConfig?.profiles ?? { government: null, live_webcam: null }).map((item) => (
                          <option key={item}>{item}</option>
                        ))}
                      </select>
                    </Field>
                    <Field label="Redaction Mode">
                      <select value={redactionMode} onChange={(e) => setRedactionMode(e.target.value)}>
                        <option value="default">default</option>
                        {(redactionConfig?.allowed_modes ?? ["black_box", "blur", "pixelate"]).map((item) => (
                          <option key={item}>{item}</option>
                        ))}
                      </select>
                    </Field>
                  </div>

                  <Field label="Target Kelas Aktif">
                    <ClassSelectionGrid
                      options={availableClasses}
                      selected={activeClasses}
                      onChange={setActiveClasses}
                    />
                  </Field>

                  <div className="inline-form upload-settings-checks">
                    <label className="checkbox-line">
                      <input
                        type="checkbox"
                        checked={useRuntimePolicy}
                        onChange={(e) => setUseRuntimePolicy(e.target.checked)}
                      />{" "}
                      Gunakan Dynamic Policy
                    </label>
                    <label className="checkbox-line">
                      <input
                        type="checkbox"
                        checked={authenticityOcr}
                        disabled={performanceMode !== "robust"}
                        onChange={(e) => setAuthenticityOcr(e.target.checked)}
                      />{" "}
                      OCR detail KTP
                    </label>
                  </div>
                </div>
              </details>
            </div>

            <label
              className={`document-drop-zone${isDraggingFile ? " is-dragging" : ""}${file ? " has-file" : ""}`}
              onDragEnter={onFileDragEnter}
              onDragOver={onFileDrag}
              onDragLeave={onFileDragLeave}
              onDrop={onFileDrop}
            >
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp,application/pdf,.jpg,.jpeg,.png,.webp,.pdf"
                onChange={onFileChange}
              />
              {preview ? (
                isPdf ? (
                  <object className="document-pdf-preview" data={preview} type="application/pdf" aria-label="PDF preview">
                    <div className="document-drop-empty">
                      <FileText size={42} />
                      <strong>{file?.name}</strong>
                      <span>PDF satu halaman siap diproses.</span>
                    </div>
                  </object>
                ) : (
                  <img src={preview} alt="Original document preview" />
                )
              ) : (
                <div className="document-drop-empty">
                  <FileText size={42} />
                  <strong>Drag & drop dokumen di sini</strong>
                  <span>atau klik untuk memilih JPG, PNG, WEBP, atau PDF satu halaman</span>
                </div>
              )}
            </label>
            {fileError && <div className="field-warning">{fileError}</div>}

            <button className="primary-button user-run-redaction" disabled={!file || isSubmitting}>
              {isSubmitting ? (
                <>
                  <RefreshCw className="spin" size={16} /> Memproses...
                </>
              ) : (
                "Jalankan Redaksi"
              )}
            </button>
          </section>

          <section className="upload-viewer-card upload-result-card">
            <div className="upload-card-header">
              <div>
                <p className="eyebrow">Preview</p>
                <h3>Hasil Redaksi</h3>
              </div>
              <EyeOff size={22} />
            </div>
            <div className={`redacted-viewer${redactedUrl ? " has-file" : ""}`}>
              {redactedUrl ? (
                <img src={redactedUrl} alt="Redacted document preview" />
              ) : (
                <div className="document-drop-empty muted-empty">
                  <EyeOff size={42} />
                  <strong>Hasil redaksi akan tampil di sini</strong>
                  <span>Spectre akan menampilkan output aman setelah proses selesai.</span>
                </div>
              )}
            </div>
          </section>
        </div>
      </form>

      {result?.ok && (
        <div className="result-box success-box upload-result-summary">
          <div className="meta-row">
            <div className="meta-item">
              <span>Record ID</span>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <strong>{recordId}</strong>
                <button
                  className="copy-button"
                  type="button"
                  onClick={() => navigator.clipboard.writeText(recordId)}
                  title="Copy ID"
                >
                  <Copy size={14} />
                </button>
              </div>
            </div>
            <div className="meta-item">
              <span>Total Latency</span>
              <strong>{formatMs(latency)}</strong>
              <small>Detector: {formatMs(detectorLatency)}</small>
            </div>
            <div className="meta-item">
              <span>Deteksi</span>
              <strong>{detectionCount} objek</strong>
            </div>
            <div className="meta-item">
              <span>Diredaksi</span>
              <strong>{redactedCount} area</strong>
            </div>
            <div className="meta-item">
              <span>Ditolak Guardrail</span>
              <strong>{rejectedCount} objek</strong>
            </div>
          </div>

          {timingItems.length > 0 && (
            <div className="timing-grid">
              {timingItems.map(([label, value]) => (
                <div className="timing-card" key={String(label)}>
                  <span>{String(label)}</span>
                  <strong>{formatMs(value)}</strong>
                </div>
              ))}
            </div>
          )}

          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "16px" }}>
            {(result.data?.detections as Array<Record<string, unknown>>)?.map((d, i) => (
              <div key={i} className={`badge ${String(d.guardrail_action) === "skip_redaction" ? "danger" : "copper"}`}>
                {String(d.class_name)} {(Number(d.confidence) * 100).toFixed(0)}%
                {d.validation_status ? ` - ${String(d.validation_status)}` : ""}
              </div>
            ))}
          </div>

          {rejectedCount > 0 && (
            <div className="alert-card warning" style={{ marginBottom: 0 }}>
              <ShieldCheck size={24} color="var(--warning)" />
              <div>
                <strong>Guardrail menolak {rejectedCount} kandidat</strong>
                <p>
                  Deteksi yang dicurigai sebagai gambar tangan/sketsa atau tidak punya bukti dokumen resmi tidak ikut
                  diredaksi pada mode precision demo.
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {result && !result.ok && (
        <div className="alert-card warning">
          <ShieldCheck size={24} color="var(--danger)" />
          <div>
            <strong>Gagal Memproses Dokumen</strong>
            <p>{result.error?.message || "Terjadi kesalahan pada sistem."}</p>
          </div>
        </div>
      )}

      {result?.ok && (
        <div className="alert-card success">
          <LockKeyhole size={24} color="var(--success)" />
          <div>
            <strong>Output aman tersimpan</strong>
            <p>
              Hasil tersensor masuk ke Operational Zone, sementara dokumen original dienkripsi di Sovereign Vault.
              Sebagai user, kamu tidak bisa membuka original - akses itu hanya lewat jalur otorisasi pemerintah.
            </p>
          </div>
        </div>
      )}

      {result && (
        <Collapsible title="Detail Teknis (JSON)">
          <JsonBlock data={result.ok ? result.data : result.error} />
        </Collapsible>
      )}
    </div>
  );
}
