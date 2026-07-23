import { CheckCircle2, XCircle } from "lucide-react";
import DiffViewer from "react-diff-viewer-continued";
import type { IncidentData } from "../lib/dashboardTypes";

type IncidentPanelProps = {
  incident: IncidentData;
};

function GateRow({ passed, label }: { passed: boolean; label: string }) {
  return (
    <div className={`flex items-center gap-2 text-sm ${passed ? "text-success" : "text-error"}`}>
      {passed ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
      <span>{label}</span>
    </div>
  );
}

export function IncidentPanel({ incident }: IncidentPanelProps) {
  const cleared = incident.regexPassed && incident.securityPassed;
  const hasOriginal = incident.originalCode.trim().length > 0;

  return (
    <section className="sunfire-card p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-text-main">Active Incident Analysis</h2>
        <span className="text-xs uppercase tracking-widest text-text-muted">Live Diff</span>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-text-main">Security Gate Checklist</h3>
          <div className="space-y-2 rounded-xl border border-primary/20 bg-base/70 p-4">
            <GateRow passed={incident.regexPassed} label="Regex Command Scan" />
            <GateRow passed={incident.securityPassed} label="Model Safety Arbitration" />
          </div>
          <div className="rounded-xl border border-primary/20 bg-base/70 p-4 text-xs text-text-muted">
            {cleared
              ? "All safety gates validated. Patch is eligible for deployment."
              : "Patch blocked by security arbitration. Deployment prevented."}
          </div>
        </div>

        <div className="rounded-xl border border-primary/20 bg-base/70 p-3">
          {hasOriginal ? (
            <DiffViewer
              oldValue={incident.originalCode}
              newValue={incident.proposedPatch}
              splitView
              useDarkTheme
            />
          ) : (
            <div className="space-y-2">
              <p className="text-xs uppercase tracking-widest text-text-muted">
                Proposed File (no prior version on record)
              </p>
              <pre className="max-h-[360px] overflow-auto rounded-lg bg-base/80 p-3 text-xs text-text-main whitespace-pre-wrap">
                {incident.proposedPatch}
              </pre>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
