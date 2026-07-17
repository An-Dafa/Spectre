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
  approveAdminAccessRequest,
  createAdminAccessRequest,
  downloadAdminOriginal,
  safeRequest,
} from "../../lib/api";

const FLOW_STEPS = [
  {
    title: "Request Intake",
    detail: "Record ID, requester, and access reason are recorded as an official request.",
  },
  {
    title: "Audit Registration",
    detail: "The request enters the audit trail before the original can be opened.",
  },
  {
    title: "Approver Gate",
    detail: "An authorized approver validates and issues approval.",
  },
  {
    title: "One-Time Token",
    detail: "A one-time token is issued and is not stored as plaintext.",
  },
  {
    title: "Vault Decryption",
    detail: "The backend validates the token, opens the vault, then marks the token as used.",
  },
  {
    title: "Secure Viewer",
    detail: "The original is shown only in a restricted session and can be ended manually.",
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

export function AdminAccessView({ latestRecordId }: { latestRecordId: string }) {
  const [step, setStep] = useState(1);
  const [recordId, setRecordId] = useState(latestRecordId);
  const [requestId, setRequestId] = useState("");
  const [accessToken, setAccessToken] = useState("");

  const [requester, setRequester] = useState("Admin Officer");
  const [reason, setReason] = useState("Official investigation No. 123/2026");
  const [adminToken, setAdminToken] = useState("spectre-admin-demo-token");
  const [approverToken, setApproverToken] = useState("spectre-approver-demo-token");
  const [approvedBy, setApprovedBy] = useState("Lead Approver");

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
        createAdminAccessRequest({ recordId, requester, requesterRole: "verifier", reason, adminToken }),
      ),
      simulationDelay(),
    ]);
    if (response.ok) {
      setRequestId(String(response.data?.request_id ?? ""));
      setSuccessMsg("Access request recorded. Waiting for authorized approval.");
      setPhase("idle");
      setStep(2);
    } else {
      setFailure(response.error?.message || "Gagal membuat request.");
    }
  }

  async function approveRequest() {
    clearMessages("approving");
    const [response] = await Promise.all([
      safeRequest(() => approveAdminAccessRequest({ requestId, approvedBy, approverToken })),
      simulationDelay(),
    ]);
    if (response.ok) {
      setAccessToken(String(response.data?.one_time_access_token ?? ""));
      setSuccessMsg("Approval is valid. A one-time access token was issued for single use.");
      setPhase("idle");
      setStep(3);
    } else {
      setFailure(response.error?.message || "Gagal menyetujui request.");
    }
  }

  async function downloadOriginal() {
    clearMessages("decrypting");
    const [response] = await Promise.all([
      safeRequest(() => downloadAdminOriginal({ requestId, accessToken, adminToken })),
      simulationDelay(1100),
    ]);
    if (response.ok && response.data) {
      if (originalBlobUrl) URL.revokeObjectURL(originalBlobUrl);
      const url = URL.createObjectURL(response.data.blob);
      setOriginalBlobUrl(url);
      setOriginalFilename(response.data.filename);
      setSuccessMsg("Vault opened through the official path. The original is ready in the secure viewer.");
      setPhase("ready");
      setStep(4);
    } else if (response.error?.status === 403) {
      setFailure("Token is already used, expired, or invalid. Access was denied by the Admin Access API.");
    } else {
      setFailure(response.error?.message || "Failed to retrieve the original document.");
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
    setSuccessMsg("Secure viewer session ended. The one-time token is considered burned and cannot be reused.");
  }

  return (
    <div className="view-stack admin-access-view">
      {viewerUrl && (
        <SecureViewer
          url={viewerUrl}
          title="ORIGINAL DOCUMENT (RESTRICTED ACCESS)"
          onClose={handleCloseViewer}
          isSensitive={true}
        />
      )}

      <section className="access-hero-card">
        <div className="access-hero-icon">
          <Landmark size={32} />
        </div>
        <div className="access-hero-copy">
          <span>Admin Access API</span>
          <h2>Controlled original access with approval, one-time token, and audit trail.</h2>
          <p>
            The original is not opened directly from the frontend. This flow simulates the official path: request,
            approval, one-time token, vault decryption, and secure viewer.
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
            <strong>{errorMsg ? "Access Denied / Failed" : "System Notice"}</strong>
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
                    <strong>Complete Access Request</strong>
                    <p>All fields will be associated with the request audit log.</p>
                  </div>
                </div>
                <div className="form-grid">
                  <Field label="Record ID Target">
                    <input value={recordId} onChange={(event) => setRecordId(event.target.value)} placeholder="Enter Record ID" />
                  </Field>
                  <Field label="Requester / Institution">
                    <input value={requester} onChange={(event) => setRequester(event.target.value)} />
                  </Field>
                </div>
                <Field label="Official Access Reason">
                  <input value={reason} onChange={(event) => setReason(event.target.value)} />
                </Field>
                <Field label="Admin Access Token">
                  <input type="password" value={adminToken} onChange={(event) => setAdminToken(event.target.value)} />
                </Field>
                <button type="button" className="primary-button access-primary-action" onClick={createRequest} disabled={isBusy}>
                  {isBusy ? <RefreshCw className="spin" size={16} /> : <Fingerprint size={16} />}
                  Submit Access Request
                </button>
              </>
            )}

            {step === 2 && (
              <>
                <div className="access-form-head">
                  <UserCheck size={22} />
                  <div>
                    <strong>Approver Authorization</strong>
                    <p>Approval issues a raw one-time token that is shown only once.</p>
                  </div>
                </div>
                <div className="access-summary-box">
                  <div>
                    <span>Request ID</span>
                    <strong>{truncate(requestId, 32)}</strong>
                  </div>
                  <div>
                    <span>Requester</span>
                    <strong>{requester}</strong>
                  </div>
                  <div>
                    <span>Reason</span>
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
                  Approve and Issue Token
                </button>
              </>
            )}

            {step === 3 && (
              <>
                <div className="access-form-head">
                  <KeyRound size={22} />
                  <div>
                    <strong>Verify One-Time Token</strong>
                    <p>This token is valid for one secure download only. Reuse must fail.</p>
                  </div>
                </div>
                <div className="access-token-card">
                  <span>One-Time Access Token</span>
                  <strong>{accessToken}</strong>
                </div>
                <button type="button" className="primary-button access-primary-action" onClick={downloadOriginal} disabled={isBusy}>
                  {isBusy ? <RefreshCw className="spin" size={16} /> : <LockKeyhole size={16} />}
                  Verify Token and Open Vault
                </button>
              </>
            )}

            {step === 4 && (
              <>
                <div className="access-form-head">
                  <Eye size={22} />
                  <div>
                    <strong>Secure Original Ready</strong>
                    <p>The original has been decrypted from the vault and is ready for the secure viewer.</p>
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
                  <Eye size={17} /> Show Original Document
                </button>
                <button type="button" className="primary-button secondary-button access-secondary-action" onClick={handleCloseViewer}>
                  End Secure Session
                </button>
              </>
            )}
          </div>
        </Panel>

        <aside className="access-activity-card">
          <div className="access-activity-head">
            <span>Live Simulation</span>
            <strong>Admin Gateway</strong>
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
              <ShieldCheck size={18} /> Admin token required
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
