import {
  AlertTriangle,
  CheckCircle2,
  Eye,
  Fingerprint,
  KeyRound,
  Landmark,
  LockKeyhole,
  RefreshCw,
  ShieldCheck,
  UserCheck,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Field } from "../../components/ui/Field";
import { Panel } from "../../components/ui/Panel";
import { SecureViewer } from "../../components/ui/SecureViewer";
import {
  approveGovernmentAccessRequest,
  createGovernmentAccessRequest,
  downloadGovernmentOriginal,
  safeRequest,
} from "../../lib/api";

const FLOW_STEPS = [
  {
    title: "Request Intake",
    detail: "Record ID, pemohon, dan alasan akses dicatat sebagai permohonan resmi.",
  },
  {
    title: "Audit Registration",
    detail: "Permohonan masuk ke audit trail sebelum original dapat dibuka.",
  },
  {
    title: "Approver Gate",
    detail: "Pejabat berwenang memvalidasi dan menerbitkan approval.",
  },
  {
    title: "One-Time Token",
    detail: "Token sekali pakai diterbitkan dan tidak disimpan dalam bentuk plaintext.",
  },
  {
    title: "Vault Decryption",
    detail: "Backend memvalidasi token, membuka vault, lalu menandai token used.",
  },
  {
    title: "Secure Viewer",
    detail: "Original hanya ditampilkan dalam sesi terbatas dan dapat diakhiri manual.",
  },
];

const PHASE_LABELS: Record<string, string> = {
  idle: "Awaiting official request",
  requesting: "Registering access request",
  approving: "Verifying approver authority",
  decrypting: "Validating one-time token",
  ready: "Restricted original ready",
  ended: "Secure session closed",
  error: "Action blocked",
};

function truncate(value: string, size = 18) {
  return value ? `${value.substring(0, size)}${value.length > size ? "..." : ""}` : "-";
}

