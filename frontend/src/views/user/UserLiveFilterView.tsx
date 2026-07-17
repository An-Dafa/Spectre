import { Camera, RefreshCw, Radio, Settings2, ShieldCheck, Square, Video } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Collapsible } from "../../components/ui/Collapsible";
import { Field } from "../../components/ui/Field";
import { JsonBlock } from "../../components/ui/JsonBlock";
import { MultiSelectDropdown } from "../../components/ui/MultiSelectDropdown";
import { NumericInput } from "../../components/ui/NumericInput";
import {
  buildBackendWebSocketUrl,
  buildTurboMjpegUrl,
  getTurboLiveStatus,
  redactLiveFrame,
  safeRequest,
  startTurboLive,
  stopTurboLive,
} from "../../lib/api";
import { PRIVACY_CLASSES } from "../../lib/constants";
import { DetectionBox, getPaddedBox } from "../../lib/liveCanvas";

type BrowserCameraDevice = {
  deviceId: string;
  label: string;
};

type CameraPipeline = "browser" | "backend";

type LiveDetection = {
  class_name?: string;
  box?: DetectionBox;
};

const PAGE_ASSETS = {
  banner: "" as string,
};

const BACKEND_CAMERA_OPTIONS = [
  { index: 0, label: "Local Backend Camera 0", helper: "Default laptop camera or main webcam." },
  { index: 1, label: "Local Backend Camera 1", helper: "External USB webcam if connected." },
  { index: 2, label: "Local Backend Camera 2", helper: "Virtual camera, OBS, or capture device." },
];

function isCameraAvailableInBrowser() {
  return Boolean(navigator.mediaDevices?.getUserMedia);
}

function isSecureCameraContext() {
  return window.isSecureContext || ["localhost", "127.0.0.1"].includes(window.location.hostname);
}

function isLocalOrPrivateFrontendHost() {
  const host = window.location.hostname;
  if (["localhost", "127.0.0.1", "::1"].includes(host)) return true;
  if (/^10\./.test(host)) return true;
  if (/^192\.168\./.test(host)) return true;
  if (/^172\.(1[6-9]|2\d|3[0-1])\./.test(host)) return true;
  return false;
}

function stopMediaStream(stream: MediaStream | null) {
  stream?.getTracks().forEach((track) => track.stop());
}

function isPermissionDeniedError(error: unknown) {
  return error instanceof DOMException && ["NotAllowedError", "PermissionDeniedError", "SecurityError"].includes(error.name);
}

function cameraErrorMessage(error: unknown) {
  if (error instanceof DOMException) {
    if (isPermissionDeniedError(error)) {
      return "Browser blocked camera access. Click the lock icon in the address bar, set Camera to Allow, then reload.";
    }
    if (error.name === "NotFoundError" || error.name === "DevicesNotFoundError") {
      return "No camera was detected on this device.";
    }
    if (error.name === "NotReadableError" || error.name === "TrackStartError") {
      return "Camera exists but is currently used by another app or blocked by the operating system.";
    }
    if (error.name === "OverconstrainedError" || error.name === "ConstraintNotSatisfiedError") {
      return "The selected camera is unavailable. Choose Default Browser Camera and try again.";
    }
    return error.message || error.name;
  }
  return error instanceof Error ? error.message : "Failed to open browser camera.";
}

function apiErrorMessage(error: { message?: string; detail?: unknown } | undefined, fallback: string) {
  const detail = error?.detail;
  if (detail && typeof detail === "object" && "detail" in detail) {
    return String((detail as Record<string, unknown>).detail);
  }
  if (typeof detail === "string" && detail.trim()) return detail;
  return error?.message || fallback;
}

async function getCameraPermissionState() {
  if (!navigator.permissions?.query) return "unknown";
  try {
    const status = await navigator.permissions.query({ name: "camera" as PermissionName });
    return status.state;
  } catch {
    return "unknown";
  }
}

