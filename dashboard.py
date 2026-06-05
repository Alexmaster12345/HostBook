#!/usr/bin/env python3
"""
HostBook CLI
  python3 dashboard.py              # live auto-refresh
  python3 dashboard.py show         # one-shot table
  python3 dashboard.py add          # add a host
  python3 dashboard.py remove       # remove a host
  python3 dashboard.py reserve      # reserve a host
  python3 dashboard.py release      # release a reservation
  python3 dashboard.py status       # show who is using a host
"""

import os, sys, sqlite3, argparse, socket, subprocess, platform, time, shutil
from datetime import datetime

DB = os.path.join(os.path.dirname(__file__), "hostbook_local.db")

# ── ANSI ──────────────────────────────────────────────────────────────────────
R="\033[0m"; BOLD="\033[1m"; CYAN="\033[96m"; GREEN="\033[92m"
YELLOW="\033[93m"; RED="\033[91m"; DIM="\033[2m"; BLUE="\033[94m"
MAGENTA="\033[95m"

STATUS_CLR = {
    "available":   GREEN,
    "reserved":    YELLOW,
    "in_use":      CYAN,
    "maintenance": RED,
    "offline":     DIM,
}

# ── Database ──────────────────────────────────────────────────────────────────
def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hosts (
            hostname TEXT PRIMARY KEY,
            product  TEXT DEFAULT '—',
            status   TEXT DEFAULT 'available'
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname   TEXT NOT NULL,
            username   TEXT NOT NULL,
            schedule   TEXT NOT NULL,
            reserved_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(hostname) REFERENCES hosts(hostname)
        )""")
    conn.commit()
    return conn


def get_hosts(conn):
    rows = conn.execute("""
        SELECT h.hostname, h.product, h.status,
               r.username, r.schedule, r.reserved_at
        FROM hosts h
        LEFT JOIN reservations r ON r.hostname = h.hostname
        ORDER BY h.hostname
    """).fetchall()
    return [dict(r) for r in rows]


# ── Current host (live data) ───────────────────────────────────────────────
def live_host_info():
    hostname = socket.gethostname()
    try:
        product = subprocess.check_output(
            ["bash", "-c", "source /etc/os-release 2>/dev/null && echo \"$PRETTY_NAME\""],
            text=True, stderr=subprocess.DEVNULL
        ).strip() or platform.system()
    except Exception:
        product = platform.system()

    try:
        who = subprocess.check_output(["who"], text=True, stderr=subprocess.DEVNULL)
        users = list({l.split()[0] for l in who.strip().splitlines() if l})
    except Exception:
        users = []

    try:
        with open("/proc/uptime") as f:
            secs = int(float(f.read().split()[0]))
        d, r = divmod(secs, 86400); h, r = divmod(r, 3600); m = r // 60
        up = (f"{d}d " if d else "") + (f"{h}h " if h else "") + f"{m}m"
        since = datetime.fromtimestamp(datetime.now().timestamp() - secs).strftime("%H:%M")
        uptime = f"Up {up}  (since {since})"
    except Exception:
        uptime = "—"

    return hostname, product, users, uptime


# ── Rendering ─────────────────────────────────────────────────────────────────
def render(rows, live=False):
    cols = ["Host", "Product", "User", "Schedule", "Status"]

    # Inject live host status into its row if it exists in DB
    hostname = socket.gethostname()
    lh, lp, lusers, luptime = live_host_info()

    display = []
    for r in rows:
        h  = r["hostname"]
        p  = r["product"] or "—"
        st = r["status"]
        if r["username"]:
            u    = r["username"]
            sch  = r["schedule"]
        elif h == hostname:
            # live data for current host
            u   = ", ".join(lusers) if lusers else os.environ.get("USER", "—")
            sch = luptime
            st  = "in_use" if lusers else "available"
        else:
            u   = "—"
            sch = "—"
        display.append((h, p, u, sch, st))

    # If DB empty, show current host only
    if not display:
        u   = ", ".join(lusers) if lusers else os.environ.get("USER", "—")
        st  = "in_use" if lusers else "available"
        display = [(lh, lp, u, luptime, st)]

    widths = [max(len(cols[i]), max(len(r[i]) for r in display)) for i in range(5)]

    def fmt(vals, header=False):
        parts = []
        for i, v in enumerate(vals):
            w = widths[i]
            if header:   parts.append(f"{BOLD}{v:<{w}}{R}")
            elif i == 0: parts.append(f"{BOLD}{BLUE}{v:<{w}}{R}")
            elif i == 2: parts.append(f"{CYAN}{v:<{w}}{R}")
            elif i == 4: parts.append(f"{STATUS_CLR.get(v, R)}{v:<{w}}{R}")
            else:        parts.append(f"{v:<{w}}")
        return "  " + "   ".join(parts)

    div = "  " + "   ".join("─" * w for w in widths)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tag = f"  {DIM}live — refreshes every 3s   q=quit{R}" if live else ""

    # Clear and print
    if live:
        print("\033[H\033[J", end="")   # clear screen

    print(f"\n  {BOLD}HostBook{R}  {DIM}│{R}  {CYAN}{hostname}{R}  {DIM}│  {now}{R}{tag}\n")
    print(div)
    print(fmt(cols, header=True))
    print(div)
    for r in display:
        print(fmt(r))
    print(div)

    in_use   = sum(1 for r in display if r[4] == "in_use")
    reserved = sum(1 for r in display if r[4] == "reserved")
    avail    = sum(1 for r in display if r[4] == "available")
    print(f"\n  Total {BOLD}{len(display)}{R}   "
          f"{GREEN}Available {avail}{R}   "
          f"{CYAN}In use {in_use}{R}   "
          f"{YELLOW}Reserved {reserved}{R}\n")


# ── Commands ──────────────────────────────────────────────────────────────────
def cmd_show(_):
    conn = db()
    render(get_hosts(conn))
    conn.close()


def cmd_live(_):
    import termios, tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        os.set_blocking(fd, False)
        while True:
            conn = db()
            render(get_hosts(conn), live=True)
            conn.close()
            for _ in range(30):   # 3s in 0.1s ticks
                time.sleep(0.1)
                try:
                    ch = sys.stdin.read(1)
                    if ch.lower() == "q":
                        print("\033[H\033[J")
                        return
                except BlockingIOError:
                    pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def cmd_add(args):
    hostname = args.host or input("  Hostname  : ").strip()
    product  = args.product or input("  Product   : ").strip() or "—"
    conn = db()
    try:
        conn.execute("INSERT INTO hosts (hostname, product) VALUES (?,?)", (hostname, product))
        conn.commit()
        print(f"\n  {GREEN}✓{R}  Host {BOLD}{hostname}{R} added.\n")
    except sqlite3.IntegrityError:
        print(f"\n  {YELLOW}!{R}  Host {BOLD}{hostname}{R} already exists.\n")
    conn.close()


def cmd_remove(args):
    hostname = args.host or input("  Hostname  : ").strip()
    conn = db()
    conn.execute("DELETE FROM reservations WHERE hostname=?", (hostname,))
    cur = conn.execute("DELETE FROM hosts WHERE hostname=?", (hostname,))
    conn.commit()
    if cur.rowcount:
        print(f"\n  {GREEN}✓{R}  Host {BOLD}{hostname}{R} removed.\n")
    else:
        print(f"\n  {RED}✗{R}  Host {BOLD}{hostname}{R} not found.\n")
    conn.close()


def cmd_reserve(args):
    hostname = args.host or input("  Hostname  : ").strip()
    conn = db()

    # Check host exists
    host = conn.execute("SELECT * FROM hosts WHERE hostname=?", (hostname,)).fetchone()
    if not host:
        print(f"\n  {RED}✗{R}  Host {BOLD}{hostname}{R} not found. Add it first with: add --host {hostname}\n")
        conn.close()
        return

    # Check if already reserved
    existing = conn.execute("SELECT * FROM reservations WHERE hostname=?", (hostname,)).fetchone()
    if existing:
        since = existing["reserved_at"]
        print(f"\n  {YELLOW}⚠  RESERVED{R}  —  {BOLD}{hostname}{R} is already in use\n")
        print(f"  {DIM}User     :{R}  {CYAN}{existing['username']}{R}")
        print(f"  {DIM}Schedule :{R}  {existing['schedule']}")
        print(f"  {DIM}Since    :{R}  {since}\n")
        print(f"  To release: python3 dashboard.py release --host {hostname}\n")
        conn.close()
        return

    username = args.user     or input("  User      : ").strip()
    schedule = args.schedule or input("  Schedule  : ").strip() or "—"

    conn.execute("INSERT INTO reservations (hostname, username, schedule) VALUES (?,?,?)",
                 (hostname, username, schedule))
    conn.execute("UPDATE hosts SET status='reserved' WHERE hostname=?", (hostname,))
    conn.commit()
    print(f"\n  {GREEN}✓{R}  {BOLD}{hostname}{R} reserved by {CYAN}{username}{R}  [{schedule}]\n")
    conn.close()


def cmd_release(args):
    hostname = args.host or input("  Hostname  : ").strip()
    conn = db()
    cur = conn.execute("DELETE FROM reservations WHERE hostname=?", (hostname,))
    if cur.rowcount:
        conn.execute("UPDATE hosts SET status='available' WHERE hostname=?", (hostname,))
        conn.commit()
        print(f"\n  {GREEN}✓{R}  {BOLD}{hostname}{R} is now available.\n")
    else:
        print(f"\n  {YELLOW}!{R}  No reservation found for {BOLD}{hostname}{R}.\n")
    conn.close()


def cmd_status(args):
    hostname = args.host or input("  Hostname  : ").strip()
    conn = db()
    host = conn.execute("SELECT * FROM hosts WHERE hostname=?", (hostname,)).fetchone()
    if not host:
        print(f"\n  {RED}✗{R}  Host {BOLD}{hostname}{R} not found.\n")
        conn.close()
        return
    res = conn.execute("SELECT * FROM reservations WHERE hostname=?", (hostname,)).fetchone()
    conn.close()

    clr = STATUS_CLR.get(host["status"], R)
    print(f"\n  {BOLD}{hostname}{R}  —  {clr}{host['status']}{R}")
    print(f"  Product  : {host['product']}")
    if res:
        print(f"  {YELLOW}Reserved by  :{R}  {CYAN}{res['username']}{R}")
        print(f"  Schedule     :  {res['schedule']}")
        print(f"  Since        :  {res['reserved_at']}")
    else:
        print(f"  {GREEN}No active reservation.{R}")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(prog="dashboard.py", description="HostBook CLI")
    sub = ap.add_subparsers(dest="cmd")

    sub.add_parser("show",    help="Print table once")
    sub.add_parser("live",    help="Live auto-refresh (q to quit)")

    p = sub.add_parser("add",     help="Add a host")
    p.add_argument("--host");    p.add_argument("--product")

    p = sub.add_parser("remove",  help="Remove a host")
    p.add_argument("--host")

    p = sub.add_parser("reserve", help="Reserve a host")
    p.add_argument("--host");    p.add_argument("--user");    p.add_argument("--schedule")

    p = sub.add_parser("release", help="Release a reservation")
    p.add_argument("--host")

    p = sub.add_parser("status",  help="Show host status")
    p.add_argument("--host")

    args = ap.parse_args()
    dispatch = {
        "show":    cmd_show,
        "live":    cmd_live,
        "add":     cmd_add,
        "remove":  cmd_remove,
        "reserve": cmd_reserve,
        "release": cmd_release,
        "status":  cmd_status,
    }
    fn = dispatch.get(args.cmd)
    if fn:
        fn(args)
    else:
        # default: live
        cmd_live(args)


if __name__ == "__main__":
    main()
