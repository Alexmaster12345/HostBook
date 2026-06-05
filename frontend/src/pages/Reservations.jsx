import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getReservations, createReservation, cancelReservation, getAssets } from "../api";

export default function Reservations() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ asset_id: "", purpose: "", starts_at: "", ends_at: "", reservation_type: "hourly" });
  const [error, setError] = useState("");

  const { data: reservations = [] } = useQuery({ queryKey: ["reservations"], queryFn: () => getReservations().then(r => r.data) });
  const { data: assets = [] } = useQuery({ queryKey: ["assets"], queryFn: () => getAssets().then(r => r.data) });

  const create = useMutation({
    mutationFn: createReservation,
    onSuccess: () => { qc.invalidateQueries(["reservations"]); setShowForm(false); setError(""); },
    onError: (e) => setError(e.response?.data?.detail || "Failed to create reservation"),
  });

  const cancel = useMutation({
    mutationFn: cancelReservation,
    onSuccess: () => qc.invalidateQueries(["reservations"]),
  });

  const submit = (e) => {
    e.preventDefault();
    create.mutate({ ...form, asset_id: Number(form.asset_id) });
  };

  const statusColor = { active: "#22c55e", pending: "#f59e0b", expired: "#94a3b8", cancelled: "#ef4444" };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <h1 style={{ margin: 0, color: "#1e293b" }}>Reservations</h1>
        <button onClick={() => setShowForm(v => !v)}
          style={{ background: "#0ea5e9", color: "#fff", border: "none", padding: "10px 20px", borderRadius: 8, cursor: "pointer", fontWeight: 600 }}>
          + New Reservation
        </button>
      </div>

      {showForm && (
        <form onSubmit={submit} style={{ background: "#fff", padding: 24, borderRadius: 10, marginBottom: 24, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          {error && <div style={{ gridColumn: "1/-1", color: "red" }}>{error}</div>}
          <div>
            <label style={{ display: "block", marginBottom: 4, color: "#475569", fontSize: 13 }}>Server *</label>
            <select value={form.asset_id} onChange={e => setForm(f => ({ ...f, asset_id: e.target.value }))} required
              style={{ width: "100%", padding: 8, border: "1px solid #cbd5e1", borderRadius: 6 }}>
              <option value="">Select a server</option>
              {assets.filter(a => a.status === "available").map(a => (
                <option key={a.id} value={a.id}>{a.hostname} ({a.os})</option>
              ))}
            </select>
          </div>
          <div>
            <label style={{ display: "block", marginBottom: 4, color: "#475569", fontSize: 13 }}>Type</label>
            <select value={form.reservation_type} onChange={e => setForm(f => ({ ...f, reservation_type: e.target.value }))}
              style={{ width: "100%", padding: 8, border: "1px solid #cbd5e1", borderRadius: 6 }}>
              {["hourly","daily","multi_day","recurring"].map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label style={{ display: "block", marginBottom: 4, color: "#475569", fontSize: 13 }}>Starts At *</label>
            <input type="datetime-local" value={form.starts_at} onChange={e => setForm(f => ({ ...f, starts_at: e.target.value }))} required
              style={{ width: "100%", padding: 8, border: "1px solid #cbd5e1", borderRadius: 6, boxSizing: "border-box" }} />
          </div>
          <div>
            <label style={{ display: "block", marginBottom: 4, color: "#475569", fontSize: 13 }}>Ends At *</label>
            <input type="datetime-local" value={form.ends_at} onChange={e => setForm(f => ({ ...f, ends_at: e.target.value }))} required
              style={{ width: "100%", padding: 8, border: "1px solid #cbd5e1", borderRadius: 6, boxSizing: "border-box" }} />
          </div>
          <div style={{ gridColumn: "1/-1" }}>
            <label style={{ display: "block", marginBottom: 4, color: "#475569", fontSize: 13 }}>Purpose</label>
            <input value={form.purpose} onChange={e => setForm(f => ({ ...f, purpose: e.target.value }))} placeholder="e.g. Performance testing"
              style={{ width: "100%", padding: 8, border: "1px solid #cbd5e1", borderRadius: 6, boxSizing: "border-box" }} />
          </div>
          <div style={{ gridColumn: "1/-1", display: "flex", gap: 12 }}>
            <button type="submit" style={{ background: "#22c55e", color: "#fff", border: "none", padding: "10px 24px", borderRadius: 8, cursor: "pointer", fontWeight: 600 }}>Reserve</button>
            <button type="button" onClick={() => setShowForm(false)} style={{ background: "#e2e8f0", border: "none", padding: "10px 24px", borderRadius: 8, cursor: "pointer" }}>Cancel</button>
          </div>
        </form>
      )}

      <div style={{ background: "#fff", borderRadius: 10, padding: 24 }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #e2e8f0", color: "#64748b", textAlign: "left" }}>
              {["ID","Server","Type","Purpose","Starts","Ends","Status",""].map(h => (
                <th key={h} style={{ padding: "8px 12px", fontSize: 13 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {reservations.map(r => (
              <tr key={r.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                <td style={{ padding: "10px 12px", color: "#94a3b8" }}>#{r.id}</td>
                <td style={{ padding: "10px 12px", fontWeight: 600 }}>{assets.find(a => a.id === r.asset_id)?.hostname || r.asset_id}</td>
                <td style={{ padding: "10px 12px", color: "#475569" }}>{r.reservation_type}</td>
                <td style={{ padding: "10px 12px", color: "#475569" }}>{r.purpose || "—"}</td>
                <td style={{ padding: "10px 12px", color: "#475569" }}>{new Date(r.starts_at).toLocaleString()}</td>
                <td style={{ padding: "10px 12px", color: "#475569" }}>{new Date(r.ends_at).toLocaleString()}</td>
                <td style={{ padding: "10px 12px" }}>
                  <span style={{ color: statusColor[r.status], fontWeight: 600 }}>{r.status}</span>
                </td>
                <td style={{ padding: "10px 12px" }}>
                  {["active","pending"].includes(r.status) && (
                    <button onClick={() => cancel.mutate(r.id)}
                      style={{ background: "none", border: "1px solid #ef4444", color: "#ef4444", padding: "4px 12px", borderRadius: 6, cursor: "pointer", fontSize: 13 }}>
                      Cancel
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
