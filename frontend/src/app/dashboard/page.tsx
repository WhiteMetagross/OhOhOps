"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Braces, DatabaseZap, RotateCcw, ShieldCheck } from "lucide-react";
import { BrandHeader } from "../../components/BrandHeader";
import { ContextPanel } from "../../components/ContextPanel";
import { IncidentPanel } from "../../components/IncidentPanel";
import { IngestPanel } from "../../components/IngestPanel";
import { LedgerHistory } from "../../components/LedgerHistory";
import { NodeStatusPanel } from "../../components/NodeStatusPanel";
import { RunForm } from "../../components/RunForm";
import { SreScorecard } from "../../components/SreScorecard";
import { StatusBanner } from "../../components/StatusBanner";
import { TelemetryChart } from "../../components/TelemetryChart";
import { TerminalLog } from "../../components/TerminalLog";
import { useGraphStream } from "../../hooks/useGraphStream";
import { getStoredSaasKey } from "../../lib/authKey";
import { API_BASE_URL, API_KEY } from "../../lib/config";
import type {
  IncidentData,
  ScorecardData,
  SystemMode,
  TelemetryPoint,
} from "../../lib/dashboardTypes";

export default function Dashboard() {
  const router = useRouter();
  const { run, isRunning, activeNode, logs, status, finalState } = useGraphStream();
  const [systemMode, setSystemMode] = useState<SystemMode>("MANUAL");
  const [telemetryData, setTelemetryData] = useState<TelemetryPoint[]>([]);
  const [features, setFeatures] = useState<{
    local_ingest?: boolean;
    api_keys?: boolean;
  }>({});

  useEffect(() => {
    import("../../lib/systemClient").then(({ fetchSystemMode }) => {
      fetchSystemMode()
        .then((data) => {
          const nextFeatures = data.features || {};
          setFeatures(nextFeatures);
          if (nextFeatures.api_keys && !getStoredSaasKey()) {
            router.replace("/onboarding?needkey=1");
          }
        })
        .catch(console.error);
    });
  }, [router]);

  useEffect(() => {
    const authKey = getStoredSaasKey() || API_KEY;
    const fetchTelemetry = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/ledger/logs?limit=40`, {
          headers: { Authorization: `Bearer ${authKey}` },
        });
        if (!response.ok) return;

        const ledgerRows: Array<{
          event_source: string;
          execution_payload: string;
          timestamp?: string;
        }> = await response.json();
        const points = ledgerRows
          .filter((row) => row.event_source === "daemon/telemetry" && row.execution_payload)
          .map((row): TelemetryPoint => {
            const extract = (key: string) => {
              const match = row.execution_payload.match(new RegExp(`${key}=([\\d.]+)`));
              return match ? Number.parseFloat(match[1]) : 0;
            };
            const cpu = extract("cpu");
            const errorRate = extract("error_rate");
            return {
              timestamp: row.timestamp
                ? new Date(row.timestamp).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })
                : "",
              cpu,
              errorRate,
              isAnomaly: cpu > 90 || errorRate > 0.1,
            };
          })
          .reverse();

        if (points.length > 0) setTelemetryData(points);
      } catch {
        // Keep last known chart data when ledger is unavailable.
      }
    };

    void fetchTelemetry();
    const intervalId = window.setInterval(fetchTelemetry, 6000);
    return () => window.clearInterval(intervalId);
  }, []);

  const handleRun = (
    targetFile: string,
    initialLogs: string[],
    projectPath: string,
    reproCommand: string,
    namespace?: string,
  ) => {
    run(targetFile, initialLogs, projectPath, reproCommand, namespace);
  };

  const cleared = Boolean(finalState?.security_clearance);
  const scorecardMetrics: ScorecardData | null = finalState
    ? {
        tokensUsed: finalState.token_consumption ?? 0,
        latencyMs: finalState.latency_ms ?? 0,
        retryCount: finalState.retry_count ?? 0,
        outcome: !cleared
          ? "blocked"
          : (finalState.execution_exit_code ?? -1) === 0
            ? "success"
            : "failed",
      }
    : null;

  const activeIncident: IncidentData | null = finalState?.proposed_patch
    ? {
        originalCode: finalState.original_code ?? "",
        proposedPatch: finalState.proposed_patch,
        securityPassed: cleared,
        regexPassed: cleared,
      }
    : null;

  const handleSimulateOutlier = async () => {
    const now = new Date();
    const mockTelemetry: TelemetryPoint[] = Array.from({ length: 10 }, (_, index) => {
      const time = new Date(now.getTime() - (10 - index) * 60000);
      return {
        timestamp: time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        cpu: 30 + (index % 3) * 5,
        errorRate: 1 + (index % 2),
        isAnomaly: false,
      };
    });
    mockTelemetry.push({
      timestamp: now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      cpu: 98,
      errorRate: 85,
      isAnomaly: true,
    });
    setTelemetryData(mockTelemetry);

    window.setTimeout(() => {
      run(
        "system_metrics",
        [
          "SYSTEM ANOMALY TRIPPED: Elevated resource usage detected.",
          "CPU=98.0%, Mem=84.2%, ErrRate=85.0",
        ],
        "workspaces/default/codebase",
        "python main.py",
      );
    }, 1500);
  };

  return (
    <main className="min-h-screen px-4 py-5 sm:px-6 sm:py-7 lg:px-8">
      <div className="mx-auto max-w-[1480px] space-y-6">
        <BrandHeader
          eyebrow="Autonomous SRE control plane"
          title="OhOhOps"
          description="Detect, investigate, validate, and recover from production incidents through one observable repair workflow."
          showHealth
          showSettings={Boolean(features.api_keys)}
        />

        <section
          aria-label="Repair guarantees"
          className="grid grid-cols-2 gap-3 lg:grid-cols-4"
        >
          {[
            { icon: Braces, label: "Tree Sitter AST chunks" },
            { icon: ShieldCheck, label: "Dual model consensus" },
            { icon: RotateCcw, label: "Automatic rollback" },
            { icon: DatabaseZap, label: "3072 value vectors" },
          ].map(({ icon: Icon, label }) => (
            <div
              key={label}
              className="sunfire-glass-subtle flex items-center gap-3 rounded-xl border border-primary/15 px-4 py-3"
            >
              <Icon className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
              <span className="text-xs font-semibold text-text-main sm:text-sm">{label}</span>
            </div>
          ))}
        </section>

        <section className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-center">
          <div>
            <p className="sunfire-kicker">Live operations</p>
            <h2 className="mt-2 text-2xl font-bold tracking-tight text-text-main">
              Repair workspace
            </h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-text-muted">
              Connect source context, submit incident evidence, then follow each graph decision
              from evaluation through deployment.
            </p>
          </div>
          <div className="sunfire-glass-subtle flex items-center gap-3 rounded-xl border border-primary/15 px-4 py-3">
            <span
              className={`h-2.5 w-2.5 rounded-full ${
                isRunning ? "animate-pulse bg-primary" : "bg-success"
              }`}
            />
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
                Agent state
              </p>
              <p className="text-sm font-semibold text-text-main">
                {isRunning ? "Repair cycle active" : "Ready for incident input"}
              </p>
            </div>
          </div>
        </section>

        <SreScorecard metrics={scorecardMetrics} />

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
          <aside className="space-y-6 xl:col-span-4">
            <IngestPanel />
            <NodeStatusPanel
              activeNode={activeNode}
              deploymentStatus={finalState?.deployment_status}
            />
            <StatusBanner status={status} />
          </aside>

          <section className="space-y-6 xl:col-span-8">
            <div className="grid grid-cols-1 gap-6 2xl:grid-cols-2">
              <TelemetryChart data={telemetryData} />
              <RunForm
                onRun={handleRun}
                isRunning={isRunning}
                systemMode={systemMode}
                onSystemModeChange={setSystemMode}
                onSimulateOutlier={handleSimulateOutlier}
              />
            </div>
            <TerminalLog logs={logs} />
          </section>
        </div>

        {activeIncident && <IncidentPanel incident={activeIncident} />}
        <ContextPanel />
        <LedgerHistory reloadKey={finalState} />
      </div>
    </main>
  );
}
