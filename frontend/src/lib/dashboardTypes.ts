export type SystemMode = "MANUAL" | "PROACTIVE";

export type TelemetryPoint = {
  timestamp: string;
  cpu: number;
  errorRate: number;
  isAnomaly: boolean;
};

export type ScorecardData = {
  tokensUsed: number;
  latencyMs: number;
  retryCount: number;
  outcome: "success" | "blocked" | "failed";
};

export type IncidentData = {
  originalCode: string;
  proposedPatch: string;
  securityPassed: boolean;
  regexPassed: boolean;
};

export type HealthStatus = {
  status: string;
  dependencies: Record<string, string>;
};

export type LedgerEntry = {
  id?: string | null;
  timestamp?: string | null;
  event_source: string;
  agent_action?: string | null;
  execution_payload?: string | null;
  execution_status?: string | null;
  token_consumption: number;
  compute_latency_ms: number;
  ragas_fidelity_score?: number | null;
};
