"use client";

import { useState } from "react";
import { Activity, ShieldAlert } from "lucide-react";
import { API_BASE_URL } from "../lib/config";
import { getAuthKey } from "../lib/authKey";

interface RunFormProps {
  onRun: (targetFile: string, logs: string[], projectPath: string, reproCommand: string, namespace?: string) => void;
  isRunning: boolean;
  systemMode: "MANUAL" | "PROACTIVE";
  onSystemModeChange: (mode: "MANUAL" | "PROACTIVE") => void;
  onSimulateOutlier: () => Promise<void>;
}

export function RunForm({ onRun, isRunning, systemMode, onSystemModeChange, onSimulateOutlier }: RunFormProps) {
  const [namespace, setNamespace] = useState("");
  const [files, setFiles] = useState<string[]>([]);
  const [targetFile, setTargetFile] = useState("");
  const [reproCommand, setReproCommand] = useState("");
  const [logs, setLogs] = useState("");
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [fetchError, setFetchError] = useState(false);
  const [simulateStatus, setSimulateStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [simulateError, setSimulateError] = useState<string | null>(null);

  const fetchFiles = async () => {
    setLoadingFiles(true);
    setFetchError(false);
    try {
      const url = namespace ? `${API_BASE_URL}/api/v1/ingest/files?namespace=${encodeURIComponent(namespace)}` : `${API_BASE_URL}/api/v1/ingest/files`;
      const res = await fetch(url, {
        headers: {
          "Authorization": `Bearer ${getAuthKey()}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setFiles(data.files || []);
        if (data.files?.length > 0 && !targetFile) {
          setTargetFile(data.files[0]);
        }
      } else {
        setFetchError(true);
      }
    } catch (e) {
      console.error("Failed to fetch ingested files", e);
      setFetchError(true);
    } finally {
      setLoadingFiles(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!reproCommand || !logs) return;
    
    const logsArray = logs.split("\n").filter(l => l.trim() !== "");
    const safeNamespace = namespace.trim() || "default";
    const resolvedProjectPath = `workspaces/${safeNamespace}/codebase`;
    
    onRun(targetFile || "AUTO_DETECT", logsArray, resolvedProjectPath, reproCommand, safeNamespace);
  };

  const handleSimulate = async () => {
    setSimulateStatus("loading");
    setSimulateError(null);
    try {
      await onSimulateOutlier();
      setSimulateStatus("success");
    } catch (error: unknown) {
      setSimulateStatus("error");
      setSimulateError(error instanceof Error ? error.message : "Failed to simulate outlier");
    }
  };

  return (
    <div className="sunfire-card space-y-4 p-5">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-error animate-pulse" />
          <h2 className="text-lg font-bold text-text-main">Anomaly Control</h2>
        </div>
        <div className="sunfire-segmented flex rounded-full border border-primary/20 p-1 text-xs">
          <button
            type="button"
            onClick={() => onSystemModeChange("MANUAL")}
            className={`px-3 py-1 rounded-full transition-colors ${
              systemMode === "MANUAL"
                ? "bg-primary text-[#231304]"
                : "text-text-muted hover:text-text-main"
            }`}
          >
              Manual Triage
          </button>
          <button
            type="button"
            onClick={() => onSystemModeChange("PROACTIVE")}
            className={`px-3 py-1 rounded-full transition-colors ${
              systemMode === "PROACTIVE"
                ? "bg-primary text-[#231304]"
                : "text-text-muted hover:text-text-main"
            }`}
          >
              Proactive Sentinel
          </button>
        </div>
      </div>

      {systemMode === "MANUAL" ? (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-text-muted mb-1 font-medium">Namespace (Filter)</label>
              <input
                type="text"
                value={namespace}
                onChange={(e) => setNamespace(e.target.value)}
                placeholder="Leave empty for all"
                onBlur={() => void fetchFiles()}
                className="sunfire-field px-3 py-2 text-sm placeholder:text-text-muted/50"
              />
            </div>
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="block text-xs text-text-muted font-medium">Target file, optional</label>
                <button
                  type="button"
                  onClick={fetchFiles}
                  className="text-[10px] text-primary hover:underline focus:outline-none"
                >
                  {loadingFiles ? "Loading" : "Refresh"}
                </button>
              </div>
              <select
                value={targetFile}
                onChange={(e) => setTargetFile(e.target.value)}
                className="sunfire-field px-3 py-2 text-sm"
              >
                <option value="">
                  {loadingFiles ? "Loading files" : fetchError ? "Error loading files" : files.length === 0 ? "No files loaded" : "Select target file or leave blank"}
                </option>
                {files.map(f => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs text-text-muted mb-1 font-medium">Reproduction Command</label>
            <input
              type="text"
              value={reproCommand}
              onChange={(e) => setReproCommand(e.target.value)}
              placeholder="python main.py"
              required
              className="sunfire-field px-3 py-2 font-mono text-sm placeholder:text-text-muted/50"
            />
          </div>

          <div>
            <label className="block text-xs text-text-muted mb-1 font-medium">Crash Logs</label>
            <textarea
              value={logs}
              onChange={(e) => setLogs(e.target.value)}
              placeholder="Paste stack trace or error logs here"
              required
              rows={4}
              className="sunfire-field resize-none px-3 py-2 font-mono text-sm placeholder:text-text-muted/50"
            />
          </div>

          <button
            type="submit"
            disabled={isRunning}
            className={`w-full py-2 rounded-lg font-semibold transition-all duration-300 ${
              isRunning
              ? "bg-surface text-text-muted cursor-not-allowed border border-surface"
              : "bg-error text-white hover:opacity-90 hover:scale-[1.02] shadow-[0_0_15px_var(--error)]"
            }`}
          >
            {isRunning ? "Cycle active" : "Run repair graph"}
          </button>
        </form>
      ) : (
        <div className="space-y-4">
          <div className="sunfire-glass-subtle flex flex-col gap-4 rounded-xl border border-primary/25 px-4 py-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="absolute inset-0 rounded-full bg-primary/30 blur-xl animate-pulse" />
                <ShieldAlert className="relative h-8 w-8 text-primary" />
              </div>
              <div>
                <p className="text-sm text-text-muted flex items-center gap-2">
                  Proactive Sentinel
                </p>
                <p className="text-lg font-semibold text-text-main">
                  {simulateStatus === "loading" ? "Simulating" : "Monitoring active"}
                </p>
              </div>
            </div>
            
            <button
              type="button"
              onClick={handleSimulate}
              disabled={simulateStatus === "loading"}
              className="sunfire-button-muted inline-flex items-center justify-center gap-2 px-4 py-2 text-sm disabled:opacity-50"
            >
              <Activity className="h-4 w-4" aria-hidden="true" />
              Simulate anomaly
            </button>
          </div>

          {simulateStatus === "error" && simulateError && (
            <div className="p-3 bg-error/10 border border-error/30 rounded-lg text-sm">
              <p className="text-error font-semibold">Simulation failed</p>
              <p className="text-text-muted mt-1 text-xs break-words">{simulateError}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
