// Centralised backend data loading shared by both shells.
import { useCallback, useEffect, useState } from "react";

import {
  ApiResult,
  AuditLog,
  HealthResponse,
  RedactionConfigResponse,
  getAuditLogs,
  getCryptoKeyInfo,
  getHealth,
  getModelInfo,
  getRedactionConfig,
  getStorageRecords,
  safeRequest,
} from "./api";

export type DashboardState = {
  health: ApiResult<HealthResponse>;
  modelInfo: ApiResult<Record<string, unknown>>;
  redactionConfig: ApiResult<RedactionConfigResponse>;
  cryptoKeyInfo: ApiResult<Record<string, unknown>>;
  storageRecords: ApiResult<{ records: Array<Record<string, unknown>> } & Record<string, unknown>>;
  auditLogs: ApiResult<{ logs: AuditLog[]; count: number }>;
};

const emptyResult = <T,>(): ApiResult<T> => ({ ok: false, error: { status: 0, message: "Not loaded" } });

const initialDashboard: DashboardState = {
  health: emptyResult(),
  modelInfo: emptyResult(),
  redactionConfig: emptyResult(),
  cryptoKeyInfo: emptyResult(),
  storageRecords: emptyResult(),
  auditLogs: emptyResult(),
};

export function useDashboard() {
  const [dashboard, setDashboard] = useState<DashboardState>(initialDashboard);
  const [isLoading, setIsLoading] = useState(false);

  const refreshDashboard = useCallback(async () => {
    setIsLoading(true);
    const [health, modelInfo, redactionConfig, cryptoKeyInfo, storageRecords, auditLogs] = await Promise.all([
      safeRequest(getHealth),
      safeRequest(getModelInfo),
      safeRequest(getRedactionConfig),
      safeRequest(getCryptoKeyInfo),
      safeRequest(() => getStorageRecords(20)),
      safeRequest(() => getAuditLogs({ limit: 30 })),
    ]);
    setDashboard({ health, modelInfo, redactionConfig, cryptoKeyInfo, storageRecords, auditLogs });
    setIsLoading(false);
  }, []);

  useEffect(() => {
    void refreshDashboard();
  }, [refreshDashboard]);

  return { dashboard, isLoading, refreshDashboard };
}
