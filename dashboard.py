#!/usr/bin/env python3
"""HostBook CLI — python3 dashboard.py [--db PATH]"""

import os, sqlite3, argparse, socket, subprocess, platform
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "backend/db/hostbook.db"))

R="\033[0m"; BOLD="\033[1m"; CYAN="\033[96m"; GREEN="\033[92m"
YELLOW="\033[93m"; RED="\033[91m"; DIM="\033[2m"; BLUE="\033[94m"

STATUS_CLR = {"available": GREEN, "reserved": YELLOW, "in_use": CYAN,
              "maintenance": RED, "offline": DIM}


def current_host_row():
    hostname = socket.gethostname()

    # OS / product
    try:
        product = subprocess.check_output(
            ["bash", "-c", "source /etc/os-release && echo \"$PRETTY_NAME\""],
            text=True, stderr=subprocess.DEVNULL
        ).strip() or platform.system()
    except Exception:
        product = platform.system()

    # Logged-in users
    try:
        who = subprocess.check_output(["who"], text=True, stderr=subprocess.DEVNULL)
        users = list({line.split()[0] for line in who.strip().splitlines() if line})
        user  = ", ".join(users) if users else os.environ.get("USER", "—")
    except Exception:
        user = os.environ.get("USER", "—")

    # Uptime as schedule
    try:
        with open("/proc/uptime") as f:
            secs = float(f.read().split()[0])
        d, r = divmod(int(secs), 86400)
        h, r = divmod(r, 3600)
        m    = r // 60
        up   = (f"{d}d " if d else "") + (f"{h}h " if h else "") + f"{m}m"
        sched = f"Up {up} (since {(datetime.now() - __import__('timedelta', fromlist=['timedelta']).__class__(seconds=int(secs))).strftime('%H:%M') if False else datetime.fromtimestamp(datetime.now().timestamp() - int(secs)).strftime('%H:%M')})"
    except Exception:
        sched = "—"

    status = "in_use" if users else "available"
    return (hostname, product, user, sched, status)


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

    def sched(rt, s, e, pur):
        if pur == "Permanent":      return "24/7 (Permanent)"
        if pur == "Overtimes only": return "Sat-Sun (Overtimes only)"
        try:
            s, e = datetime.fromisoformat(s), datetime.fromisoformat(e)
        except Exception:
            return "—"
        if rt == "recurring": return f"Weekly (Every {s.strftime('%A')})"
        if rt == "multi_day": return f"Mon-Fri ({s.strftime('%H:%M')} - {e.strftime('%H:%M')})"
        return f"Daily ({s.strftime('%H:%M')} - {e.strftime('%H:%M')})"

    return [(h, p or "—", u, sched(rt, s, e, pur), st)
            for h, p, u, rt, s, e, pur, st in rows]


def render(rows):
    cols   = ["Host", "Product", "User", "Schedule", "Status"]
    widths = [max(len(cols[i]), max(len(r[i]) for r in rows)) for i in range(5)]

    def fmt(vals, header=False):
        parts = []
        for i, v in enumerate(vals):
            w = widths[i]
            if header:              parts.append(f"{BOLD}{v:<{w}}{R}")
            elif i == 0:            parts.append(f"{BOLD}{BLUE}{v:<{w}}{R}")
            elif i == 2:            parts.append(f"{CYAN}{v:<{w}}{R}")
            elif i == 4:            parts.append(f"{STATUS_CLR.get(v,R)}{v:<{w}}{R}")
            else:                   parts.append(f"{v:<{w}}")
        return "  " + "   ".join(parts)

    div  = "  " + "   ".join("─" * w for w in widths)
    now  = datetime.now().strftime("%Y-%m-%d %H:%M")
    host = socket.gethostname()

    print(f"\n  {BOLD}HostBook{R}  {DIM}│{R}  {CYAN}{host}{R}  {DIM}│  {now}{R}\n")
    print(div)
    print(fmt(cols, header=True))
    print(div)
    for r in rows:
        print(fmt(r))
    print(div)

    in_use   = sum(1 for r in rows if r[4] == "in_use")
    reserved = sum(1 for r in rows if r[4] == "reserved")
    print(f"\n  Total {BOLD}{len(rows)}{R}   "
          f"In use {CYAN}{in_use}{R}   "
          f"Reserved {YELLOW}{reserved}{R}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DB_PATH)
    args = ap.parse_args()
    rows = load_db(args.db) or [current_host_row()]
    render(rows)


if __name__ == "__main__":
    main()
