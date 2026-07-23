"use client";

import { useState, useEffect } from "react";
import { API_BASE_URL } from "../lib/config";
import { fetchSystemMode } from "../lib/systemClient";
import { Loader2 } from "lucide-react";
import { getAuthKey } from "../lib/authKey";

const LOADING_TIPS = [
  "Tree Sitter AST boundaries keep functions and classes intact during retrieval.",
  "Pinecone or ChromaDB powers retrieval for connected source repositories.",
  "Sandbox validation executes proposed patches before deployment.",
  "Proactive mode evaluates telemetry signals for unusual behavior.",
  "Namespaces keep projects and environments isolated.",
  "Static rules and two independent model votes inspect every proposed patch.",
  "Unhealthy deployments restore the original file and restart automatically.",
  "Every embedding provider emits a fixed 3072 value vector.",
  "The operational ledger records agent actions for audit and observability.",
];

export function IngestPanel() {
  const [activeTab, setActiveTab] = useState<"github" | "zip" | "local">("github");
  const [githubUrl, setGithubUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [localPath, setLocalPath] = useState("");
  const [features, setFeatures] = useState<{ local_ingest?: boolean, api_keys?: boolean }>({});
  const [namespace, setNamespace] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [result, setResult] = useState<{ files: number; chunks: number; time: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tipIndex, setTipIndex] = useState(0);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (status === "loading") {
      interval = setInterval(() => {
        setTipIndex((prev) => (prev + 1) % LOADING_TIPS.length);
      }, 8000);
    }
    return () => clearInterval(interval);
  }, [status]);

  useEffect(() => {
    fetchSystemMode()
      .then(data => setFeatures(data.features || {}))
      .catch(err => console.error("Failed to fetch system mode", err));
  }, []);

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("loading");
    setResult(null);
    setError(null);
    setTipIndex(0);

    try {
      let response;
      if (activeTab === "github") {
        if (!githubUrl.trim()) throw new Error("URL required");
        response = await fetch(`${API_BASE_URL}/api/v1/ingest/github`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": `Bearer ${getAuthKey()}` },
          body: JSON.stringify({ github_url: githubUrl.trim(), namespace: namespace.trim() || null }),
        });
      } else if (activeTab === "zip") {
        if (!file) throw new Error("File required");
        const formData = new FormData();
        formData.append("file", file);
        if (namespace.trim()) formData.append("namespace", namespace.trim());
        response = await fetch(`${API_BASE_URL}/api/v1/ingest/upload`, {
          method: "POST",
          headers: { "Authorization": `Bearer ${getAuthKey()}` },
          body: formData,
        });
      } else if (activeTab === "local") {
        if (!localPath.trim()) throw new Error("Local path required");
        response = await fetch(`${API_BASE_URL}/api/v1/ingest`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": `Bearer ${getAuthKey()}` },
          body: JSON.stringify({ directory: localPath.trim(), namespace: namespace.trim() || null }),
        });
      }

      if (!response || !response.ok) {
        const errData = await response?.json().catch(() => ({}));
        throw new Error(errData?.detail || "Ingestion failed");
      }

      const data = await response.json();
      setResult({ files: data.files_processed, chunks: data.chunks_indexed, time: data.elapsed_ms });
      setStatus("success");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "An unknown error occurred");
      setStatus("error");
    }
  };

  return (
    <div className="sunfire-card space-y-4 p-5">
      <div className="flex items-center gap-2 mb-2">
        <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
        <h2 className="text-lg font-bold text-text-main">Sync Workspace / Connect Repository</h2>
      </div>

      <div className="flex gap-2 border-b sunfire-divider pb-2">
        {(["github", "zip", ...(features.local_ingest ? ["local"] as const : [])] as const).map(tab => (
          <button
            key={tab}
            type="button"
            onClick={() => { setActiveTab(tab); setStatus("idle"); }}
            className={`px-3 py-1 text-sm rounded-lg font-medium transition-colors ${
              activeTab === tab ? "bg-primary text-[#231304]" : "text-text-muted hover:text-text-main hover:bg-primary/8"
            }`}
          >
            {tab === "github" ? "GitHub URL" : tab === "zip" ? "ZIP Upload" : "Local Path"}
          </button>
        ))}
      </div>
      
      <form onSubmit={handleIngest} className="space-y-3">
        {activeTab === "github" && (
          <div>
            <label className="block text-xs text-text-muted mb-1 font-medium">GitHub Repository URL</label>
            <input
              type="url"
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              placeholder="https://github.com/user/repo"
              className="sunfire-field px-3 py-2 text-sm placeholder:text-text-muted/50"
              required={activeTab === "github"}
            />
          </div>
        )}

        {activeTab === "zip" && (
          <div>
            <label className="block text-xs text-text-muted mb-1 font-medium">Upload ZIP File</label>
            <input
              type="file"
              accept=".zip"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="sunfire-field px-3 py-2 text-sm file:mr-4 file:rounded file:border-0 file:bg-primary/10 file:px-3 file:py-1 file:text-xs file:font-semibold file:text-primary hover:file:bg-primary/20"
              required={activeTab === "zip"}
            />
          </div>
        )}

        {activeTab === "local" && (
          <div>
            <label className="block text-xs text-text-muted mb-1 font-medium">Local Absolute Path</label>
            <input
              type="text"
              value={localPath}
              onChange={(e) => setLocalPath(e.target.value)}
              placeholder="/sandbox/..."
              className="sunfire-field px-3 py-2 text-sm placeholder:text-text-muted/50"
              required={activeTab === "local"}
            />
          </div>
        )}

        <div>
          <label className="block text-xs text-text-muted mb-1 font-medium">Namespace (Optional)</label>
          <input
            type="text"
            value={namespace}
            onChange={(e) => setNamespace(e.target.value)}
            placeholder="production"
            className="sunfire-field px-3 py-2 text-sm placeholder:text-text-muted/50"
          />
        </div>

        {status === "loading" ? (
          <div className="w-full bg-surface border border-primary/30 p-4 rounded-lg flex flex-col items-center justify-center space-y-3 animate-in fade-in duration-300">
            <Loader2 className="w-6 h-6 text-primary animate-spin" />
            <p className="text-xs text-text-muted text-center italic transition-opacity duration-500 min-h-[32px]">
              {LOADING_TIPS[tipIndex]}
            </p>
          </div>
        ) : (
          <button
            type="submit"
            disabled={(activeTab === "github" && !githubUrl) || (activeTab === "zip" && !file) || (activeTab === "local" && !localPath)}
            className="sunfire-button-muted w-full py-2 text-sm disabled:cursor-not-allowed disabled:opacity-50"
          >
            Run Ingestion
          </button>
        )}
      </form>

      {status === "success" && result && (
        <div className="p-3 bg-success/10 border border-success/30 rounded-lg text-sm">
          <p className="text-success font-semibold flex items-center gap-2">
            Ingestion complete
          </p>
          <ul className="text-text-muted mt-2 space-y-1 text-xs">
            <li>Files processed: <span className="text-text-main font-mono">{result.files}</span></li>
            <li>Chunks indexed: <span className="text-text-main font-mono">{result.chunks}</span></li>
            <li>Time elapsed: <span className="text-text-main font-mono">{result.time}ms</span></li>
          </ul>
        </div>
      )}

      {status === "error" && error && (
        <div className="p-3 bg-error/10 border border-error/30 rounded-lg text-sm">
          <p className="text-error font-semibold flex items-center gap-2">
            Ingestion error
          </p>
          <p className="text-text-muted mt-1 text-xs break-words">{error}</p>
        </div>
      )}
    </div>
  );
}
