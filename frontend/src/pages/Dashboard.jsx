import { useQuery } from "@tanstack/react-query";
import { getSummary, getAssets } from "../api";

const STATUS_COLOR = {
  available:   "#22c55e",
  reserved:    "#f59e0b",
  in_use:      "#3b82f6",
  maintenance: "#a855f7",
  offline:     "#ef4444",
};

function StatCard({ label, value, color }) {
  return (
    <div style={{ background: "#fff", borderRadius: 10, padding: "20px 24px", flex: 1, borderTop: `4px solid ${color}` }}>
      <div style={{ fontSize: 28, fontWeight: 700, color }}>{value}</div>
      <div style={{ color: "#64748b", marginTop: 4 }}>{label}</div>
    </div>
  );
}

function StatusBadge({ status }) {
  return (
    <span style={{ background: STATUS_COLOR[status] + "22", color: STATUS_COLOR[status],
      padding: "2px 10px", borderRadius: 99, fontSize: 13, fontWeight: 600 }}>
      {status.replace("_", " ")}
    </span>
  );
}

export default function Dashboard() {
  const { data: summary } = useQuery({ queryKey: ["summary"], queryFn: () => getSummary().then(r => r.data) });
  const { data: assets = [] } = useQuery({ queryKey: ["assets"], queryFn: () => getAssets().then(r => r.data) });

  return (
    <div>
      <h1 style={{ margin: "0 0 24px", color: "#1e293b" }}>Dashboard</h1>

      <div style={{ display: "flex", gap: 16, marginBottom: 32, flexWrap: "wrap" }}>
        <StatCard label="Total Hosts"  value={summary?.total ?? "—"}       color="#64748b" />
        <StatCard label="Available"    value={summary?.available ?? "—"}    color="#22c55e" />
        <StatCard label="Reserved"     value={summary?.reserved ?? "—"}     color="#f59e0b" />
        <StatCard label="In Use"       value={summary?.in_use ?? "—"}       color="#3b82f6" />
        <StatCard label="Offline"      value={summary?.offline ?? "—"}      color="#ef4444" />
        <StatCard label="Maintenance"  value={summary?.maintenance ?? "—"}  color="#a855f7" />
      </div>

      <div style={{ background: "#fff", borderRadius: 10, padding: 24 }}>
        <h2 style={{ margin: "0 0 16px", fontSize: 17, color: "#1e293b" }}>All Servers</h2>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #e2e8f0", color: "#64748b", textAlign: "left" }}>
              <th style={{ padding: "8px 12px" }}>Hostname</th>
              <th style={{ padding: "8px 12px" }}>OS</th>
              <th style={{ padding: "8px 12px" }}>Environment</th>
              <th style={{ padding: "8px 12px" }}>Location</th>
              <th style={{ padding: "8px 12px" }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {assets.map(a => (
              <tr key={a.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                <td style={{ padding: "10px 12px", fontWeight: 600 }}>{a.hostname}</td>
                <td style={{ padding: "10px 12px", color: "#475569" }}>{a.os || "—"}</td>
                <td style={{ padding: "10px 12px", color: "#475569" }}>{a.environment || "—"}</td>
                <td style={{ padding: "10px 12px", color: "#475569" }}>{a.location || "—"}</td>
                <td style={{ padding: "10px 12px" }}><StatusBadge status={a.status} /></td>
              </tr>
            ))}
            {!assets.length && (
              <tr><td colSpan={5} style={{ padding: 24, textAlign: "center", color: "#94a3b8" }}>No servers registered yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
