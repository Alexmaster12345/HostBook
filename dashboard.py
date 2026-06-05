#!/usr/bin/env python3
"""
HostBook Terminal Dashboard
Real-time system and fleet overview using curses.
Press 'q' to quit, 'r' to refresh manually.
"""

import curses
import os
import time
import subprocess
import socket
from datetime import datetime


def get_cpu_percent():
    try:
        with open("/proc/stat") as f:
            line = f.readline().split()
        idle1 = int(line[4])
        total1 = sum(int(x) for x in line[1:])
        time.sleep(0.1)
        with open("/proc/stat") as f:
            line = f.readline().split()
        idle2 = int(line[4])
        total2 = sum(int(x) for x in line[1:])
        diff_idle = idle2 - idle1
        diff_total = total2 - total1
        return round((1 - diff_idle / diff_total) * 100, 1) if diff_total else 0.0
    except Exception:
        return 0.0


def get_ram():
    info = {}
    with open("/proc/meminfo") as f:
        for line in f:
            k, v = line.split(":")[0], line.split()[1]
            info[k] = int(v)
    total = info.get("MemTotal", 1)
    available = info.get("MemAvailable", total)
    used = total - available
    percent = round(used / total * 100, 1)
    return round(total / 1024), round(used / 1024), percent


def get_disk():
    stat = os.statvfs("/")
    total = stat.f_blocks * stat.f_frsize
    free = stat.f_bfree * stat.f_frsize
    used = total - free
    pct = round(used / total * 100, 1) if total else 0
    return round(total / 1024**3), round(used / 1024**3), pct


def get_load():
    return os.getloadavg()


def get_logged_in_users():
    try:
        out = subprocess.check_output(["who"], text=True)
        users = [line.split()[0] for line in out.strip().splitlines() if line]
        return list(set(users))
    except Exception:
        return []


