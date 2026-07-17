const configuredApiBaseUrl = String(import.meta.env.VITE_API_BASE_URL ?? "").trim();
const defaultApiBaseUrl = configuredApiBaseUrl || "";
const fallbackApiBaseUrls = [
  defaultApiBaseUrl,
  "",
  "https://127.0.0.1:8000",
  "https://localhost:8000",
];

let activeApiBaseUrl = defaultApiBaseUrl;

export type ApiError = {
  status: number;
  message: string;
  detail?: unknown;
};

export type ApiResult<T> = {
  ok: boolean;
  data?: T;
  error?: ApiError;
};

export type HealthResponse = {
  status: string;
  app: string;
  model_loaded: boolean;
  model_exists: boolean;
  model_loading?: boolean;
  device: string;
  operational_zone: string;
  sovereign_vault: string;
  database: string;
};

export type ModelInfoResponse = Record<string, unknown>;
export type CryptoKeyInfoResponse = Record<string, unknown>;
export type StorageRecordsResponse = { records: Array<Record<string, unknown>> } & Record<string, unknown>;
export type VaultRecordResponse = Record<string, unknown>;
export type RuntimePolicyResponse = { policy?: Record<string, unknown> } & Record<string, unknown>;

export type AuditLog = {
  id: number;
  record_id: string | null;
  zone: string;
  event_type: string;
  actor: string;
  action: string;
  details: Record<string, unknown>;
  created_at: string | null;
};

export type AuditLogFilters = {
  limit?: number;
  recordId?: string;
  zone?: string;
  eventType?: string;
};

export type AuditLogsResponse = {
  logs: AuditLog[];
  count: number;
  filters: Record<string, unknown>;
};

export type RedactionClass = {
  name: string;
  risk_level: string;
  description: string;
};

export type RedactionProfile = {
  profile: string;
  mode: string;
  label_enabled: boolean;
  label_text: string;
  active_classes: string[];
};

export type RedactionConfigResponse = {
  profiles: Record<string, RedactionProfile>;
  allowed_modes: string[];
  classes: RedactionClass[];
  canonical_classes: string[];
};

export type RedactImageInput = {
  file: File;
  confidenceThreshold: number;
  profile: string;
  redactionMode?: string;
  activeClasses?: string;
  disabledClasses?: string;
  useRuntimePolicy?: boolean;
  documentTta?: boolean;
  ttaAngles?: string;
  guardrailEnabled?: boolean;
  guardrailMode?: string;
  authenticityOcr?: boolean;
  performanceMode?: string;
};

export type LiveFrameInput = {
  frameBlob: Blob;
  confidenceThreshold?: number;
  redactionMode?: string;
  activeClasses?: string;
  disabledClasses?: string;
  returnImage?: boolean;
};

export type TurboLiveInput = {
  sessionId?: string;
  cameraIndex?: number;
  confidenceThreshold?: number;
  redactionMode?: string;
  activeClasses?: string;
  disabledClasses?: string;
  targetWidth?: number;
  inferIntervalMs?: number;
  jpegQuality?: number;
  boxHoldMs?: number;
};

function normalizeBaseUrl(value: string) {
  return value.replace(/\/$/, "");
}

function candidateApiBaseUrls() {
  return Array.from(new Set([activeApiBaseUrl, ...fallbackApiBaseUrls].map(normalizeBaseUrl)));
}

async function parseError(response: Response): Promise<ApiError> {
  let detail: unknown = undefined;
  try {
    detail = await response.json();
  } catch {
    detail = await response.text().catch(() => "");
  }
  return {
    status: response.status,
    message: `${response.url} failed: ${response.status}`,
    detail,
  };
}

