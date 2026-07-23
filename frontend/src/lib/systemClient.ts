import { API_BASE_URL } from "./config";
import { getAuthKey } from "./authKey";
import type { HealthStatus, LedgerEntry } from "./dashboardTypes";

export interface SystemModeResponse {
  deployment_mode: string;
  features: {
    api_keys: boolean;
    local_ingest: boolean;
  };
}

export async function fetchSystemMode(): Promise<SystemModeResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/system/mode`);
  if (!res.ok) throw new Error(`System mode fetch failed: ${res.statusText}`);
  return res.json();
}

/** Fetch per-dependency readiness. The /health endpoint is unauthenticated. */
export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE_URL}/api/v1/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return res.json();
}

/** Fetch the most recent operational-ledger entries (run history). */
export async function fetchLedgerLogs(limit = 20): Promise<LedgerEntry[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/ledger/logs?limit=${limit}`, {
    headers: { Authorization: `Bearer ${getAuthKey()}` },
  });
  if (!res.ok) throw new Error(`Failed to load history: ${res.statusText}`);
  return res.json();
}
