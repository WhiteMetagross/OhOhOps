"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Check,
  Clipboard,
  Cloud,
  Container,
  KeyRound,
  ShieldCheck,
  TerminalSquare,
} from "lucide-react";
import { BrandHeader } from "../../components/BrandHeader";
import { generateKey, verifyKey } from "../../lib/keysClient";
import { setStoredSaasKey } from "../../lib/authKey";

type SetupMode = "cloud" | "local";

const localSteps = [
  {
    title: "Clone OhOhOps",
    detail: "Get the project and enter its working directory.",
    command: "git clone https://github.com/WhiteMetagross/OhOhOps.git\ncd OhOhOps",
  },
  {
    title: "Create configuration",
    detail: "Copy the example file, then add provider keys only when those services are required.",
    command:
      "Copy-Item backend/.env.example backend/.env\n# DEPLOYMENT_MODE=local\n# SANDBOX_MODE=docker\n# CHROMA_HOST=chromadb",
  },
  {
    title: "Start the stack",
    detail: "Docker Compose builds and starts ChromaDB, FastAPI, and the dashboard.",
    command: "docker compose up --build",
  },
  {
    title: "Verify services",
    detail: "Open the dashboard and confirm the backend health endpoint responds.",
    command:
      "http://localhost:3000\nhttp://localhost:8000/api/v1/health",
  },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<SetupMode>("cloud");
  const [namespace, setNamespace] = useState("");
  const [generating, setGenerating] = useState(false);
  const [generatedKey, setGeneratedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [keyInput, setKeyInput] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [verifyError, setVerifyError] = useState<string | null>(null);
  const [verifiedNamespace, setVerifiedNamespace] = useState<string | null>(null);

  const handleGenerate = async () => {
    setGenerating(true);
    setVerifyError(null);
    try {
      const rawKey = await generateKey(namespace.trim());
      setGeneratedKey(rawKey);
      setKeyInput(rawKey);
    } catch (error) {
      setVerifyError(error instanceof Error ? error.message : "Key generation failed.");
    } finally {
      setGenerating(false);
    }
  };

  const handleVerify = async () => {
    setVerifying(true);
    setVerifyError(null);
    setVerifiedNamespace(null);
    try {
      const result = await verifyKey(keyInput.trim());
      setStoredSaasKey(keyInput.trim());
      setVerifiedNamespace(result.namespace);
    } catch (error) {
      setVerifyError(error instanceof Error ? error.message : "Verification failed.");
    } finally {
      setVerifying(false);
    }
  };

  const copyKey = async () => {
    if (!generatedKey) return;
    await navigator.clipboard.writeText(generatedKey);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  };

  return (
    <main className="min-h-screen px-4 py-5 sm:px-6 sm:py-7 lg:px-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <BrandHeader
          eyebrow="Deployment and access"
          title="Set up OhOhOps"
          description="Choose a deployment model, connect required services, and validate access before opening the repair workspace."
        />

        <section className="sunfire-card p-2" aria-label="Deployment model">
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setActiveTab("cloud")}
              className={`flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold transition ${
                activeTab === "cloud"
                  ? "bg-primary text-[#231304]"
                  : "text-text-muted hover:bg-primary/10 hover:text-text-main"
              }`}
            >
              <Cloud className="h-4 w-4" aria-hidden="true" />
              Managed service
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("local")}
              className={`flex items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold transition ${
                activeTab === "local"
                  ? "bg-primary text-[#231304]"
                  : "text-text-muted hover:bg-primary/10 hover:text-text-main"
              }`}
            >
              <Container className="h-4 w-4" aria-hidden="true" />
              Local Docker
            </button>
          </div>
        </section>

        {activeTab === "cloud" ? (
          <section className="grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
            <div className="sunfire-card p-6 sm:p-7">
              <p className="sunfire-kicker">Access model</p>
              <h2 className="mt-2 text-2xl font-bold text-text-main">Namespace scoped keys</h2>
              <p className="mt-3 text-sm leading-6 text-text-muted">
                Each key maps requests, telemetry, retrieval context, and pending patches to one
                tenant namespace. Store the raw key when created because it is shown once.
              </p>
              <div className="mt-6 space-y-4">
                {[
                  { icon: KeyRound, title: "Generate", text: "Create a key for one namespace." },
                  { icon: ShieldCheck, title: "Verify", text: "Confirm backend acceptance before use." },
                  { icon: TerminalSquare, title: "Connect", text: "Use the same key for dashboard and daemon." },
                ].map(({ icon: Icon, title, text }, index) => (
                  <div key={title} className="flex gap-3">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-primary/20 bg-primary/10 text-primary">
                      <Icon className="h-4 w-4" aria-hidden="true" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-text-main">
                        {index + 1}. {title}
                      </p>
                      <p className="mt-1 text-sm text-text-muted">{text}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="sunfire-card-strong space-y-6 p-6 sm:p-7">
              <div>
                <p className="sunfire-kicker">Step one</p>
                <h2 className="mt-2 text-xl font-bold text-text-main">Create tenant access</h2>
              </div>

              <div className="space-y-2">
                <label htmlFor="namespace" className="text-sm font-semibold text-text-main">
                  Tenant namespace
                </label>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <input
                    id="namespace"
                    value={namespace}
                    onChange={(event) => setNamespace(event.target.value)}
                    placeholder="production"
                    className="sunfire-field flex-1 px-3 py-2.5 text-sm"
                  />
                  <button
                    type="button"
                    onClick={handleGenerate}
                    disabled={generating || !namespace.trim()}
                    className="sunfire-button px-5 py-2.5 text-sm"
                  >
                    {generating ? "Generating" : "Generate key"}
                  </button>
                </div>
              </div>

              {generatedKey && (
                <div className="rounded-xl border border-success/25 bg-success/8 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.13em] text-success">
                    Key ready
                  </p>
                  <div className="mt-2 flex items-center gap-2">
                    <code className="sunfire-glass-subtle min-w-0 flex-1 truncate rounded-lg px-3 py-2 text-xs text-text-main">
                      {generatedKey}
                    </code>
                    <button
                      type="button"
                      onClick={copyKey}
                      className="sunfire-button-muted inline-flex items-center gap-2 px-3 py-2 text-xs"
                    >
                      {copied ? <Check className="h-4 w-4" /> : <Clipboard className="h-4 w-4" />}
                      {copied ? "Copied" : "Copy"}
                    </button>
                  </div>
                </div>
              )}

              <div className="space-y-2 border-t sunfire-divider pt-5">
                <label htmlFor="access-key" className="text-sm font-semibold text-text-main">
                  Verify access key
                </label>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <input
                    id="access-key"
                    value={keyInput}
                    onChange={(event) => {
                      setKeyInput(event.target.value);
                      setVerifiedNamespace(null);
                    }}
                    placeholder="oh_ops_..."
                    className="sunfire-field flex-1 px-3 py-2.5 font-mono text-sm"
                  />
                  <button
                    type="button"
                    onClick={handleVerify}
                    disabled={verifying || !keyInput.trim()}
                    className="sunfire-button-muted px-5 py-2.5 text-sm"
                  >
                    {verifying ? "Verifying" : "Verify key"}
                  </button>
                </div>
                {verifyError && <p className="text-sm text-error">{verifyError}</p>}
                {verifiedNamespace && (
                  <p className="text-sm text-success">
                    Access verified for namespace {verifiedNamespace}.
                  </p>
                )}
              </div>

              <button
                type="button"
                onClick={() => router.push("/dashboard")}
                disabled={!verifiedNamespace}
                className="sunfire-button w-full px-6 py-3 text-sm"
              >
                Open operations workspace
              </button>
            </div>
          </section>
        ) : (
          <section className="sunfire-card p-6 sm:p-8">
            <div className="max-w-3xl">
              <p className="sunfire-kicker">Local deployment</p>
              <h2 className="mt-2 text-2xl font-bold text-text-main">One Compose stack</h2>
              <p className="mt-3 text-sm leading-6 text-text-muted">
                Local mode runs the dashboard, API, ChromaDB, and Docker sandbox workflow on
                your machine. Gemini or another configured model is still required for real patch generation.
              </p>
            </div>

            <ol className="mt-8 grid gap-4 md:grid-cols-2">
              {localSteps.map((step, index) => (
                <li
                  key={step.title}
                  className="sunfire-glass-subtle min-w-0 rounded-2xl border border-primary/12 p-5"
                >
                  <div className="flex items-center gap-3">
                    <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-sm font-black text-[#231304]">
                      {index + 1}
                    </span>
                    <h3 className="font-semibold text-text-main">{step.title}</h3>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-text-muted">{step.detail}</p>
                  <pre className="sunfire-code mt-4 overflow-x-auto rounded-xl p-4 text-xs leading-6">
                    <code>{step.command}</code>
                  </pre>
                </li>
              ))}
            </ol>
          </section>
        )}
      </div>
    </main>
  );
}