function shouldTryNextBase(error: ApiError) {
  return error.status === 0 || error.status === 404;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  let lastError: ApiError | null = null;
  for (const baseUrl of candidateApiBaseUrls()) {
    try {
      const response = await fetch(`${baseUrl}${path}`, init);
      if (response.ok) {
        const data = (await response.json()) as T;
        if (
          path === "/api/health" &&
          data &&
          typeof data === "object" &&
          !("model_loading" in data) &&
          candidateApiBaseUrls().length > 1
        ) {
          lastError = {
            status: 404,
            message: `${baseUrl}${path} is an older backend instance`,
            detail: data,
          };
          continue;
        }
        activeApiBaseUrl = baseUrl;
        return data;
      }
      lastError = await parseError(response);
      if (!shouldTryNextBase(lastError)) break;
    } catch (error) {
      lastError = {
        status: 0,
        message: error instanceof Error ? error.message : "Network request failed",
        detail: error,
      };
    }
  }
  throw lastError ?? { status: 0, message: "No API base URL reachable" };
}

async function requestBlob(path: string, init?: RequestInit) {
  let lastError: ApiError | null = null;
  for (const baseUrl of candidateApiBaseUrls()) {
    try {
      const response = await fetch(`${baseUrl}${path}`, init);
      if (response.ok) {
        activeApiBaseUrl = baseUrl;
        return response;
      }
      lastError = await parseError(response);
      if (!shouldTryNextBase(lastError)) break;
    } catch (error) {
      lastError = {
        status: 0,
        message: error instanceof Error ? error.message : "Network request failed",
        detail: error,
      };
    }
  }
  throw lastError ?? { status: 0, message: "No API base URL reachable" };
}

export async function safeRequest<T>(request: () => Promise<T>): Promise<ApiResult<T>> {
  try {
    return { ok: true, data: await request() };
  } catch (error) {
    const fallback: ApiError = {
      status: 0,
      message: error instanceof Error ? error.message : "Unknown request failure",
      detail: error,
    };
    return { ok: false, error: isApiError(error) ? error : fallback };
  }
}

function isApiError(error: unknown): error is ApiError {
  return typeof error === "object" && error !== null && "status" in error && "message" in error;
}

function withParams(path: string, params: URLSearchParams) {
  const query = params.toString();
  return query ? `${path}?${query}` : path;
}

export function getApiBaseUrl() {
  return activeApiBaseUrl || "same-origin /api proxy";
}

export function getApiBaseCandidates() {
  return candidateApiBaseUrls().map((baseUrl) => baseUrl || "same-origin /api proxy");
}

