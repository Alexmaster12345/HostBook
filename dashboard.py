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

import os, sys, sqlite3, argparse, socket, subprocess, platform, time
from datetime import datetime, timedelta, timezone

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
            os       TEXT DEFAULT '—',
            product  TEXT DEFAULT '—',
            status   TEXT DEFAULT 'available'
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname    TEXT NOT NULL,
            username    TEXT NOT NULL,
            schedule    TEXT NOT NULL,
            duration_min INTEGER NOT NULL DEFAULT 60,
            reserved_at TEXT DEFAULT (datetime('now')),
            ends_at     TEXT,
            FOREIGN KEY(hostname) REFERENCES hosts(hostname)
        )""")
    # migrate reservations table
    res_cols = [r[1] for r in conn.execute("PRAGMA table_info(reservations)").fetchall()]
    if "ends_at" not in res_cols:
        conn.execute("ALTER TABLE reservations ADD COLUMN ends_at TEXT")
    if "duration_min" not in res_cols:
        conn.execute("ALTER TABLE reservations ADD COLUMN duration_min INTEGER DEFAULT 60")
    # migrate hosts table — add os column if missing
    host_cols = [r[1] for r in conn.execute("PRAGMA table_info(hosts)").fetchall()]
    if "os" not in host_cols:
        conn.execute("ALTER TABLE hosts ADD COLUMN os TEXT DEFAULT '—'")
    conn.commit()
    return conn


def expire_reservations(conn):
    expired = conn.execute(
        "SELECT hostname FROM reservations WHERE ends_at <= datetime('now')"
    ).fetchall()
    for row in expired:
        conn.execute("DELETE FROM reservations WHERE hostname=?", (row["hostname"],))
        conn.execute("UPDATE hosts SET status='available' WHERE hostname=?", (row["hostname"],))
    if expired:
        conn.commit()


def get_hosts(conn):
    rows = conn.execute("""
        SELECT h.hostname, h.os, h.product, h.status,
               r.username, r.schedule, r.reserved_at, r.ends_at, r.duration_min
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

    return hostname, product, users, uptime, product  # last = os (same source)


# ── Countdown helper ──────────────────────────────────────────────────────────
def countdown(ends_at_str: str) -> tuple[str, str]:
    """Return (plain_text, colored_text) countdown for a reservation."""
    try:
        ends = datetime.strptime(ends_at_str, "%Y-%m-%d %H:%M:%S")
        secs = int((ends - datetime.now(timezone.utc).replace(tzinfo=None)).total_seconds())
        if secs <= 0:
            return "expired", f"{RED}expired{R}"
        h, rem = divmod(secs, 3600)
        m, s   = divmod(rem, 60)
        text   = f"{h}h {m:02d}m {s:02d}s" if h else f"{m}m {s:02d}s"
        clr    = GREEN if secs > 3600 else (YELLOW if secs > 300 else RED)
        return text, f"{clr}{text}{R}"
    except Exception:
        return "—", "—"


