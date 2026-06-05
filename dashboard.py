#!/usr/bin/env python3
"""HostBook CLI — python3 dashboard.py [--sample] [--db PATH]"""

import os, sqlite3, argparse, socket
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "backend/db/hostbook.db"))

R="\033[0m"; BOLD="\033[1m"; CYAN="\033[96m"; GREEN="\033[92m"
YELLOW="\033[93m"; RED="\033[91m"; DIM="\033[2m"; BLUE="\033[94m"

STATUS_CLR = {"available": GREEN, "reserved": YELLOW, "in_use": CYAN,
              "maintenance": RED, "offline": DIM}

SAMPLE = [
    ("host-prod-01",  "WebSphere v9.0",    "jsmith",  "multi_day", "2026-06-05 09:00", "2026-06-05 17:00", None,             "reserved"),
    ("host-prod-02",  "OpenShift Cluster", "dnoah",   "recurring", "2026-06-02 00:00", "2099-12-31 23:59", "Permanent",      "in_use"),
    ("host-test-04",  "Oracle DB 19c",     "mrossi",  "daily",     "2026-06-07 00:00", "2026-06-07 23:59", "Overtimes only", "reserved"),
    ("host-dev-09",   "JBoss EAP 7.4",     "alee",    "daily",     "2026-06-05 18:00", "2026-06-06 02:00", None,             "reserved"),
    ("host-stage-03", "SAP HANA",          "v-patel", "recurring", "2026-06-09 00:00", "2026-06-09 23:59", None,             "reserved"),
]


def schedule(rtype, s, e, purpose):
    if purpose == "Permanent":      return "24/7 (Permanent)"
    if purpose == "Overtimes only": return "Sat-Sun (Overtimes only)"
    try:
        s, e = datetime.fromisoformat(s), datetime.fromisoformat(e)
    except Exception:
        return "—"
    if rtype == "recurring":  return f"Weekly (Every {s.strftime('%A')})"
    if rtype == "multi_day":  return f"Mon-Fri ({s.strftime('%H:%M')} - {e.strftime('%H:%M')})"
    return f"Daily ({s.strftime('%H:%M')} - {e.strftime('%H:%M')})"


def load_db(path):
    if not os.path.exists(path): return []
    conn = sqlite3.connect(path)
    rows = conn.execute("""
        SELECT a.hostname, a.os, u.username, r.reservation_type,
               r.starts_at, r.ends_at, r.purpose, a.status
        FROM reservations r
        JOIN assets a ON a.id=r.asset_id
        JOIN users  u ON u.id=r.user_id
        WHERE r.status IN ('active','pending') ORDER BY r.starts_at
    """).fetchall()
    conn.close()
    return rows


def render(rows):
    cols   = ["Host", "Product", "User", "Schedule", "Status"]
    data   = [(h, p or "—", u, schedule(rt, s, e, pur), st)
              for h, p, u, rt, s, e, pur, st in rows]
    widths = [max(len(cols[i]), max((len(r[i]) for r in data), default=0)) for i in range(5)]

    def row_str(vals, header=False):
        parts = []
        for i, v in enumerate(vals):
            w = widths[i]
            if header:
                parts.append(f"{BOLD}{v:<{w}}{R}")
            elif i == 0:   parts.append(f"{BOLD}{BLUE}{v:<{w}}{R}")
            elif i == 2:   parts.append(f"{CYAN}{v:<{w}}{R}")
            elif i == 4:   parts.append(f"{STATUS_CLR.get(v,R)}{v:<{w}}{R}")
            else:          parts.append(f"{v:<{w}}")
        return "  " + "   ".join(parts)

    div = "  " + "   ".join("─" * w for w in widths)

    # ── header ────────────────────────────────────────────────────────
    now  = datetime.now().strftime("%Y-%m-%d %H:%M")
    host = socket.gethostname()
    print(f"\n  {BOLD}HostBook{R}  {DIM}│{R}  {CYAN}{host}{R}  {DIM}│  {now}{R}\n")
    print(div)
    print(row_str(cols, header=True))
    print(div)

    # ── rows ──────────────────────────────────────────────────────────
    for r in data:
        print(row_str(r))

    # ── footer ────────────────────────────────────────────────────────
    print(div)
    total    = len(data)
    in_use   = sum(1 for r in data if r[4] == "in_use")
    reserved = sum(1 for r in data if r[4] == "reserved")
    print(f"\n  Total {BOLD}{total}{R}   "
          f"In use {CYAN}{in_use}{R}   "
          f"Reserved {YELLOW}{reserved}{R}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db",     default=DB_PATH)
    ap.add_argument("--sample", action="store_true")
    args = ap.parse_args()
    rows = SAMPLE if args.sample else (load_db(args.db) or SAMPLE)
    render(rows)


if __name__ == "__main__":
    main()