function simulationDelay(ms = 900) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export function GovernmentAccessView({ latestRecordId }: { latestRecordId: string }) {
  const [step, setStep] = useState(1);
  const [recordId, setRecordId] = useState(latestRecordId);
  const [requestId, setRequestId] = useState("");
  const [accessToken, setAccessToken] = useState("");

  const [requester, setRequester] = useState("Pejabat Dukcapil");
  const [reason, setReason] = useState("Investigasi resmi No. 123/2026");
  const [governmentToken, setGovernmentToken] = useState("spectre-government-demo-token");
  const [approverToken, setApproverToken] = useState("spectre-approver-demo-token");
  const [approvedBy, setApprovedBy] = useState("Hakim Ketua");

  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [phase, setPhase] = useState("idle");
  const [simulationIndex, setSimulationIndex] = useState(0);

  const [viewerUrl, setViewerUrl] = useState("");
  const [originalBlobUrl, setOriginalBlobUrl] = useState("");
  const [originalFilename, setOriginalFilename] = useState("spectre-original.bin");

  useEffect(() => {
    if (latestRecordId && !recordId) setRecordId(latestRecordId);
  }, [latestRecordId, recordId]);

  useEffect(() => {
    if (!["requesting", "approving", "decrypting"].includes(phase)) return;

    const timer = window.setInterval(() => {
      setSimulationIndex((current) => (current + 1) % FLOW_STEPS.length);
    }, 520);

    return () => window.clearInterval(timer);
  }, [phase]);

  useEffect(() => {
    return () => {
      if (originalBlobUrl) URL.revokeObjectURL(originalBlobUrl);
    };
  }, [originalBlobUrl]);

  const completedStepCount = useMemo(() => {
    if (step <= 1) return 0;
    if (step === 2) return 2;
    if (step === 3) return 4;
    return 6;
  }, [step]);

  const progressPercent = Math.round((completedStepCount / FLOW_STEPS.length) * 100);
  const isBusy = ["requesting", "approving", "decrypting"].includes(phase);

  function setFailure(message: string) {
    setErrorMsg(message);
    setSuccessMsg("");
    setPhase("error");
  }

  function clearMessages(nextPhase: string) {
    setErrorMsg("");
    setSuccessMsg("");
    setPhase(nextPhase);
    setSimulationIndex(0);
  }

  async function createRequest() {
    clearMessages("requesting");
    const [response] = await Promise.all([
      safeRequest(() =>
        createGovernmentAccessRequest({ recordId, requester, requesterRole: "verifier", reason, governmentToken }),
      ),
      simulationDelay(),
    ]);
    if (response.ok) {
      setRequestId(String(response.data?.request_id ?? ""));
      setSuccessMsg("Permohonan akses tercatat. Menunggu approval pejabat berwenang.");
      setPhase("idle");
      setStep(2);
    } else {
      setFailure(response.error?.message || "Gagal membuat request.");
    }
  }

  async function approveRequest() {
    clearMessages("approving");
    const [response] = await Promise.all([
      safeRequest(() => approveGovernmentAccessRequest({ requestId, approvedBy, approverToken })),
      simulationDelay(),
    ]);
    if (response.ok) {
      setAccessToken(String(response.data?.one_time_access_token ?? ""));
      setSuccessMsg("Approval valid. One-time access token diterbitkan untuk satu kali penggunaan.");
      setPhase("idle");
      setStep(3);
    } else {
      setFailure(response.error?.message || "Gagal menyetujui request.");
    }
  }

  async function downloadOriginal() {
    clearMessages("decrypting");
    const [response] = await Promise.all([
      safeRequest(() => downloadGovernmentOriginal({ requestId, accessToken, governmentToken })),
      simulationDelay(1100),
    ]);
    if (response.ok && response.data) {
      if (originalBlobUrl) URL.revokeObjectURL(originalBlobUrl);
      const url = URL.createObjectURL(response.data.blob);
      setOriginalBlobUrl(url);
      setOriginalFilename(response.data.filename);
      setSuccessMsg("Vault berhasil dibuka lewat jalur resmi. Original siap ditampilkan dalam secure viewer.");
      setPhase("ready");
      setStep(4);
    } else if (response.error?.status === 403) {
      setFailure("Token sudah digunakan, kedaluwarsa, atau tidak valid. Akses ditolak oleh Government Access API.");
    } else {
      setFailure(response.error?.message || "Gagal menarik dokumen asli.");
    }
  }

  function openSecureViewer() {
    if (!originalBlobUrl) return;
    setViewerUrl(originalBlobUrl);
  }

  function handleCloseViewer() {
    setViewerUrl("");
    if (originalBlobUrl) {
      URL.revokeObjectURL(originalBlobUrl);
      setOriginalBlobUrl("");
    }
    setStep(1);
    setPhase("ended");
    setAccessToken("");
    setRequestId("");
    setSuccessMsg("Sesi secure viewer diakhiri. Token satu kali dianggap hangus dan tidak dapat dipakai ulang.");
  }

  return (
    <div className="view-stack government-access-view">
      {viewerUrl && (
        <SecureViewer
          url={viewerUrl}
          title="DOKUMEN ASLI (RESTRICTED ACCESS)"
          onClose={handleCloseViewer}
          isSensitive={true}
        />
      )}

      <section className="access-hero-card">
        <div className="access-hero-icon">
          <Landmark size={32} />
        </div>
        <div className="access-hero-copy">
          <span>Government Access API</span>
          <h2>Controlled original access with approval, one-time token, and audit trail.</h2>
          <p>
            Original tidak langsung dibuka dari frontend. Flow ini mensimulasikan jalur resmi: request, approval,
            token satu kali, dekripsi vault, dan secure viewer.
          </p>
        </div>
        <div className="access-live-chip">
          <span /> {PHASE_LABELS[phase] ?? PHASE_LABELS.idle}
        </div>
      </section>

      <section className="access-simulation-panel">
        <div className="access-progress-head">
          <div>
            <span>Authorization Progress</span>
            <strong>{progressPercent}% complete</strong>
          </div>
          <div className={`access-processing-chip ${isBusy ? "running" : ""}`}>
            {isBusy ? <RefreshCw className="spin" size={15} /> : <ShieldCheck size={15} />}
            {isBusy ? "Processing secure checks" : "Policy checks idle"}
          </div>
        </div>
        <div className="access-progress-track">
          <div style={{ width: `${progressPercent}%` }} />
        </div>
        <div className="access-flow-grid">
          {FLOW_STEPS.map((item, index) => {
            const status = index < completedStepCount ? "done" : index === simulationIndex && isBusy ? "running" : "pending";
            return (
              <div key={item.title} className={`access-flow-card ${status}`}>
                <div className="access-flow-index">{index < completedStepCount ? <CheckCircle2 size={17} /> : index + 1}</div>
                <strong>{item.title}</strong>
                <p>{item.detail}</p>
              </div>
            );
          })}
        </div>
      </section>

      {(errorMsg || successMsg) && (
        <div className={`access-notice ${errorMsg ? "error" : "success"}`}>
          {errorMsg ? <AlertTriangle size={22} /> : <ShieldCheck size={22} />}
          <div>
            <strong>{errorMsg ? "Akses Ditolak / Gagal" : "Pemberitahuan Sistem"}</strong>
            <p>{errorMsg || successMsg}</p>
          </div>
        </div>
      )}

      <section className="access-workbench-grid">
        <Panel title="Official Workflow" eyebrow={`Step ${step} of 4`} icon={<Landmark />}>
          <div className="access-stepper-rail">
            {["Request", "Approve", "Token", "Viewer"].map((label, index) => {
              const indexStep = index + 1;
              return (
                <div key={label} className={`access-step-dot ${step === indexStep ? "active" : ""} ${step > indexStep ? "done" : ""}`}>
                  <span>{step > indexStep ? <CheckCircle2 size={15} /> : indexStep}</span>
                  <strong>{label}</strong>
                </div>
              );
            })}
          </div>

          <div className="access-action-card">
            {step === 1 && (
              <>
                <div className="access-form-head">
                  <LockKeyhole size={22} />
                  <div>
                    <strong>Lengkapi Permohonan Akses</strong>
                    <p>Semua field akan diasosiasikan dengan audit log request.</p>
                  </div>
                </div>
                <div className="form-grid">
                  <Field label="Record ID Target">
                    <input value={recordId} onChange={(event) => setRecordId(event.target.value)} placeholder="Masukkan Record ID" />
                  </Field>
                  <Field label="Pemohon / Institusi">
                    <input value={requester} onChange={(event) => setRequester(event.target.value)} />
                  </Field>
                </div>
                <Field label="Alasan Akses Resmi">
                  <input value={reason} onChange={(event) => setReason(event.target.value)} />
                </Field>
                <Field label="Government Access Token">
                  <input type="password" value={governmentToken} onChange={(event) => setGovernmentToken(event.target.value)} />
                </Field>
                <button type="button" className="primary-button access-primary-action" onClick={createRequest} disabled={isBusy}>
                  {isBusy ? <RefreshCw className="spin" size={16} /> : <Fingerprint size={16} />}
                  Ajukan Permohonan Akses
                </button>
              </>
            )}

            {step === 2 && (
              <>
                <div className="access-form-head">
                  <UserCheck size={22} />
                  <div>
                    <strong>Otorisasi Approver</strong>
                    <p>Approval menerbitkan token mentah sekali pakai yang hanya ditampilkan satu kali.</p>
                  </div>
                </div>
                <div className="access-summary-box">
                  <div>
                    <span>Request ID</span>
                    <strong>{truncate(requestId, 32)}</strong>
                  </div>
                  <div>
                    <span>Pemohon</span>
                    <strong>{requester}</strong>
                  </div>
                  <div>
                    <span>Alasan</span>
                    <strong>{reason}</strong>
                  </div>
                </div>
                <div className="form-grid">
                  <Field label="Approved By">
                    <input value={approvedBy} onChange={(event) => setApprovedBy(event.target.value)} />
                  </Field>
                  <Field label="Approver Token">
                    <input type="password" value={approverToken} onChange={(event) => setApproverToken(event.target.value)} />
                  </Field>
                </div>
                <button type="button" className="primary-button access-primary-action" onClick={approveRequest} disabled={isBusy}>
                  {isBusy ? <RefreshCw className="spin" size={16} /> : <KeyRound size={16} />}
                  Setujui & Terbitkan Token
                </button>
              </>
            )}

            {step === 3 && (
              <>
                <div className="access-form-head">
                  <KeyRound size={22} />
                  <div>
                    <strong>Verifikasi One-Time Token</strong>
                    <p>Token ini hanya valid untuk satu secure download. Reuse harus gagal.</p>
                  </div>
                </div>
                <div className="access-token-card">
                  <span>One-Time Access Token</span>
                  <strong>{accessToken}</strong>
                </div>
                <button type="button" className="primary-button access-primary-action" onClick={downloadOriginal} disabled={isBusy}>
                  {isBusy ? <RefreshCw className="spin" size={16} /> : <LockKeyhole size={16} />}
                  Verifikasi Token & Buka Vault
                </button>
              </>
            )}

            {step === 4 && (
              <>
                <div className="access-form-head">
                  <Eye size={22} />
                  <div>
                    <strong>Secure Original Ready</strong>
                    <p>Original sudah didekripsi dari vault dan siap ditampilkan dalam secure viewer.</p>
                  </div>
                </div>
                <div className="access-summary-box">
                  <div>
                    <span>Filename</span>
                    <strong>{originalFilename}</strong>
                  </div>
                  <div>
                    <span>Token Status</span>
                    <strong>Used after download</strong>
                  </div>
                </div>
                <button type="button" className="primary-button access-primary-action" onClick={openSecureViewer} disabled={!originalBlobUrl}>
                  <Eye size={17} /> Tampilkan Dokumen Original
                </button>
                <button type="button" className="primary-button secondary-button access-secondary-action" onClick={handleCloseViewer}>
                  Akhiri Secure Session
                </button>
              </>
            )}
          </div>
        </Panel>

        <aside className="access-activity-card">
          <div className="access-activity-head">
            <span>Live Simulation</span>
            <strong>Government Gateway</strong>
          </div>
          <div className="access-scanner">
            <div />
          </div>
          <div className="access-log-list">
            <div className={step >= 1 ? "active" : ""}>Record target loaded: {truncate(recordId, 22)}</div>
            <div className={step >= 2 ? "active" : ""}>Request registered: {truncate(requestId, 22)}</div>
            <div className={step >= 3 ? "active" : ""}>Approver authority verified.</div>
            <div className={step >= 3 ? "active" : ""}>One-time token issued and hashed in database.</div>
            <div className={step >= 4 ? "active" : ""}>Vault decryption authorized, token marked as used.</div>
          </div>
          <div className="access-policy-stack">
            <div>
              <ShieldCheck size={18} /> Government token required
            </div>
            <div>
              <KeyRound size={18} /> One-time token cannot be reused
            </div>
            <div>
              <LockKeyhole size={18} /> Original never enters Operational Zone
            </div>
          </div>
        </aside>
      </section>
    </div>
  );
}
