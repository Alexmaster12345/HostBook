import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../api";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const { data } = await login(username, password);
      localStorage.setItem("token", data.access_token);
      navigate("/");
    } catch {
      setError("Invalid username or password");
    }
  };

  return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh", background: "#1e293b" }}>
      <form onSubmit={submit} style={{ background: "#fff", padding: 40, borderRadius: 12, width: 360, boxShadow: "0 4px 24px rgba(0,0,0,0.2)" }}>
        <h2 style={{ margin: "0 0 8px", color: "#1e293b" }}>HostBook</h2>
        <p style={{ color: "#64748b", marginBottom: 24 }}>Sign in to your account</p>
        {error && <div style={{ color: "red", marginBottom: 12 }}>{error}</div>}
        <input value={username} onChange={e => setUsername(e.target.value)}
          placeholder="Username" required
          style={{ width: "100%", padding: 10, marginBottom: 12, border: "1px solid #cbd5e1", borderRadius: 6, boxSizing: "border-box" }} />
        <input value={password} onChange={e => setPassword(e.target.value)}
          type="password" placeholder="Password" required
          style={{ width: "100%", padding: 10, marginBottom: 20, border: "1px solid #cbd5e1", borderRadius: 6, boxSizing: "border-box" }} />
        <button type="submit"
          style={{ width: "100%", padding: 12, background: "#0ea5e9", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontWeight: 600 }}>
          Sign In
        </button>
      </form>
    </div>
  );
}
