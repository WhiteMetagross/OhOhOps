import { CheckCircle2, Circle, LoaderCircle } from "lucide-react";

const nodes = [
  "Evaluation",
  "Context retrieval",
  "Code modification",
  "Dual model consensus",
  "Docker sandbox",
  "Deployment",
];

const mapping: Record<string, string> = {
  evaluation_node: "Evaluation",
  context_node: "Context retrieval",
  modification_node: "Code modification",
  arbitration_node: "Dual model consensus",
  sandbox_node: "Docker sandbox",
  deployment_node: "Deployment",
};

export function NodeStatusPanel({
  activeNode,
  deploymentStatus,
}: {
  activeNode: string | null;
  deploymentStatus?: string | null;
}) {
  const uiNode = mapping[activeNode || ""] || activeNode;
  const activeIndex = nodes.indexOf(uiNode || "");

  return (
    <section className="sunfire-card p-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="sunfire-kicker">Graph trace</p>
          <h2 className="mt-1 text-lg font-bold text-text-main">Repair stages</h2>
        </div>
        <span className="rounded-full border border-primary/15 bg-primary/6 px-2.5 py-1 text-xs text-text-muted">
          Six nodes
        </span>
      </div>

      <ol className="mt-5 space-y-1">
        {nodes.map((node, index) => {
          const pendingDaemon = node === "Deployment" && deploymentStatus === "pending_daemon";
          const active = uiNode === node || pendingDaemon;
          const complete = activeIndex > index || activeNode === "END";
          const Icon = active ? LoaderCircle : complete ? CheckCircle2 : Circle;

          return (
            <li
              key={node}
              className={`flex items-center gap-3 rounded-xl border px-3 py-3 transition ${
                active
                  ? "glow-active border-primary/45 bg-primary/10 text-text-main"
                  : complete
                    ? "border-success/10 bg-success/5 text-text-main"
                    : "border-transparent text-text-muted"
              }`}
            >
              <Icon
                className={`h-4 w-4 shrink-0 ${
                  active ? "animate-spin text-primary" : complete ? "text-success" : "text-text-muted/50"
                }`}
                aria-hidden="true"
              />
              <span className="text-sm font-medium">{node}</span>
              {pendingDaemon && (
                <span className="ml-auto text-xs font-semibold text-warning">Daemon pending</span>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
