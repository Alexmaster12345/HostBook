import { useQuery } from "@tanstack/react-query";
import { getUtilization, getIdleHosts } from "../api";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

export default function Analytics() {
  const { data: util = [] } = useQuery({ queryKey: ["utilization"], queryFn: () => getUtilization().then(r => r.data) });
  const { data: idle = [] } = useQuery({ queryKey: ["idle"], queryFn: () => getIdleHosts().then(r => r.data) });

  return (
    <div>
      <h1 style={{ margin: "0 0 24px", color: "#1e293b" }}>Analytics</h1>

      <div style={{ background: "#fff", borderRadius: 10, padding: 24, marginBottom: 24 }}>
        <h2 style={{ margin: "0 0 20px", fontSize: 17 }}>Hours Reserved per Server</h2>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={util} margin={{ left: 0, right: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="hostname" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Bar dataKey="total_hours_reserved" fill="#0ea5e9" radius={[4,4,0,0]} name="Hours Reserved" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
        <div style={{ background: "#fff", borderRadius: 10, padding: 24 }}>
          <h2 style={{ margin: "0 0 16px", fontSize: 17 }}>Utilization Summary</h2>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #e2e8f0", color: "#64748b", textAlign: "left" }}>
                {["Host","Reservations","Avg CPU %","Avg RAM %"].map(h => (
                  <th key={h} style={{ padding: "6px 8px", fontSize: 13 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {util.map(r => (
                <tr key={r.asset_id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "8px", fontWeight: 600 }}>{r.hostname}</td>
                  <td style={{ padding: "8px", color: "#475569" }}>{r.total_reservations}</td>
                  <td style={{ padding: "8px", color: "#475569" }}>{r.avg_cpu ?? "—"}</td>
                  <td style={{ padding: "8px", color: "#475569" }}>{r.avg_ram ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div style={{ background: "#fff", borderRadius: 10, padding: 24 }}>
          <h2 style={{ margin: "0 0 16px", fontSize: 17, color: "#ef4444" }}>Idle Hosts (24h+)</h2>
          {idle.length === 0
            ? <p style={{ color: "#94a3b8" }}>No idle hosts detected.</p>
            : idle.map(h => (
              <div key={h.asset_id} style={{ padding: "10px 0", borderBottom: "1px solid #f1f5f9" }}>
                <div style={{ fontWeight: 600 }}>{h.hostname}</div>
                <div style={{ color: "#94a3b8", fontSize: 13 }}>
                  Last seen: {h.last_seen ? new Date(h.last_seen).toLocaleString() : "Never"}
                </div>
              </div>
            ))
          }
        </div>
      </div>
    </div>
  );
}