def get_uptime():
    with open("/proc/uptime") as f:
        secs = float(f.read().split()[0])
    d, r = divmod(int(secs), 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    parts.append(f"{m}m")
    return " ".join(parts)


def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "unknown"


def get_active_conns():
    try:
        out = subprocess.check_output(["ss", "-tn", "state", "established"], text=True)
        return max(0, len(out.strip().splitlines()) - 1)
    except Exception:
        return 0


def get_top_procs():
    try:
        out = subprocess.check_output(
            ["ps", "aux", "--sort=-%cpu"],
            text=True
        ).splitlines()
        procs = []
        for line in out[1:6]:
            parts = line.split(None, 10)
            if len(parts) >= 11:
                procs.append((parts[0], parts[2], parts[3], parts[10][:30]))
        return procs
    except Exception:
        return []


def bar(value, width=20, fill="█", empty="░"):
    filled = int(value / 100 * width)
    return fill * filled + empty * (width - filled)


def color_pct(pct):
    if pct < 50:   return 1   # green
    if pct < 80:   return 3   # yellow
    return 2                   # red


def draw(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN,   curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_RED,     curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_YELLOW,  curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_CYAN,    curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_WHITE,   curses.COLOR_BLUE)
    curses.init_pair(6, curses.COLOR_BLACK,   curses.COLOR_WHITE)

    REFRESH = 3  # seconds

    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        now = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        hostname = socket.gethostname()
        ip       = get_ip()
        uptime   = get_uptime()
        cpu      = get_cpu_percent()
        ram_tot, ram_used, ram_pct = get_ram()
        disk_tot, disk_used, disk_pct = get_disk()
        load1, load5, load15 = get_load()
        users    = get_logged_in_users()
        conns    = get_active_conns()
        procs    = get_top_procs()

        # ── Header bar ────────────────────────────────────────────────
        header = f" HostBook Dashboard  │  {hostname}  │  {ip}  │  {now} "
        stdscr.attron(curses.color_pair(5) | curses.A_BOLD)
        stdscr.addstr(0, 0, header.ljust(w)[:w])
        stdscr.attroff(curses.color_pair(5) | curses.A_BOLD)

        row = 2

        # ── System Info ───────────────────────────────────────────────
        stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
        stdscr.addstr(row, 2, "SYSTEM INFO")
        stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
        row += 1

        stdscr.addstr(row, 4, f"Uptime   : ")
        stdscr.attron(curses.color_pair(1))
        stdscr.addstr(uptime)
        stdscr.attroff(curses.color_pair(1))

        stdscr.addstr(row, 35, f"Load     : ")
        stdscr.attron(curses.color_pair(color_pct(load1 * 20)))
        stdscr.addstr(f"{load1:.2f}  {load5:.2f}  {load15:.2f}  (1m 5m 15m)")
        stdscr.attroff(curses.color_pair(color_pct(load1 * 20)))
        row += 1

        stdscr.addstr(row, 4, f"TCP Conn : ")
        stdscr.attron(curses.color_pair(4))
        stdscr.addstr(str(conns))
        stdscr.attroff(curses.color_pair(4))

        stdscr.addstr(row, 35, f"Users    : ")
        stdscr.attron(curses.color_pair(1) if users else curses.color_pair(3))
        stdscr.addstr(", ".join(users) if users else "none")
        stdscr.attroff(curses.color_pair(1) if users else curses.color_pair(3))
        row += 2

        # ── Resource Meters ───────────────────────────────────────────
        stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
        stdscr.addstr(row, 2, "RESOURCE USAGE")
        stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
        row += 1

        metrics = [
            ("CPU",  cpu,      f"{cpu}%"),
            ("RAM",  ram_pct,  f"{ram_used}MB / {ram_tot}MB  ({ram_pct}%)"),
            ("DISK", disk_pct, f"{disk_used}GB / {disk_tot}GB  ({disk_pct}%)"),
        ]
        for label, pct, detail in metrics:
            b = bar(pct, width=30)
            stdscr.addstr(row, 4, f"{label:<5} ")
            stdscr.attron(curses.color_pair(color_pct(pct)))
            stdscr.addstr(b)
            stdscr.attroff(curses.color_pair(color_pct(pct)))
            stdscr.addstr(f"  {detail}")
            row += 1

        row += 1

        # ── Top Processes ─────────────────────────────────────────────
        stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
        stdscr.addstr(row, 2, "TOP PROCESSES  (by CPU)")
        stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
        row += 1

        stdscr.attron(curses.color_pair(6))
        stdscr.addstr(row, 4, f"{'USER':<10} {'CPU%':>6} {'MEM%':>6}  COMMAND")
        stdscr.attroff(curses.color_pair(6))
        row += 1

        for user, cpu_p, mem_p, cmd in procs:
            if row >= h - 3:
                break
            stdscr.addstr(row, 4, f"{user:<10} ")
            stdscr.attron(curses.color_pair(color_pct(float(cpu_p))))
            stdscr.addstr(f"{cpu_p:>6} ")
            stdscr.attroff(curses.color_pair(color_pct(float(cpu_p))))
            stdscr.attron(curses.color_pair(color_pct(float(mem_p))))
            stdscr.addstr(f"{mem_p:>6}")
            stdscr.attroff(curses.color_pair(color_pct(float(mem_p))))
            stdscr.addstr(f"  {cmd}")
            row += 1

        # ── Footer ────────────────────────────────────────────────────
        footer = f"  [q] Quit   [r] Refresh   Auto-refresh every {REFRESH}s  "
        stdscr.attron(curses.color_pair(5))
        stdscr.addstr(h - 1, 0, footer.ljust(w)[:w])
        stdscr.attroff(curses.color_pair(5))

        stdscr.refresh()

        # Wait for keypress or timeout
        for _ in range(REFRESH * 10):
            key = stdscr.getch()
            if key == ord("q"):
                return
            if key == ord("r"):
                break
            time.sleep(0.1)


def main():
    curses.wrapper(draw)
    print("HostBook Dashboard closed.")


if __name__ == "__main__":
    main()