export function buildBackendFileUrl(relativeUrl?: string) {
  if (!relativeUrl) return "";
  if (/^https?:\/\//i.test(relativeUrl)) return relativeUrl.replace(/^http:/i, "https:");
  return `${activeApiBaseUrl}${relativeUrl}`;
}

export function buildBackendWebSocketUrl(path: string) {
  const baseUrl = activeApiBaseUrl || window.location.origin;
  const url = new URL(path, baseUrl);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}

export function getHealth() {
  return requestJson<HealthResponse>("/api/health");
}

export function getModelInfo() {
  return requestJson<ModelInfoResponse>("/api/model-info");
}

export function getRedactionConfig() {
  return requestJson<RedactionConfigResponse>("/api/redaction-config");
}

export function getCryptoKeyInfo() {
  return requestJson<CryptoKeyInfoResponse>("/api/crypto/key-info");
}

export function getStorageRecords(limit = 10) {
  return requestJson<StorageRecordsResponse>(`/api/storage/records?limit=${limit}`);
}

export function getVaultRecord(recordId: string) {
  return requestJson<VaultRecordResponse>(`/api/vault/records/${encodeURIComponent(recordId)}`);
}

export function rotateVaultKey(cryptoAdminToken: string) {
  return requestJson<Record<string, unknown>>("/api/crypto/rotate-vault-key", {
    method: "POST",
    headers: { "X-Crypto-Admin-Token": cryptoAdminToken },
  });
}

export function redactImage(input: RedactImageInput) {
  const formData = new FormData();
  formData.append("file", input.file);

  const params = new URLSearchParams();
  params.set("confidence_threshold", String(input.confidenceThreshold));
  params.set("profile", input.profile);
  params.set("performance_mode", input.performanceMode || "fast");
  params.set("document_tta", String(input.documentTta ?? true));
  if (input.ttaAngles) params.set("tta_angles", input.ttaAngles);
  params.set("guardrail_enabled", String(input.guardrailEnabled ?? true));
  if (input.guardrailMode) params.set("guardrail_mode", input.guardrailMode);
  params.set("authenticity_ocr", String(input.authenticityOcr ?? false));
  if (input.redactionMode && input.redactionMode !== "default") params.set("redaction_mode", input.redactionMode);
  if (input.activeClasses?.trim()) params.set("active_classes", input.activeClasses.trim());
  if (input.disabledClasses?.trim()) params.set("disabled_classes", input.disabledClasses.trim());
  if (input.useRuntimePolicy) params.set("use_runtime_policy", "true");

  return requestJson<Record<string, unknown>>(withParams("/api/redact", params), {
    method: "POST",
    body: formData,
  });
}

export function redactLiveFrame(input: LiveFrameInput) {
  const formData = new FormData();
  formData.append("file", input.frameBlob, "frame.jpg");

  const params = new URLSearchParams();
  params.set("confidence_threshold", String(input.confidenceThreshold ?? 0.25));
  params.set("redaction_mode", input.redactionMode || "blur");
  params.set("return_image", String(input.returnImage ?? true));
  if (input.activeClasses?.trim()) params.set("active_classes", input.activeClasses.trim());
  if (input.disabledClasses?.trim()) params.set("disabled_classes", input.disabledClasses.trim());

  return requestJson<Record<string, unknown>>(withParams("/api/live/redact-frame", params), {
    method: "POST",
    body: formData,
  });
}

export function startTurboLive(input: TurboLiveInput = {}) {
  const params = new URLSearchParams();
  params.set("session_id", input.sessionId || "default");
  params.set("camera_index", String(input.cameraIndex ?? 0));
  params.set("confidence_threshold", String(input.confidenceThreshold ?? 0.25));
  params.set("redaction_mode", input.redactionMode || "blur");
  params.set("active_classes", input.activeClasses || "Wajah");
  params.set("target_width", String(input.targetWidth ?? 320));
  params.set("infer_interval_ms", String(input.inferIntervalMs ?? 180));
  params.set("jpeg_quality", String(input.jpegQuality ?? 75));
  params.set("box_hold_ms", String(input.boxHoldMs ?? 700));
  if (input.disabledClasses?.trim()) params.set("disabled_classes", input.disabledClasses.trim());

  return requestJson<Record<string, unknown>>(withParams("/api/live/turbo/start", params), { method: "POST" });
}

export function stopTurboLive(sessionId = "default") {
  const params = new URLSearchParams();
  params.set("session_id", sessionId);
  return requestJson<Record<string, unknown>>(withParams("/api/live/turbo/stop", params), { method: "POST" });
}

export function getTurboLiveStatus(sessionId = "default") {
  const params = new URLSearchParams();
  params.set("session_id", sessionId);
  return requestJson<Record<string, unknown>>(withParams("/api/live/turbo/status", params));
}

export function buildTurboMjpegUrl(sessionId = "default") {
  const params = new URLSearchParams();
  params.set("session_id", sessionId);
  return `${activeApiBaseUrl}${withParams("/api/live/turbo/mjpeg", params)}`;
}

export function getRuntimePolicy() {
  return requestJson<RuntimePolicyResponse>("/api/runtime-policy");
}

export function updateRuntimePolicy(policy: Record<string, unknown>) {
  return requestJson<RuntimePolicyResponse>("/api/runtime-policy", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(policy),
  });
}

export function resetRuntimePolicy() {
  return requestJson<RuntimePolicyResponse>("/api/runtime-policy/reset", { method: "POST" });
}

export function createGovernmentAccessRequest(input: {
  recordId: string;
  requester: string;
  requesterRole: string;
  reason: string;
  governmentToken: string;
}) {
  const params = new URLSearchParams();
  params.set("record_id", input.recordId);
  params.set("requester", input.requester);
  params.set("requester_role", input.requesterRole);
  params.set("reason", input.reason);
  return requestJson<Record<string, unknown>>(withParams("/api/government/access-requests", params), {
    method: "POST",
    headers: { "X-Government-Token": input.governmentToken },
  });
}