# ── Rendering ─────────────────────────────────────────────────────────────────
def render(rows, live=False):
    cols = ["Host", "OS", "Product", "User", "Schedule", "Status"]

    hostname = socket.gethostname()
    lh, lp, lusers, luptime, los = live_host_info()

    # Build display rows — (plain_text_tuple, colored_text_tuple)
    # columns: host, os, product, user, schedule, status
    plain_rows   = []
    colored_rows = []

    for r in rows:
        h   = r["hostname"]
        ros = r.get("os") or "—"
        p   = r["product"] or "—"
        st  = r["status"]

        if r["username"]:
            u = r["username"]
            if r.get("ends_at"):
                plain_sch, color_sch = countdown(r["ends_at"])
            else:
                plain_sch = color_sch = r["schedule"]
        elif h == hostname:
            u = ", ".join(lusers) if lusers else os.environ.get("USER", "—")
            plain_sch = color_sch = luptime
            ros = los
            st  = "in_use" if lusers else "available"
        else:
            u = plain_sch = color_sch = "—"

        plain_rows.append((h, ros, p, u, plain_sch, st))
        colored_rows.append((h, ros, p, u, color_sch, st))

    if not plain_rows:
        u  = ", ".join(lusers) if lusers else os.environ.get("USER", "—")
        st = "in_use" if lusers else "available"
        plain_rows   = [(lh, los, lp, u, luptime, st)]
        colored_rows = [(lh, los, lp, u, luptime, st)]

    # Column widths based on plain text (no ANSI codes)
    widths = [max(len(cols[i]), max(len(r[i]) for r in plain_rows)) for i in range(6)]

    def fmt(plain_vals, color_vals=None, header=False):
        color_vals = color_vals or plain_vals
        parts = []
        for i, (pv, cv) in enumerate(zip(plain_vals, color_vals)):
            w   = widths[i]
            pad = w - len(pv)
            lpad = pad // 2
            rpad = pad - lpad

            if header:
                parts.append(f"{BOLD}{' '*lpad}{pv}{' '*rpad}{R}")
            elif i == 0:                              # Host
                parts.append(f"{BOLD}{BLUE}{' '*lpad}{cv}{' '*rpad}{R}")
            elif i == 1:                              # OS
                parts.append(f"{MAGENTA}{' '*lpad}{cv}{' '*rpad}{R}")
            elif i == 3:                              # User
                parts.append(f"{CYAN}{' '*lpad}{cv}{' '*rpad}{R}")
            elif i == 4:                              # Schedule / countdown
                parts.append(f"{' '*lpad}{cv}{' '*rpad}")
            elif i == 5:                              # Status
                parts.append(f"{STATUS_CLR.get(pv, R)}{' '*lpad}{cv}{' '*rpad}{R}")
            else:
                parts.append(f"{' '*lpad}{cv}{' '*rpad}")
        return "  " + "   ".join(parts)

    div = "  " + "   ".join("─" * w for w in widths)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tag = f"  {DIM}live — q=quit{R}" if live else ""

    if live:
        print("\033[H\033[J", end="")

    print(f"\n  {BOLD}HostBook{R}  {DIM}│{R}  {CYAN}{hostname}{R}  {DIM}│  {now}{R}{tag}\n")
    print(div)
    print(fmt(cols, header=True))
    print(div)
    for p, c in zip(plain_rows, colored_rows):
        print(fmt(p, c))
    print(div)

    in_use   = sum(1 for r in plain_rows if r[5] == "in_use")
    reserved = sum(1 for r in plain_rows if r[5] == "reserved")
    avail    = sum(1 for r in plain_rows if r[5] == "available")
    print(f"\n  Total {BOLD}{len(plain_rows)}{R}   "
          f"{GREEN}Available {avail}{R}   "
          f"{CYAN}In use {in_use}{R}   "
          f"{YELLOW}Reserved {reserved}{R}\n")


# ── Commands ──────────────────────────────────────────────────────────────────
def cmd_show(_):
    conn = db()
    expire_reservations(conn)
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
            expire_reservations(conn)
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


def require_root():
    if os.geteuid() != 0:
        print(f"\n  {RED}✗{R}  Permission denied — root required to modify hosts.\n")
        sys.exit(1)


def cmd_add(args):
    require_root()
    hostname = args.host    or input("  Hostname  : ").strip()
    ros      = args.os      or input("  OS        : ").strip() or "—"
    product  = args.product or input("  Product   : ").strip() or "—"
    conn = db()
    try:
        conn.execute("INSERT INTO hosts (hostname, os, product) VALUES (?,?,?)",
                     (hostname, ros, product))
        conn.commit()
        print(f"\n  {GREEN}✓{R}  Host {BOLD}{hostname}{R} added  [{MAGENTA}{ros}{R}  {product}]\n")
    except sqlite3.IntegrityError:
        print(f"\n  {YELLOW}!{R}  Host {BOLD}{hostname}{R} already exists.\n")
    conn.close()


def cmd_remove(args):
    require_root()
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


def pick_duration(args) -> int:
    """Interactively ask for duration in minutes or hours. Returns total minutes."""
    if args.minutes:
        return int(args.minutes)
    if args.hours:
        return int(float(args.hours) * 60)

    print(f"\n  {BOLD}Duration unit:{R}")
    print(f"  {CYAN}1{R}  Minutes")
    print(f"  {CYAN}2{R}  Hours")
    choice = input("  Choose [1/2] : ").strip()

    if choice == "1":
        val = input("  Minutes     : ").strip()
        return int(val)
    else:
        val = input("  Hours       : ").strip()
        return max(1, int(float(val) * 60))


def fmt_duration(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} min"
    h, m = divmod(minutes, 60)
    return f"{h}h {m}m" if m else f"{h}h"


def format_schedule(duration_min: int, ends_at: datetime) -> str:
    return f"{fmt_duration(duration_min)}  (until {ends_at.strftime('%H:%M')} UTC)"