export function UserLiveFilterView({ isActive }: { isActive: boolean }) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const outputCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const pixelCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const browserSocketRef = useRef<WebSocket | null>(null);
  const browserSocketConfigRef = useRef("");
  const browserHttpFallbackRef = useRef(false);
  const browserTimerRef = useRef<number | null>(null);
  const browserLoopIdRef = useRef(0);
  const browserRenderFrameRef = useRef<number | null>(null);
  const browserRenderedFrameCountRef = useRef(0);
  const browserFrameStartedAtRef = useRef(0);
  const latestDetectionsRef = useRef<LiveDetection[]>([]);
  const latestDetectionShapeRef = useRef({ width: 0, height: 0 });
  const lastDetectionAtRef = useRef(0);
  const statusIntervalRef = useRef<number | null>(null);
  const runningRef = useRef(false);
  const settingsRef = useRef({
    selectedDeviceId: "",
    confidenceThreshold: 0.25,
    redactionMode: "blur",
    activeClasses: ["Wajah"],
    targetWidth: 320,
    inferIntervalMs: 180,
    jpegQuality: 60,
    boxHoldMs: 700,
    selectedCameraLabel: "Default Browser Camera",
  });

  const [sessionId] = useState("default");
  const [cameraPipeline, setCameraPipeline] = useState<CameraPipeline>("browser");
  const [activeSource, setActiveSource] = useState<CameraPipeline | null>(null);
  const [cameraDevices, setCameraDevices] = useState<BrowserCameraDevice[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [backendCameraIndex, setBackendCameraIndex] = useState(0);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.25);
  const [redactionMode, setRedactionMode] = useState("blur");
  const [activeClasses, setActiveClasses] = useState<string[]>(["Wajah"]);
  const [targetWidth, setTargetWidth] = useState(320);
  const [inferIntervalMs, setInferIntervalMs] = useState(180);
  const [jpegQuality, setJpegQuality] = useState(60);
  const [boxHoldMs, setBoxHoldMs] = useState(700);
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [backendStreamUrl, setBackendStreamUrl] = useState("");
  const [mjpegError, setMjpegError] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isBusy, setIsBusy] = useState(false);
  const [running, setRunning] = useState(false);
  const [cameraPermissionState, setCameraPermissionState] = useState("unknown");

  const classOptions = PRIVACY_CLASSES;
  const selectedBrowserCamera =
    cameraDevices.find((camera) => camera.deviceId === selectedDeviceId) ??
    cameraDevices[0] ?? { deviceId: "", label: "Default Browser Camera" };
  const selectedBackendCamera =
    BACKEND_CAMERA_OPTIONS.find((camera) => camera.index === backendCameraIndex) ?? BACKEND_CAMERA_OPTIONS[0];
  const selectedCameraLabel = cameraPipeline === "backend" ? selectedBackendCamera.label : selectedBrowserCamera.label;

  settingsRef.current = {
    selectedDeviceId,
    confidenceThreshold,
    redactionMode,
    activeClasses,
    targetWidth,
    inferIntervalMs,
    jpegQuality,
    boxHoldMs,
    selectedCameraLabel,
  };

  async function refreshCameraDevices() {
    if (!navigator.mediaDevices?.enumerateDevices) {
      setCameraPermissionState("unsupported");
      return;
    }

    try {
      const permissionState = await getCameraPermissionState();
      setCameraPermissionState(permissionState);
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices
        .filter((device) => device.kind === "videoinput")
        .map((device, index) => ({
          deviceId: device.deviceId,
          label: device.label || `Camera ${index}`,
        }));
      setCameraDevices(videoDevices);
      if (!selectedDeviceId && permissionState === "granted" && videoDevices[0]?.deviceId) {
        setSelectedDeviceId(videoDevices[0].deviceId);
      }
    } catch {
      setCameraPermissionState("unknown");
    }
  }

  async function captureFrameBlob() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) return null;
    if (!video.videoWidth || !video.videoHeight) return null;

    const settings = settingsRef.current;
    const width = Math.min(settings.targetWidth, video.videoWidth);
    const height = Math.max(1, Math.round((video.videoHeight / video.videoWidth) * width));
    canvas.width = width;
    canvas.height = height;

    const context = canvas.getContext("2d");
    if (!context) return null;
    context.drawImage(video, 0, 0, width, height);

    return new Promise<Blob | null>((resolve) => {
      canvas.toBlob((blob) => resolve(blob), "image/jpeg", settings.jpegQuality / 100);
    });
  }

  async function requestBrowserCameraStream() {
    const settings = settingsRef.current;
    const baseVideoConstraints: MediaTrackConstraints = {
      width: { ideal: settings.targetWidth },
      frameRate: { ideal: 12, max: 20 },
    };
    const attempts: Array<MediaTrackConstraints | boolean> = [];

    if (settings.selectedDeviceId) {
      attempts.push({ ...baseVideoConstraints, deviceId: { exact: settings.selectedDeviceId } });
    }
    attempts.push({ ...baseVideoConstraints, facingMode: "user" });
    attempts.push(true);

    let lastError: unknown = null;
    for (const video of attempts) {
      try {
        return await navigator.mediaDevices.getUserMedia({ audio: false, video });
      } catch (cameraError) {
        if (isPermissionDeniedError(cameraError)) throw cameraError;
        lastError = cameraError;
      }
    }
    throw lastError ?? new Error("Failed to open browser camera.");
  }

  function applyBrowserDetectionResult(data: Record<string, unknown>) {
    const detections = Array.isArray(data.detections) ? (data.detections as LiveDetection[]) : [];
    if (detections.length > 0) {
      latestDetectionsRef.current = detections;
      const imageShape = data.image_shape as Record<string, unknown> | undefined;
      latestDetectionShapeRef.current = {
        width: Number(imageShape?.width ?? 0),
        height: Number(imageShape?.height ?? 0),
      };
      lastDetectionAtRef.current = performance.now();
    }

    const settings = settingsRef.current;
    setError("");
    setStatus((previous) => ({
      running: true,
      source: browserHttpFallbackRef.current ? "browser_http_fallback" : "browser_websocket",
      camera_label: settings.selectedCameraLabel,
      frame_counter: browserRenderedFrameCountRef.current,
      inference_counter: Number(previous?.inference_counter ?? 0) + 1,
      latest_stats: {
        transport: browserHttpFallbackRef.current ? "HTTP" : "WebSocket",
        inference_size: data.inference_size ?? settings.targetWidth,
        latency_ms: data.latency_ms ?? 0,
        detection_count: data.detection_count ?? 0,
        redacted_count: data.redacted_count ?? 0,
      },
      privacy_policy: data.storage_policy,
    }));
  }

  function renderBrowserFrame() {
    const video = videoRef.current;
    const canvas = outputCanvasRef.current;
    if (!runningRef.current || !streamRef.current || !video || !canvas) return;

    if (video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA && video.videoWidth && video.videoHeight) {
      const settings = settingsRef.current;
      const width = Math.min(settings.targetWidth, video.videoWidth);
      const height = Math.max(1, Math.round((video.videoHeight / video.videoWidth) * width));
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
      }

      const context = canvas.getContext("2d");
      const scratch = pixelCanvasRef.current;
      const scratchContext = scratch?.getContext("2d");
      if (context) {
        context.filter = "none";
        context.imageSmoothingEnabled = true;
        context.drawImage(video, 0, 0, width, height);
        browserRenderedFrameCountRef.current += 1;

        const detectionAge = performance.now() - lastDetectionAtRef.current;
        const detections = detectionAge <= settings.boxHoldMs ? latestDetectionsRef.current : [];
        const detectionShape = latestDetectionShapeRef.current;
        const scaleX = detectionShape.width > 0 ? width / detectionShape.width : 1;
        const scaleY = detectionShape.height > 0 ? height / detectionShape.height : 1;
        for (const detection of detections) {
          if (detection.class_name && !settings.activeClasses.includes(detection.class_name)) continue;
          const rawBox = detection.box;
          if (!rawBox || !Object.values(rawBox).every(Number.isFinite)) continue;
          const box = getPaddedBox({
            x1: rawBox.x1 * scaleX,
            y1: rawBox.y1 * scaleY,
            x2: rawBox.x2 * scaleX,
            y2: rawBox.y2 * scaleY,
          }, width, height);
          if (!box) continue;

          const boxWidth = box.x2 - box.x1;
          const boxHeight = box.y2 - box.y1;
          if (settings.redactionMode === "black_box") {
            context.fillStyle = "#000";
            context.fillRect(box.x1, box.y1, boxWidth, boxHeight);
          } else if (scratch && scratchContext) {
            const pixelated = settings.redactionMode === "pixelate";
            scratch.width = pixelated ? Math.max(1, Math.round(boxWidth / 14)) : boxWidth;
            scratch.height = pixelated ? Math.max(1, Math.round(boxHeight / 14)) : boxHeight;
            scratchContext.drawImage(
              canvas,
              box.x1,
              box.y1,
              boxWidth,
              boxHeight,
              0,
              0,
              scratch.width,
              scratch.height,
            );
            context.save();
            context.imageSmoothingEnabled = !pixelated;
            context.filter = pixelated ? "none" : `blur(${Math.max(10, Math.round(Math.min(boxWidth, boxHeight) * 0.16))}px)`;
            context.drawImage(scratch, 0, 0, scratch.width, scratch.height, box.x1, box.y1, boxWidth, boxHeight);
            context.restore();
          }
        }
      }
    }

    browserRenderFrameRef.current = window.requestAnimationFrame(renderBrowserFrame);
  }

  function startBrowserRenderLoop() {
    if (browserRenderFrameRef.current) window.cancelAnimationFrame(browserRenderFrameRef.current);
    browserRenderFrameRef.current = window.requestAnimationFrame(renderBrowserFrame);
  }

  function stopBrowserRenderLoop() {
    if (browserRenderFrameRef.current) {
      window.cancelAnimationFrame(browserRenderFrameRef.current);
      browserRenderFrameRef.current = null;
    }
    latestDetectionsRef.current = [];
    latestDetectionShapeRef.current = { width: 0, height: 0 };
    lastDetectionAtRef.current = 0;
    browserRenderedFrameCountRef.current = 0;
  }

  function scheduleBrowserFrame(loopId: number, callback: () => void) {
    if (!runningRef.current || loopId !== browserLoopIdRef.current) return;
    const elapsedMs = performance.now() - browserFrameStartedAtRef.current;
    browserTimerRef.current = window.setTimeout(
      callback,
      Math.max(50, settingsRef.current.inferIntervalMs - elapsedMs),
    );
  }

  async function processBrowserFrame(loopId: number) {
    if (!runningRef.current || loopId !== browserLoopIdRef.current) return;
    browserFrameStartedAtRef.current = performance.now();
    try {
      const frameBlob = await captureFrameBlob();
      if (!frameBlob) return;
      const settings = settingsRef.current;
      const response = await safeRequest(() =>
        redactLiveFrame({
          frameBlob,
          confidenceThreshold: settings.confidenceThreshold,
          redactionMode: settings.redactionMode,
          activeClasses: settings.activeClasses.join(","),
          returnImage: false,
        }),
      );
      if (!runningRef.current || loopId !== browserLoopIdRef.current) return;
      if (!response.ok) {
        setError(apiErrorMessage(response.error, "Failed to process live frame."));
        return;
      }
      applyBrowserDetectionResult(response.data ?? {});
    } finally {
      scheduleBrowserFrame(loopId, () => void processBrowserFrame(loopId));
    }
  }

  async function sendBrowserSocketFrame(loopId: number) {
    if (!runningRef.current || loopId !== browserLoopIdRef.current) return;
    const socket = browserSocketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      startBrowserHttpFallback(loopId, "WebSocket unavailable. Using HTTP detection fallback.");
      return;
    }

    const frameBlob = await captureFrameBlob();
    if (!frameBlob || !runningRef.current || loopId !== browserLoopIdRef.current) {
      scheduleBrowserFrame(loopId, () => void sendBrowserSocketFrame(loopId));
      return;
    }

    const settings = settingsRef.current;
    const config = JSON.stringify({
      confidence_threshold: settings.confidenceThreshold,
      redaction_mode: settings.redactionMode,
      active_classes: settings.activeClasses,
    });
    if (config !== browserSocketConfigRef.current) {
      socket.send(config);
      browserSocketConfigRef.current = config;
    }
    browserFrameStartedAtRef.current = performance.now();
    socket.send(frameBlob);
  }

  function startBrowserHttpFallback(loopId: number, reason: string) {
    if (!runningRef.current || loopId !== browserLoopIdRef.current || browserHttpFallbackRef.current) return;
    browserHttpFallbackRef.current = true;
    const socket = browserSocketRef.current;
    browserSocketRef.current = null;
    if (socket) {
      socket.onclose = null;
      socket.onerror = null;
      socket.close();
    }
    setMessage(reason);
    void processBrowserFrame(loopId);
  }

  function startBrowserProcessingLoop() {
    stopBrowserProcessingLoop();
    const loopId = ++browserLoopIdRef.current;
    browserHttpFallbackRef.current = false;
    browserSocketConfigRef.current = "";
    try {
      const socket = new WebSocket(buildBackendWebSocketUrl("/api/live/ws"));
      browserSocketRef.current = socket;
      socket.onopen = () => {
        if (loopId !== browserLoopIdRef.current) return;
        setMessage(`${settingsRef.current.selectedCameraLabel} active over WebSocket detection.`);
        void sendBrowserSocketFrame(loopId);
      };
      socket.onmessage = (event) => {
        if (!runningRef.current || loopId !== browserLoopIdRef.current) return;
        try {
          const data = JSON.parse(String(event.data)) as Record<string, unknown>;
          if (data.type === "error") {
            setError(String(data.message ?? "Live detection failed."));
          } else {
            applyBrowserDetectionResult(data);
          }
        } catch {
          setError("Backend returned an invalid live detection response.");
        }
        scheduleBrowserFrame(loopId, () => void sendBrowserSocketFrame(loopId));
      };
      socket.onerror = () => startBrowserHttpFallback(loopId, "WebSocket failed. Using HTTP detection fallback.");
      socket.onclose = () => startBrowserHttpFallback(loopId, "WebSocket closed. Using HTTP detection fallback.");
    } catch {
      startBrowserHttpFallback(loopId, "WebSocket is unsupported. Using HTTP detection fallback.");
    }
  }

  function stopBrowserProcessingLoop() {
    browserLoopIdRef.current += 1;
    if (browserTimerRef.current) {
      window.clearTimeout(browserTimerRef.current);
      browserTimerRef.current = null;
    }
    const socket = browserSocketRef.current;
    browserSocketRef.current = null;
    if (socket) {
      socket.onclose = null;
      socket.onerror = null;
      socket.close();
    }
    browserHttpFallbackRef.current = false;
    browserSocketConfigRef.current = "";
  }

  async function startBackendLiveCamera(note?: string) {
    setIsBusy(true);
    setError("");
    setMessage(note || "");
    stopBrowserProcessingLoop();
    stopBrowserRenderLoop();
    stopMediaStream(streamRef.current);
    streamRef.current = null;
    setMjpegError(false);

    const response = await safeRequest(() =>
      startTurboLive({
        sessionId,
        cameraIndex: backendCameraIndex,
        confidenceThreshold,
        redactionMode,
        activeClasses: activeClasses.join(","),
        targetWidth,
        inferIntervalMs,
        jpegQuality,
        boxHoldMs,
      }),
    );

    if (!response.ok) {
      runningRef.current = false;
      setRunning(false);
      setActiveSource(null);
      setIsBusy(false);
      setError(apiErrorMessage(response.error, "Failed to start local backend camera."));
      return;
    }

    runningRef.current = true;
    setRunning(true);
    setActiveSource("backend");
    setCameraPipeline("backend");
    setStatus(response.data ?? null);
    setBackendStreamUrl(`${buildTurboMjpegUrl(sessionId)}&t=${Date.now()}`);
    setMessage(note || `${selectedBackendCamera.label} active through local backend camera fallback.`);
    setIsBusy(false);
  }

  async function startBrowserLiveCamera(allowLocalBackendFallback = true) {
    setIsBusy(true);
    setError("");
    setMessage("");

    if (!isSecureCameraContext()) {
      setIsBusy(false);
      setError("Browser camera requires HTTPS or localhost. For local demo, open http://localhost:5173.");
      return;
    }

    if (!isCameraAvailableInBrowser()) {
      setIsBusy(false);
      setError("This browser does not support camera access. Use recent Chrome, Edge, or Firefox.");
      return;
    }

    try {
      stopBrowserProcessingLoop();
      stopBrowserRenderLoop();
      stopMediaStream(streamRef.current);
      const stream = await requestBrowserCameraStream();
      const settings = settingsRef.current;

      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      runningRef.current = true;
      setRunning(true);
      setActiveSource("browser");
      setBackendStreamUrl("");
      setStatus({
        running: true,
        source: "browser_camera",
        camera_label: settings.selectedCameraLabel,
        frame_counter: 0,
        inference_counter: 0,
        latest_stats: {},
      });
      await refreshCameraDevices();
      setCameraPermissionState(await getCameraPermissionState());
      startBrowserRenderLoop();
      startBrowserProcessingLoop();
      setMessage(`${settings.selectedCameraLabel} active. Connecting optimized live detection.`);
    } catch (cameraError) {
      stopBrowserProcessingLoop();
      stopBrowserRenderLoop();
      stopMediaStream(streamRef.current);
      streamRef.current = null;
      runningRef.current = false;
      setRunning(false);
      setActiveSource(null);
      setCameraPermissionState(await getCameraPermissionState());

      if (allowLocalBackendFallback && isLocalOrPrivateFrontendHost()) {
        setIsBusy(false);
        await startBackendLiveCamera("Browser camera was denied. Using Local Backend Camera fallback for local demo.");
        return;
      }

      setError(`${cameraErrorMessage(cameraError)} For deployed demo, the browser permission must be allowed.`);
    } finally {
      setIsBusy(false);
    }
  }

  async function startLiveCamera() {
    if (cameraPipeline === "backend") {
      await startBackendLiveCamera();
      return;
    }
    await startBrowserLiveCamera(true);
  }

  async function stopLiveCamera() {
    setIsBusy(true);
    runningRef.current = false;
    stopBrowserProcessingLoop();
    stopBrowserRenderLoop();
    stopMediaStream(streamRef.current);
    streamRef.current = null;

    if (activeSource === "backend" || cameraPipeline === "backend") {
      await safeRequest(() => stopTurboLive(sessionId));
    }

    setRunning(false);
    setActiveSource(null);
    setBackendStreamUrl("");
    setMjpegError(false);
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setStatus((previous) => ({ ...(previous ?? {}), running: false }));
    setMessage("Live stream stopped.");
    setError("");
    setIsBusy(false);
  }

  useEffect(() => {
    if (isActive) {
      void refreshCameraDevices();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isActive]);

  useEffect(() => {
    if (!running || activeSource !== "backend") return undefined;
    statusIntervalRef.current = window.setInterval(async () => {
      const response = await safeRequest(() => getTurboLiveStatus(sessionId));
      if (response.ok) setStatus(response.data ?? null);
    }, 1500);
    return () => {
      if (statusIntervalRef.current) {
        window.clearInterval(statusIntervalRef.current);
        statusIntervalRef.current = null;
      }
    };
  }, [running, activeSource, sessionId]);

  useEffect(() => {
    return () => {
      runningRef.current = false;
      stopBrowserProcessingLoop();
      stopBrowserRenderLoop();
      stopMediaStream(streamRef.current);
      void safeRequest(() => stopTurboLive(sessionId));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const latestStats = (status?.latest_stats ?? {}) as Record<string, unknown>;
  const sourceLabel =
    activeSource === "backend"
      ? "Local Backend"
      : activeSource === "browser"
        ? "Browser"
        : cameraPipeline === "backend"
          ? "Local Backend"
          : "Browser";

  return (
    <div className="view-stack user-live-page">
      {PAGE_ASSETS.banner && <img className="page-banner" src={PAGE_ASSETS.banner} alt="" />}
      <section className="user-hero user-hero-compact live-hero">
        <div className="user-hero-copy">
          <h1>Live Stream Privacy Filter.</h1>
          <p>
            Browser Camera uses persistent WebSocket detection and local canvas redaction. Local mode can fall back to
            backend OpenCV camera when browser permission is blocked.
          </p>
        </div>
      </section>

      <section className="live-studio-layout">
        <div className="live-stage-card">
          <div className="live-platform-bar">
            <div className={`live-status-chip ${running ? "is-live" : "is-offline"}`}>
              <span />
              {running ? "LIVE" : "OFFLINE"}
            </div>
            <div className="live-stream-title">
              <strong>Spectre Secure Stream</strong>
              <small>{selectedCameraLabel}</small>
            </div>
            <div className="live-platform-count">Source: {sourceLabel}</div>
          </div>

          <div className="live-frame live-platform-frame">
            <video
              ref={videoRef}
              muted
              playsInline
              autoPlay
              style={{
                display: activeSource === "browser" && running ? "block" : "none",
                position: "absolute",
                inset: 0,
                width: "100%",
                height: "100%",
                opacity: 0,
                pointerEvents: "none",
              }}
            />
            <canvas ref={canvasRef} style={{ display: "none" }} />
            <canvas ref={pixelCanvasRef} style={{ display: "none" }} />
            <canvas
              ref={outputCanvasRef}
              style={{
                display: activeSource === "browser" && running ? "block" : "none",
                width: "100%",
                height: "100%",
                objectFit: "contain",
              }}
            />
            {activeSource === "backend" && backendStreamUrl && !mjpegError ? (
              <img
                src={backendStreamUrl}
                alt="Local backend camera MJPEG stream"
                onError={() => {
                  setMjpegError(true);
                  setError("Local backend stream disconnected. Check whether the backend camera is still running.");
                }}
              />
            ) : activeSource === "backend" && mjpegError ? (
              <div className="empty-state live-empty-state">
                <p style={{ color: "#ff6b6b", marginBottom: "12px" }}>Local backend stream disconnected.</p>
                <button
                  type="button"
                  className="live-action-button secondary"
                  onClick={() => {
                    setMjpegError(false);
                    setBackendStreamUrl(`${buildTurboMjpegUrl(sessionId)}&t=${Date.now()}`);
                  }}
                >
                  Reconnect Stream
                </button>
              </div>
            ) : activeSource === "browser" && running ? (
              null
            ) : !running ? (
              <div className="empty-state live-empty-state">
                <Video size={46} />
                <strong>Stream belum berjalan</strong>
                <span>Pilih pipeline kamera dan tekan Start Live untuk mulai redaksi frame.</span>
              </div>
            ) : (
              <div className="empty-state live-empty-state">
                <RefreshCw className="spin" size={34} />
                <strong>Menyiapkan frame redaksi</strong>
                <span>Kamera sudah aktif, backend sedang memproses frame pertama.</span>
              </div>
            )}
          </div>

          <div className="live-control-dock">
            <div className="live-main-actions">
              {!running ? (
                <button type="button" className="live-action-button start" onClick={startLiveCamera} disabled={isBusy}>
                  {isBusy ? <RefreshCw className="spin" size={18} /> : <Radio size={18} />}
                  {isBusy ? "Starting..." : "Start Live"}
                </button>
              ) : (
                <button type="button" className="live-action-button stop" onClick={() => void stopLiveCamera()} disabled={isBusy}>
                  {isBusy ? <RefreshCw className="spin" size={18} /> : <Square size={16} />}
                  {isBusy ? "Stopping..." : "End Stream"}
                </button>
              )}
              <button type="button" className="live-action-button secondary" onClick={() => void refreshCameraDevices()}>
                <RefreshCw size={16} /> Refresh Camera
              </button>
            </div>

            <details className="live-settings-dropdown">
              <summary>
                <Settings2 size={16} /> Stream Settings
              </summary>
              <div className="live-settings-menu">
                <Field label="Camera Pipeline">
                  <select
                    value={cameraPipeline}
                    onChange={(event) => setCameraPipeline(event.target.value as CameraPipeline)}
                    disabled={running}
                  >
                    <option value="browser">Browser Camera - recommended for deploy</option>
                    <option value="backend">Local Backend Camera - local fallback only</option>
                  </select>
                  <small className="field-hint">
                    Browser Camera uses WebSocket detection over HTTPS/WSS. Local Backend Camera uses OpenCV on your
                    laptop and is not for Azure container camera.
                  </small>
                </Field>

                {cameraPipeline === "browser" ? (
                  <Field label="Browser Camera Source">
                    <select
                      value={selectedDeviceId}
                      onChange={(event) => setSelectedDeviceId(event.target.value)}
                      disabled={running}
                    >
                      <option value="">Default Browser Camera</option>
                      {cameraDevices.map((camera) => (
                        <option key={camera.deviceId} value={camera.deviceId}>
                          {camera.label}
                        </option>
                      ))}
                    </select>
                    <small className="field-hint">
                      Permission: {cameraPermissionState}. If labels are hidden, click Start Live and allow camera access.
                    </small>
                  </Field>
                ) : (
                  <Field label="Local Backend Camera Index">
                    <select
                      value={backendCameraIndex}
                      onChange={(event) => setBackendCameraIndex(Number(event.target.value))}
                      disabled={running}
                    >
                      {BACKEND_CAMERA_OPTIONS.map((camera) => (
                        <option key={camera.index} value={camera.index}>
                          {camera.label}
                        </option>
                      ))}
                    </select>
                    <small className="field-hint">{selectedBackendCamera.helper}</small>
                  </Field>
                )}

                <Field label={`Confidence (${confidenceThreshold})`}>
                  <input
                    type="range"
                    min="0.01"
                    max="0.99"
                    step="0.01"
                    value={confidenceThreshold}
                    onChange={(event) => setConfidenceThreshold(Number(event.target.value))}
                  />
                </Field>
                <Field label="Redaction Mode">
                  <select value={redactionMode} onChange={(event) => setRedactionMode(event.target.value)}>
                    <option value="blur">Soft Blur</option>
                    <option value="pixelate">Pixelate</option>
                    <option value="black_box">Black Box</option>
                  </select>
                </Field>
                <Field label="Target Classes">
                  <MultiSelectDropdown
                    label="Kelas"
                    options={classOptions}
                    selected={activeClasses}
                    onChange={setActiveClasses}
                  />
                </Field>
                <div className="form-grid compact-form-grid">
                  <Field label="Frame Width">
                    <NumericInput min={240} max={1280} value={targetWidth} fallbackValue={320} onValueChange={setTargetWidth} />
                  </Field>
                  <Field label="Infer Interval (ms)">
                    <NumericInput
                      min={120}
                      max={2000}
                      value={inferIntervalMs}
                      fallbackValue={180}
                      onValueChange={setInferIntervalMs}
                    />
                  </Field>
                  <Field label="JPEG Quality">
                    <NumericInput min={35} max={95} value={jpegQuality} fallbackValue={60} onValueChange={setJpegQuality} />
                  </Field>
                  <Field label="Box Hold (ms)">
                    <NumericInput min={100} max={5000} value={boxHoldMs} fallbackValue={700} onValueChange={setBoxHoldMs} />
                  </Field>
                </div>
              </div>
            </details>
          </div>

          {(message || error) && <div className={`live-toast ${error ? "error" : "success"}`}>{error || message}</div>}
        </div>

        <aside className="live-side-panel">
          <div className="live-creator-card">
            <div className="live-avatar">
              <Camera size={22} />
            </div>
            <div>
              <strong>{selectedCameraLabel}</strong>
              <span>{sourceLabel} camera pipeline</span>
            </div>
          </div>

          <div className="live-stat-grid">
            <div className="meta-item">
              <span>Frames</span>
              <strong>{String(status?.frame_counter ?? 0)}</strong>
            </div>
            <div className="meta-item">
              <span>Inference</span>
              <strong>{String(status?.inference_counter ?? 0)}</strong>
            </div>
            <div className="meta-item">
              <span>Latency</span>
              <strong>{String(latestStats.latency_ms ?? 0)} ms</strong>
            </div>
            <div className="meta-item">
              <span>Redacted</span>
              <strong>{String(latestStats.redacted_count ?? 0)}</strong>
            </div>
          </div>

          <div className="alert-card success live-privacy-card">
            <ShieldCheck size={24} color="var(--success)" />
            <div>
              <strong>Ephemeral Processing</strong>
              <p>
                Frames are rendered continuously in the browser. Only compressed detection frames are sent
                ephemerally; bounding boxes return over WebSocket and are never stored.
              </p>
            </div>
          </div>

          <Collapsible title="Detail Status">
            <JsonBlock data={status} />
          </Collapsible>
        </aside>
      </section>
    </div>
  );
}
