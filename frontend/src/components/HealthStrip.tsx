"use client";

import { useEffect, useState } from "react";
import { fetchHealth } from "../lib/systemClient";
import type { HealthStatus } from "../lib/dashboardTypes";

const DEP_LABELS: Record<string, string> = {
  model: "Model",
  security_arbiters: "Dual security",
  embeddings: "Embeddings",
  embedding_dimension: "3072 vector",
  chroma: "ChromaDB",
  gemini: "Gemini",
  pinecone: "Pinecone",
  docker: "Docker",
  ledger: "Ledger",
};

function statusColor(value: string): string {
  if (/^\d+$/.test(value)) return "bg-primary";
  switch (value) {
    case "ok":
      return "bg-success";
    case "error":
      return "bg-error";
    default:
      return "bg-text-muted/50"; // not_configured / unknown
  }
}

export function HealthStrip() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [unreachable, setUnreachable] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      try {
        const data = await fetchHealth();
        if (!cancelled) {
          setHealth(data);
          setUnreachable(false);
        }
      } catch {
        if (!cancelled) setUnreachable(true);
      }
    };

    poll();
    const interval = setInterval(poll, 15000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const deps = health?.dependencies ?? {};
  const entries = Object.keys(DEP_LABELS).filter((k) => k in deps);

  return (
    <div className="flex flex-wrap items-center gap-3">
      <span className="text-xs uppercase tracking-widest text-text-muted">System</span>
      {unreachable ? (
        <span className="flex items-center gap-1.5 text-xs text-error">
          <span className="w-2 h-2 rounded-full bg-error" />
          Backend unreachable
        </span>
      ) : entries.length === 0 ? (
        <span className="flex items-center gap-1.5 text-xs text-text-muted">
          <span className="w-2 h-2 rounded-full bg-text-muted/50 animate-pulse" />
          Checking
        </span>
      ) : (
        entries.map((key) => (
          <span
            key={key}
            title={`${DEP_LABELS[key]}: ${deps[key]}`}
            className="flex items-center gap-1.5 text-xs text-text-main/80"
          >
            <span className={`w-2 h-2 rounded-full ${statusColor(deps[key])}`} />
            {DEP_LABELS[key]}
          </span>
        ))
      )}
    </div>
  );
}
