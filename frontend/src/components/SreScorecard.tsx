import { ScorecardData } from "../lib/dashboardTypes";

type ScorecardProps = {
  metrics: ScorecardData | null;
};

const formatTokens = (value?: number) => {
  if (value === undefined || value === null) return "Pending";
  return value.toLocaleString();
};

const formatLatency = (value?: number) => {
  if (value === undefined || value === null) return "Pending";
  if (value < 1000) return `${value}ms`;
  return `${(value / 1000).toFixed(1)}s`;
};

const formatRetries = (value?: number) => {
  if (value === undefined || value === null) return "Pending";
  return `${value}`;
};

const OUTCOME_LABEL: Record<ScorecardData["outcome"], string> = {
  success: "Verified",
  blocked: "Blocked",
  failed: "Failed",
};

export function SreScorecard({ metrics }: ScorecardProps) {
  const outcome = metrics?.outcome;
  const outcomeColor =
    outcome === "success"
      ? "text-success drop-shadow-[0_0_10px_rgba(74,222,128,0.35)]"
      : outcome
      ? "text-error drop-shadow-[0_0_10px_rgba(239,68,68,0.35)]"
      : "text-text-main";

  const cards = [
    { label: "Tokens Used", value: formatTokens(metrics?.tokensUsed), color: null },
    { label: "Execution Latency", value: formatLatency(metrics?.latencyMs), color: null },
    { label: "Retry Cycles", value: formatRetries(metrics?.retryCount), color: null },
    { label: "Outcome", value: outcome ? OUTCOME_LABEL[outcome] : "Pending", color: outcomeColor },
  ];

  return (
    <section aria-label="Latest run metrics" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {cards.map((card) => (
        <div
          key={card.label}
          className="sunfire-card px-4 py-4 sm:px-5"
        >
          <p className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-text-muted">{card.label}</p>
          <p
            className={`mt-2 text-xl font-bold sm:text-2xl ${
              card.color ?? "text-text-main"
            }`}
          >
            {card.value}
          </p>
        </div>
      ))}
    </section>
  );
}
