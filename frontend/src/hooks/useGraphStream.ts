import { useState, useCallback } from "react";
import { GraphStreamEvent } from "../lib/types";
import { streamGraphRun } from "../lib/sseClient";

export function useGraphStream() {
  const [isRunning, setIsRunning] = useState(false);
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [finalState, setFinalState] = useState<GraphStreamEvent["state"] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "running" | "success" | "blocked" | "failed">("idle");

  const run = useCallback(async (targetFile: string, initialLogs: string[], projectPath: string, reproCommand: string, namespace: string = "") => {
    setIsRunning(true);
    setActiveNode(null);
    setLogs(["[SYSTEM] Initializing autonomous repair cycle..."]);
    setFinalState(null);
    setError(null);
    setStatus("running");

    try {
      for await (const event of streamGraphRun(targetFile, initialLogs, projectPath, reproCommand, namespace)) {
        if (event.event === "node_update" && event.state) {
          setActiveNode(event.state.active_node || null);
          if (event.state.latest_message) {
            setLogs(prev => [...prev, `[${event.state?.active_node}] ${event.state?.latest_message}`]);
          }
        } else if (event.event === "complete" && event.state) {
          setActiveNode("END");
          setFinalState(event.state);
          
          if (event.state.security_clearance) {
            if (event.state.execution_exit_code === 0) {
               setStatus("success");
               setLogs(prev => [...prev, "[SYSTEM] Fix verified! Exit Code: 0", `[PATCH]\n${event.state?.proposed_patch}`]);
               
               if (event.state.deployment_status) {
                 if (event.state.deployment_status === "success") {
                    setLogs(prev => [...prev, `[DEPLOYMENT] Project successfully restarted. PID: ${event.state?.deployment_pid}`]);
                 } else if (event.state.deployment_status === "pending_daemon") {
                    setLogs(prev => [...prev, `[DEPLOYMENT] Patch queued for local daemon pickup.`]);
                 } else if (event.state.deployment_status !== "skipped" && event.state.deployment_status !== "disabled") {
                    setLogs(prev => [...prev, `[DEPLOYMENT] Restart failed: ${event.state?.deployment_reason}`]);
                 }
               }
            } else {
               setStatus("failed");
               setLogs(prev => [...prev, `[SYSTEM] Run failed. Exit Code: ${event.state?.execution_exit_code}`]);
            }
          } else {
             setStatus("blocked");
             setLogs(prev => [...prev, "[SYSTEM] Run blocked by security arbitration."]);
          }
        } else if (event.event === "error") {
          setError(event.error || "Unknown stream error");
          setStatus("failed");
          setLogs(prev => [...prev, `[ERROR] ${event.error}`]);
        }
      }
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Unknown stream error";
      setError(message);
      setStatus("failed");
      setLogs(prev => [...prev, `[SYSTEM] Stream failed: ${message}`]);
    } finally {
      setIsRunning(false);
    }
  }, []);

  return { run, isRunning, activeNode, logs, finalState, error, status };
}
