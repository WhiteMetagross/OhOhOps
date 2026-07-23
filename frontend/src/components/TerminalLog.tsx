import { useEffect, useRef } from "react";

export function TerminalLog({ logs }: { logs: string[] }) {
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <section className="sunfire-card flex h-[440px] flex-col overflow-hidden">
      <div className="sunfire-glass-subtle flex items-center gap-2 border-b sunfire-divider px-4 py-3">
        <span className="h-2.5 w-2.5 rounded-full bg-error" />
        <span className="h-2.5 w-2.5 rounded-full bg-primary" />
        <span className="h-2.5 w-2.5 rounded-full bg-success" />
        <span className="ml-2 text-xs font-semibold uppercase tracking-[0.13em] text-text-muted">
          Live agent output
        </span>
        <span className="ml-auto hidden font-mono text-xs text-text-muted sm:block">
          ohohops@agent
        </span>
      </div>

      <div
        aria-live="polite"
        className="flex-1 space-y-2 overflow-y-auto p-5 font-mono text-xs leading-6 sm:text-sm"
      >
        {logs.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-text-muted">Agent output appears here when a repair cycle starts.</p>
          </div>
        ) : (
          logs.map((log, index) => (
            <div key={`${index}-${log.slice(0, 24)}`}>
              <span
                className={
                  log.includes("[PATCH]")
                    ? "mt-3 block whitespace-pre-wrap rounded-xl border border-success/15 bg-success/5 p-4 text-success"
                    : "block text-text-main"
                }
              >
                <span className="mr-2 text-primary">|</span>
                {log}
              </span>
            </div>
          ))
        )}
        <div ref={logsEndRef} />
      </div>
    </section>
  );
}