export function approveGovernmentAccessRequest(input: { requestId: string; approvedBy: string; approverToken: string }) {
  const params = new URLSearchParams();
  params.set("approved_by", input.approvedBy);
  return requestJson<Record<string, unknown>>(
    withParams(`/api/government/access-requests/${encodeURIComponent(input.requestId)}/approve`, params),
    { method: "POST", headers: { "X-Approver-Token": input.approverToken } },
  );
}

export function getGovernmentAccessRequest(input: { requestId: string; governmentToken: string }) {
  return requestJson<Record<string, unknown>>(`/api/government/access-requests/${encodeURIComponent(input.requestId)}`, {
    headers: { "X-Government-Token": input.governmentToken },
  });
}

export async function downloadGovernmentOriginal(input: {
  requestId: string;
  accessToken: string;
  governmentToken: string;
}) {
  const params = new URLSearchParams();
  params.set("access_token", input.accessToken);
  const response = await requestBlob(
    withParams(`/api/government/access-requests/${encodeURIComponent(input.requestId)}/secure-original`, params),
    { headers: { "X-Government-Token": input.governmentToken } },
  );
  const blob = await response.blob();
  const filename = response.headers.get("content-disposition")?.match(/filename="(.+)"/)?.[1] || "spectre-original.bin";
  return { blob, filename };
}

export function getAuditLogs({ limit = 50, recordId = "", zone = "", eventType = "" }: AuditLogFilters = {}) {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  if (recordId.trim()) params.set("record_id", recordId.trim());
  if (zone.trim()) params.set("zone", zone.trim());
  if (eventType.trim()) params.set("event_type", eventType.trim());
  return requestJson<AuditLogsResponse>(withParams("/api/audit-logs", params));
}

export function getRequiredBackendEndpoints() {
  return [
    { method: "GET", path: "/api/health", feature: "System readiness" },
    { method: "GET", path: "/api/model-info", feature: "YOLO model status" },
    { method: "GET", path: "/api/redaction-config", feature: "Redaction policy config" },
    { method: "POST", path: "/api/redact", feature: "Government document redaction pipeline" },
    { method: "GET", path: "/api/files/redacted/{filename}", feature: "Redacted image preview/download" },
    { method: "GET", path: "/api/storage/records", feature: "Operational Zone registry" },
    { method: "GET", path: "/api/crypto/key-info", feature: "Sovereign Vault key state" },
    { method: "POST", path: "/api/crypto/rotate-vault-key", feature: "Key rotation" },
    { method: "GET", path: "/api/vault/records/{record_id}", feature: "Vault metadata only" },
    { method: "GET", path: "/api/runtime-policy", feature: "Dynamic Injection current policy" },
    { method: "PUT", path: "/api/runtime-policy", feature: "Dynamic Injection update" },
    { method: "POST", path: "/api/runtime-policy/reset", feature: "Dynamic Injection reset" },
    { method: "POST", path: "/api/government/access-requests", feature: "Create original access request" },
    { method: "POST", path: "/api/government/access-requests/{request_id}/approve", feature: "Approve access request" },
    { method: "GET", path: "/api/government/access-requests/{request_id}", feature: "Access request status" },
    { method: "GET", path: "/api/government/access-requests/{request_id}/secure-original", feature: "One-time original download" },
    { method: "GET", path: "/api/audit-logs", feature: "Security event trace" },
    { method: "WS", path: "/api/live/ws", feature: "Persistent binary-frame detection transport" },
    { method: "POST", path: "/api/live/redact-frame", feature: "Browser camera frame redaction" },
    { method: "POST", path: "/api/live/turbo/start", feature: "Optional local-only backend camera stream" },
    { method: "POST", path: "/api/live/turbo/stop", feature: "Stop optional backend camera stream" },
    { method: "GET", path: "/api/live/turbo/status", feature: "Optional backend camera stream status" },
    { method: "GET", path: "/api/live/turbo/mjpeg", feature: "Optional backend MJPEG redacted output" },
  ];
}
