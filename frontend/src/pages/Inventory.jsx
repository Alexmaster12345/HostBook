import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getAssets, createAsset } from "../api";

const ENVS = ["dev", "qa", "staging", "prod", "lab"];
const TYPES = ["physical", "vm", "workstation", "lab"];

export default function Inventory() {
  const qc = useQueryClient();
  const [filter, setFilter] = useState({});
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ hostname: "", os: "", environment: "lab", asset_type: "physical", ip_address: "", cpu_cores: "", ram_gb: "", storage_gb: "", location: "" });

  const { data: assets = [] } = useQuery({
    queryKey: ["assets", filter],
    queryFn: () => getAssets(filter).then(r => r.data),
  });

  const create = useMutation({
    mutationFn: createAsset,
    onSuccess: () => { qc.invalidateQueries(["assets"]); setShowForm(false); },
  });

  const submit = (e) => {
    e.preventDefault();
    create.mutate({ ...form, cpu_cores: Number(form.cpu_cores) || null, ram_gb: Number(form.ram_gb) || null, storage_gb: Number(form.storage_gb) || null });
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <h1 style={{ margin: 0, color: "#1e293b" }}>Server Inventory</h1>
        <button onClick={() => setShowForm(v => !v)}
          style={{ background: "#0ea5e9", color: "#fff", border: "none", padding: "10px 20px", borderRadius: 8, cursor: "pointer", fontWeight: 600 }}>
          + Add Server
        </button>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
        {[["environment", ENVS], ["asset_type", TYPES]].map(([key, opts]) => (
          <select key={key} onChange={e => setFilter(f => ({ ...f, [key]: e.target.value || undefined }))}
            style={{ padding: "8px 12px", border: "1px solid #cbd5e1", borderRadius: 6 }}>
            <option value="">{key === "environment" ? "All Environments" : "All Types"}</option>
            {opts.map(o => <option key={o} value={o}>{o}</option>)}
          </select>
        ))}
      </div>

      {/* Add Form */}
      {showForm && (
        <form onSubmit={submit} style={{ background: "#fff", padding: 24, borderRadius: 10, marginBottom: 24, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          {[["hostname","Hostname*"], ["os","Operating System"], ["ip_address","IP Address"], ["location","Location"], ["cpu_cores","CPU Cores"], ["ram_gb","RAM (GB)"], ["storage_gb","Storage (GB)"]].map(([k, label]) => (
            <div key={k}>
              <label style={{ display: "block", marginBottom: 4, color: "#475569", fontSize: 13 }}>{label}</label>
              <input value={form[k]} onChange={e => setForm(f => ({ ...f, [k]: e.target.value }))} required={k === "hostname"}
                style={{ width: "100%", padding: 8, border: "1px solid #cbd5e1", borderRadius: 6, boxSizing: "border-box" }} />
            </div>
          ))}
          <div>
            <label style={{ display: "block", marginBottom: 4, color: "#475569", fontSize: 13 }}>Environment</label>
            <select value={form.environment} onChange={e => setForm(f => ({ ...f, environment: e.target.value }))}
              style={{ width: "100%", padding: 8, border: "1px solid #cbd5e1", borderRadius: 6 }}>
              {ENVS.map(e => <option key={e} value={e}>{e}</option>)}
            </select>
          </div>
          <div style={{ gridColumn: "1/-1", display: "flex", gap: 12 }}>
            <button type="submit" style={{ background: "#22c55e", color: "#fff", border: "none", padding: "10px 24px", borderRadius: 8, cursor: "pointer", fontWeight: 600 }}>Save</button>
            <button type="button" onClick={() => setShowForm(false)} style={{ background: "#e2e8f0", border: "none", padding: "10px 24px", borderRadius: 8, cursor: "pointer" }}>Cancel</button>
          </div>
        </form>
      )}

      {/* Table */}
      <div style={{ background: "#fff", borderRadius: 10, padding: 24 }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #e2e8f0", color: "#64748b", textAlign: "left" }}>
              {["Hostname","IP","OS","Type","Env","CPU","RAM","Storage","Location","Status"].map(h => (
                <th key={h} style={{ padding: "8px 10px", fontSize: 13 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {assets.map(a => (
              <tr key={a.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                <td style={{ padding: "10px", fontWeight: 600 }}>{a.hostname}</td>
                <td style={{ padding: "10px", color: "#475569" }}>{a.ip_address || "—"}</td>
                <td style={{ padding: "10px", color: "#475569" }}>{a.os || "—"}</td>
                <td style={{ padding: "10px", color: "#475569" }}>{a.asset_type}</td>
                <td style={{ padding: "10px", color: "#475569" }}>{a.environment || "—"}</td>
                <td style={{ padding: "10px", color: "#475569" }}>{a.cpu_cores ? `${a.cpu_cores}c` : "—"}</td>
                <td style={{ padding: "10px", color: "#475569" }}>{a.ram_gb ? `${a.ram_gb}GB` : "—"}</td>
                <td style={{ padding: "10px", color: "#475569" }}>{a.storage_gb ? `${a.storage_gb}GB` : "—"}</td>
                <td style={{ padding: "10px", color: "#475569" }}>{a.location || "—"}</td>
                <td style={{ padding: "10px" }}><span style={{ color: a.status === "available" ? "#22c55e" : "#f59e0b", fontWeight: 600 }}>{a.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
