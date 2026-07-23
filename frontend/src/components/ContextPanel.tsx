"use client";

import { useState } from "react";
import { Search, Loader2 } from "lucide-react";
import { streamContextQuery } from "../lib/contextClient";

export function ContextPanel() {
  const [prompt, setPrompt] = useState("");
  const [namespace, setNamespace] = useState("");
  const [answer, setAnswer] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasAsked, setHasAsked] = useState(false);

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || isStreaming) return;

    setIsStreaming(true);
    setAnswer("");
    setError(null);
    setHasAsked(true);

    try {
      for await (const event of streamContextQuery(prompt.trim(), namespace)) {
        if (event.event === "message" && event.text) {
          setAnswer((prev) => prev + event.text);
        } else if (event.event === "error") {
          setError(event.raw || "Stream error");
          break;
        } else if (event.event === "done") {
          break;
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed");
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <section className="sunfire-card space-y-4 p-6">
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
        <h2 className="text-xl font-semibold text-text-main">Codebase Q&amp;A</h2>
        <span className="text-xs uppercase tracking-widest text-text-muted ml-auto">Agentic RAG</span>
      </div>

      <form onSubmit={handleAsk} className="space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-3">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Ask where retry limits, security gates, or deployment logic are defined"
            rows={2}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleAsk(e);
            }}
            className="sunfire-field resize-none px-3 py-2 text-sm placeholder:text-text-muted/50"
          />
          <div className="flex sm:flex-col gap-3">
            <input
              type="text"
              value={namespace}
              onChange={(e) => setNamespace(e.target.value)}
              placeholder="namespace"
              className="sunfire-field w-full px-3 py-2 text-sm placeholder:text-text-muted/50 sm:w-36"
            />
            <button
              type="submit"
              disabled={!prompt.trim() || isStreaming}
              className="sunfire-button flex items-center justify-center gap-2 px-4 py-2 text-sm disabled:cursor-not-allowed"
            >
              {isStreaming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              {isStreaming ? "Asking" : "Ask"}
            </button>
          </div>
        </div>
      </form>

      {error && (
        <div className="p-3 bg-error/10 border border-error/30 rounded-lg text-sm">
          <p className="text-error font-semibold">Query failed</p>
          <p className="text-text-muted mt-1 text-xs break-words">{error}</p>
        </div>
      )}

      {hasAsked && !error && (
        <div className="rounded-xl border border-primary/20 bg-base/70 p-4 min-h-[80px]">
          {answer ? (
            <p className="text-sm text-text-main whitespace-pre-wrap leading-relaxed">
              {answer}
              {isStreaming && <span className="inline-block w-2 h-4 bg-primary/70 ml-0.5 animate-pulse align-middle" />}
            </p>
          ) : (
            <p className="text-sm text-text-muted italic">
              {isStreaming ? "Retrieving context and reasoning" : "No response."}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
