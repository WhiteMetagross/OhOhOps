"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, Clipboard, KeyRound, Loader2, RefreshCw } from "lucide-react";
import { BrandHeader } from "../../components/BrandHeader";
import { API_BASE_URL, API_KEY } from "../../lib/config";

interface ApiKey {
  id: string;
  namespace: string;
  label: string;
  created_at: string;
  revoked: boolean;
  last_used_at: string | null;
}

async function getKeyServiceError(response: Response): Promise<string> {
  const body = await response.json().catch(() => ({}));
  if (body.detail === "Ledger unavailable") {
    return "Tenant key storage is unavailable. Configure SUPABASE_DB_URL to enable this page.";
  }
  return body.detail || "Unable to load API keys.";
}

export default function SettingsPage() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [namespace, setNamespace] = useState("");
  const [label, setLabel] = useState("");
  const [generating, setGenerating] = useState(false);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchKeys = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/keys`, {
        headers: { Authorization: `Bearer ${API_KEY}` },
      });
      if (!response.ok) throw new Error(await getKeyServiceError(response));
      setKeys(await response.json());
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : "Unable to load API keys.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/keys`, {
          headers: { Authorization: `Bearer ${API_KEY}` },
        });
        if (!response.ok) throw new Error(await getKeyServiceError(response));
        const data = await response.json();
        if (!cancelled) setKeys(data);
      } catch (fetchError) {
        if (!cancelled) {
          setError(
            fetchError instanceof Error ? fetchError.message : "Unable to load API keys.",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleGenerate = async (event: React.FormEvent) => {
    event.preventDefault();
    setGenerating(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/keys`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${API_KEY}`,
        },
        body: JSON.stringify({ namespace, label }),
      });
      if (!response.ok) throw new Error("Unable to generate API key.");
      const data = await response.json();
      setNewKey(data.raw_key);
      setNamespace("");
      setLabel("");
      await fetchKeys();
    } catch (generateError) {
      setError(
        generateError instanceof Error ? generateError.message : "Unable to generate API key.",
      );
    } finally {
      setGenerating(false);
    }
  };

  const copyToClipboard = async (text: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  };

  return (
    <main className="min-h-screen px-4 py-5 sm:px-6 sm:py-7 lg:px-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <BrandHeader
          eyebrow="Tenant administration"
          title="Access keys"
          description="Create namespace scoped credentials and review service access from one secure workspace."
        />

        {error && (
          <div role="alert" className="rounded-xl border border-error/30 bg-error/10 px-4 py-3 text-sm text-error">
            {error}
          </div>
        )}

        <section className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="sunfire-card-strong min-w-0 p-6 sm:p-7">
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/12 text-primary">
                <KeyRound className="h-5 w-5" aria-hidden="true" />
              </div>
              <div>
                <p className="sunfire-kicker">New credential</p>
                <h2 className="mt-1 text-xl font-bold text-text-main">Generate tenant key</h2>
              </div>
            </div>

            <form onSubmit={handleGenerate} className="mt-6 space-y-4">
              <div>
                <label htmlFor="tenant-namespace" className="text-sm font-semibold text-text-main">
                  Tenant namespace
                </label>
                <input
                  id="tenant-namespace"
                  value={namespace}
                  onChange={(event) => setNamespace(event.target.value)}
                  placeholder="production"
                  required
                  className="sunfire-field mt-2 px-3 py-2.5 text-sm"
                />
              </div>
              <div>
                <label htmlFor="key-label" className="text-sm font-semibold text-text-main">
                  Label
                </label>
                <input
                  id="key-label"
                  value={label}
                  onChange={(event) => setLabel(event.target.value)}
                  placeholder="Primary operations daemon"
                  className="sunfire-field mt-2 px-3 py-2.5 text-sm"
                />
              </div>
              <button
                type="submit"
                disabled={generating || !namespace.trim()}
                className="sunfire-button flex w-full items-center justify-center px-5 py-3 text-sm"
              >
                {generating ? <Loader2 className="h-5 w-5 animate-spin" /> : "Generate key"}
              </button>
            </form>

            {newKey && (
              <div className="mt-5 rounded-xl border border-success/25 bg-success/8 p-4">
                <p className="text-sm font-semibold text-success">Key generated</p>
                <p className="mt-1 text-xs leading-5 text-text-muted">
                  Copy this value now. Stored records contain only its secure hash.
                </p>
                <div className="mt-3 flex items-center gap-2">
                  <code className="sunfire-glass-subtle min-w-0 flex-1 truncate rounded-lg px-3 py-2 text-xs text-text-main">
                    {newKey}
                  </code>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(newKey)}
                    className="sunfire-button-muted inline-flex items-center gap-2 px-3 py-2 text-xs"
                  >
                    {copied ? <Check className="h-4 w-4" /> : <Clipboard className="h-4 w-4" />}
                    {copied ? "Copied" : "Copy"}
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="sunfire-card min-w-0 p-6 sm:p-7">
            <p className="sunfire-kicker">Daemon connection</p>
            <h2 className="mt-2 text-xl font-bold text-text-main">Connect local telemetry</h2>
            <p className="mt-3 text-sm leading-6 text-text-muted">
              Download the daemon from this repository, then provide your deployment URL,
              project directory, and tenant key.
            </p>
            <pre className="sunfire-code mt-6 overflow-x-auto rounded-xl p-5 text-xs leading-6">
              <code>{`Invoke-WebRequest \`
  -Uri "https://raw.githubusercontent.com/WhiteMetagross/OhOhOps/main/frontend/public/ohohops_daemon.py" \`
  -OutFile "ohohops_daemon.py"

python ohohops_daemon.py \`
  --api-key ${newKey || "oh_ops_YOUR_KEY"} \`
  --server-url https://YOUR_OHOHOPS_API \`
  --project-dir "C:\\path\\to\\project"`}</code>
            </pre>
          </div>
        </section>

        <section className="sunfire-card p-6 sm:p-7">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="sunfire-kicker">Credential inventory</p>
              <h2 className="mt-1 text-xl font-bold text-text-main">Tenant keys</h2>
            </div>
            <button
              type="button"
              onClick={fetchKeys}
              disabled={loading}
              className="sunfire-button-muted inline-flex items-center gap-2 px-3 py-2 text-sm"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>

          {loading ? (
            <div className="flex justify-center py-14">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : keys.length === 0 ? (
            <p className="py-12 text-center text-sm text-text-muted">No tenant keys yet.</p>
          ) : (
            <div className="mt-5 overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="border-b sunfire-divider text-xs uppercase tracking-[0.12em] text-text-muted">
                  <tr>
                    <th className="px-3 py-3 font-semibold">Namespace</th>
                    <th className="px-3 py-3 font-semibold">Label</th>
                    <th className="px-3 py-3 font-semibold">Created</th>
                    <th className="px-3 py-3 font-semibold">Last used</th>
                    <th className="px-3 py-3 text-right font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {keys.map((key) => (
                    <tr key={key.id} className="border-b border-primary/8 transition hover:bg-primary/4">
                      <td className="px-3 py-4 font-medium text-text-main">{key.namespace}</td>
                      <td className="px-3 py-4 text-text-muted">{key.label || "No label"}</td>
                      <td className="px-3 py-4 text-text-muted">
                        {new Date(key.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-3 py-4 text-text-muted">
                        {key.last_used_at
                          ? new Date(key.last_used_at).toLocaleDateString()
                          : "Never"}
                      </td>
                      <td className="px-3 py-4 text-right">
                        <span
                          className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${
                            key.revoked
                              ? "border-error/25 bg-error/10 text-error"
                              : "border-success/25 bg-success/10 text-success"
                          }`}
                        >
                          {key.revoked ? "Revoked" : "Active"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
