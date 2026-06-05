import { Outlet, NavLink, useNavigate } from "react-router-dom";

const nav = [
  { to: "/",            label: "Dashboard" },
  { to: "/inventory",   label: "Inventory" },
  { to: "/reservations",label: "Reservations" },
  { to: "/analytics",   label: "Analytics" },
];

export default function Layout() {
  const navigate = useNavigate();
  const logout = () => { localStorage.removeItem("token"); navigate("/login"); };

  return (
    <div style={{ display: "flex", minHeight: "100vh", fontFamily: "sans-serif" }}>
      <aside style={{ width: 220, background: "#1e293b", color: "#fff", padding: "24px 0" }}>
        <div style={{ padding: "0 20px 24px", fontSize: 20, fontWeight: 700, borderBottom: "1px solid #334155" }}>
          HostBook
        </div>
        <nav style={{ marginTop: 16 }}>
          {nav.map(({ to, label }) => (
            <NavLink key={to} to={to} end={to === "/"}
              style={({ isActive }) => ({
                display: "block", padding: "10px 20px", color: isActive ? "#38bdf8" : "#cbd5e1",
                textDecoration: "none", background: isActive ? "#0f172a" : "transparent",
              })}>
              {label}
            </NavLink>
          ))}
        </nav>
        <button onClick={logout}
          style={{ position: "absolute", bottom: 24, left: 20, background: "none", border: "1px solid #475569",
            color: "#94a3b8", padding: "8px 16px", cursor: "pointer", borderRadius: 6 }}>
          Logout
        </button>
      </aside>
      <main style={{ flex: 1, padding: 32, background: "#f1f5f9" }}>
        <Outlet />
      </main>
    </div>
  );
}
