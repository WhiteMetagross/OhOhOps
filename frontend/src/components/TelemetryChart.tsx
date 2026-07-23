import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
  Customized,
} from "recharts";
import type { TelemetryPoint } from "../lib/dashboardTypes";

type TelemetryChartProps = {
  data: TelemetryPoint[];
};

type CustomizedProps = {
  xAxisMap?: Record<string, { scale: (value: string) => number; bandwidth?: () => number }>;
  offset?: { left: number; top: number; width: number; height: number };
  data?: TelemetryPoint[];
};

const renderAnomalyBands = (props: CustomizedProps) => {
  const xAxis = props.xAxisMap ? props.xAxisMap[Object.keys(props.xAxisMap)[0]] : null;
  const { offset, data } = props;
  if (!xAxis || !offset || !data) return null;

  return data.map((point) => {
    if (!point.isAnomaly) return null;
    const xValue = xAxis.scale(point.timestamp);
    if (Number.isNaN(xValue)) return null;
    const bandWidth = xAxis.bandwidth ? Math.max(8, xAxis.bandwidth()) : 10;
    const x = offset.left + xValue - bandWidth / 2;

    return (
      <rect
        key={`anomaly-${point.timestamp}`}
        x={x}
        y={offset.top}
        width={bandWidth}
        height={offset.height}
        fill="var(--error)"
        fillOpacity={0.16}
      />
    );
  });
};

export function TelemetryChart({ data }: TelemetryChartProps) {
  return (
    <section className="sunfire-card p-5">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-text-main">Telemetry Pulse</h2>
        <p className="text-xs text-text-muted">CPU and error rate</p>
      </div>

      <div className="mt-4 h-[240px]">
        {data.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-text-muted">
            Waiting for telemetry feed
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 10, right: 20, bottom: 0, left: -10 }}>
              <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" stroke="var(--text-muted)" tick={{ fontSize: 10 }} />
              <YAxis stroke="var(--text-muted)" tick={{ fontSize: 10 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--glass-strong)",
                  border: "1px solid var(--line)",
                  borderRadius: "10px",
                  color: "var(--text-main)",
                  backdropFilter: "blur(18px)",
                }}
                labelStyle={{ color: "var(--primary)" }}
              />
              <Customized component={renderAnomalyBands} />
              <Line type="monotone" dataKey="cpu" stroke="var(--primary)" strokeWidth={2.5} dot={false} />
              <Line type="monotone" dataKey="errorRate" stroke="var(--error)" strokeWidth={2.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </section>
  );
}
