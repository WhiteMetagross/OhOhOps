import { CheckCircle2, ShieldX } from "lucide-react";

type StatusType = "idle" | "running" | "success" | "blocked" | "failed";

export function StatusBanner({ status }: { status: StatusType }) {
  if (status === "idle" || status === "running") return null;

  const success = status === "success";
  const Icon = success ? CheckCircle2 : ShieldX;

  return (
    <div
      role="status"
      className={`flex items-center gap-3 rounded-2xl border p-4 ${
        success
          ? "border-success/30 bg-success/10 text-success"
          : "border-error/30 bg-error/10 text-error"
      }`}
    >
      <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
      <div>
        <p className="text-sm font-bold">{success ? "Fix verified" : "Repair stopped"}</p>
        <p className="mt-0.5 text-xs text-text-muted">
          {success ? "Patch passed validation and deployment logic." : "Review security or execution output."}
        </p>
      </div>
    </div>
  );
}