def time_remaining(ends_at_str: str) -> str:
    try:
        ends = datetime.strptime(ends_at_str, "%Y-%m-%d %H:%M:%S")
        delta = int((ends - datetime.now(timezone.utc).replace(tzinfo=None)).total_seconds())
        if delta <= 0:
            return f"{RED}expired{R}"
        h, r = divmod(delta, 3600)
        m    = r // 60
        clr  = GREEN if delta > 3600 else (YELLOW if delta > 600 else RED)
        return f"{clr}{fmt_duration(h*60+m)} left{R}"
    except Exception:
        return "—"


def cmd_reserve(args):
    hostname = args.host or input("  Hostname  : ").strip()
    conn = db()
    expire_reservations(conn)

    # Check host exists
    host = conn.execute("SELECT * FROM hosts WHERE hostname=?", (hostname,)).fetchone()
    if not host:
        print(f"\n  {RED}✗{R}  Host {BOLD}{hostname}{R} not found. Add it first with: add --host {hostname}\n")
        conn.close()
        return

    # Check if already reserved
    existing = conn.execute("SELECT * FROM reservations WHERE hostname=?", (hostname,)).fetchone()
    if existing:
        ends_at_str = existing["ends_at"] or ""
        remaining   = time_remaining(ends_at_str) if ends_at_str else "—"

        # Progress bar: how much of the reservation has elapsed
        bar = ""
        try:
            ends   = datetime.strptime(ends_at_str, "%Y-%m-%d %H:%M:%S")
            total  = existing["duration_min"] * 60
            left   = max(0, int((ends - datetime.now(timezone.utc).replace(tzinfo=None)).total_seconds()))
            used   = total - left
            filled = int((used / total) * 20) if total else 0
            bar_clr = GREEN if left > 3600 else (YELLOW if left > 300 else RED)
            bar = f"  {DIM}[{R}{bar_clr}{'█' * filled}{R}{DIM}{'░' * (20 - filled)}]{R}"
        except Exception:
            pass

        div = f"  {'─' * 42}"
        print(f"\n{div}")
        print(f"  {YELLOW}{BOLD}⚠  HOST TAKEN{R}  —  {BOLD}{hostname}{R} is already reserved")
        print(div)
        print(f"  {DIM}Reserved by :{R}  {CYAN}{BOLD}{existing['username']}{R}")
        print(f"  {DIM}Since       :{R}  {existing['reserved_at']}")
        print(f"  {DIM}Duration    :{R}  {existing['schedule']}")
        print(f"  {DIM}Time left   :{R}  {remaining}")
        if bar:
            print(bar)
        print(div)
        print(f"  {DIM}To release  :{R}  python3 dashboard.py release --host {hostname}\n")
        conn.close()
        return

    username = args.user or os.environ.get("USER") or os.environ.get("LOGNAME") or "unknown"

    # ── Duration picker ───────────────────────────────────────────────
    duration_min = pick_duration(args)
    ends_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=duration_min)
    schedule = format_schedule(duration_min, ends_at)

    conn.execute(
        "INSERT INTO reservations (hostname, username, schedule, duration_min, ends_at) VALUES (?,?,?,?,?)",
        (hostname, username, schedule, duration_min, ends_at.strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.execute("UPDATE hosts SET status='reserved' WHERE hostname=?", (hostname,))
    conn.commit()
    print(f"\n  {GREEN}✓{R}  {BOLD}{hostname}{R} reserved by {CYAN}{username}{R}")
    print(f"  Duration  : {YELLOW}{fmt_duration(duration_min)}{R}")
    print(f"  Ends at   : {ends_at.strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"  Schedule  : {schedule}\n")
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
        remaining = time_remaining(res["ends_at"]) if res["ends_at"] else "—"
        print(f"  {YELLOW}Reserved by  :{R}  {CYAN}{res['username']}{R}")
        print(f"  Schedule     :  {res['schedule']}")
        print(f"  Since        :  {res['reserved_at']}")
        print(f"  Remaining    :  {remaining}")
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
    p.add_argument("--host")
    p.add_argument("--os",      help="Operating system name")
    p.add_argument("--product", help="Product / workload running on the host")

    p = sub.add_parser("remove",  help="Remove a host")
    p.add_argument("--host")

    p = sub.add_parser("reserve", help="Reserve a host")
    p.add_argument("--host")
    p.add_argument("--user")
    p.add_argument("--minutes", type=int,   help="Duration in minutes")
    p.add_argument("--hours",   type=float, help="Duration in hours")

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
