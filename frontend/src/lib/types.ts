export interface GraphStreamStateDelta {
  active_node?: string;
  retry_count?: number;
  execution_exit_code?: number;
  security_clearance?: boolean;
  original_code?: string;
  proposed_patch?: string;
  latest_message?: string;
  token_consumption?: number;
  latency_ms?: number;
  deployment_status?: string | null;
  deployment_pid?: number | null;
  deployment_reason?: string | null;
  deployment_stderr?: string | null;
}

export interface GraphStreamEvent {
  event: "node_update" | "complete" | "error";
  run_id: string;
  node?: string;
  state?: GraphStreamStateDelta;
  error?: string;
}
