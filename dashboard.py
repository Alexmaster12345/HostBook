#!/usr/bin/env python3
"""
HostBook CLI Dashboard
Displays server reservations and schedules in a formatted table.
Usage: python3 dashboard.py [--db path/to/hostbook.db]
"""

import os
import sys
import sqlite3
import argparse
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "backend/db/hostbook.db"))

# ANSI colours
RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
DIM    = "\033[2m"
WHITE  = "\033[97m"
BG_DARK = "\033[48;5;236m"


def status_color(status: str) -> str:
    return {
        "available":   GREEN,
        "reserved":    YELLOW,
        "in_use":      CYAN,
        "maintenance": RED,
        "offline":     DIM,
    }.get(status, RESET)


def schedule_label(res: dict) -> str:
    rtype = res["reservation_type"]
    start = datetime.fromisoformat(res["starts_at"]) if res["starts_at"] else None
    end   = datetime.fromisoformat(res["ends_at"])   if res["ends_at"]   else None

    if not start or not end:
        return "—"

    if rtype == "recurring":
        day  = start.strftime("%A")
        return f"Weekly (Every {day})"
    if rtype == "daily":
        return f"Daily ({start.strftime('%H:%M')} - {end.strftime('%H:%M')})"
    if rtype == "multi_day":
        days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        return f"Mon-Fri ({start.strftime('%H:%M')} - {end.strftime('%H:%M')})"
    # hourly
    return f"{start.strftime('%a')} ({start.strftime('%H:%M')} - {end.strftime('%H:%M')})"


def load_from_db(db_path: str) -> list[dict]:
    if not os.path.exists(db_path):
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT
            a.hostname,
            a.os        AS product,
            a.status,
            u.username  AS user,
            r.reservation_type,
            r.starts_at,
            r.ends_at,
            r.purpose
        FROM reservations r
        JOIN assets a ON a.id = r.asset_id
        JOIN users  u ON u.id = r.user_id
        WHERE r.status IN ('active', 'pending')
        ORDER BY r.starts_at
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


SAMPLE = [
    {"hostname": "host-prod-01",  "product": "WebSphere v9.0",    "status": "reserved",  "user": "jsmith",  "reservation_type": "multi_day", "starts_at": "2026-06-05 09:00", "ends_at": "2026-06-05 17:00", "purpose": None},
    {"hostname": "host-prod-02",  "product": "OpenShift Cluster", "status": "in_use",    "user": "dnoah",   "reservation_type": "recurring", "starts_at": "2026-06-02 00:00", "ends_at": "2099-12-31 23:59", "purpose": "Permanent"},
    {"hostname": "host-test-04",  "product": "Oracle DB 19c",     "status": "reserved",  "user": "mrossi",  "reservation_type": "daily",     "starts_at": "2026-06-07 00:00", "ends_at": "2026-06-07 23:59", "purpose": "Overtimes only"},
    {"hostname": "host-dev-09",   "product": "JBoss EAP 7.4",    "status": "reserved",  "user": "alee",    "reservation_type": "daily",     "starts_at": "2026-06-05 18:00", "ends_at": "2026-06-06 02:00", "purpose": None},
    {"hostname": "host-stage-03", "product": "SAP HANA",          "status": "reserved",  "user": "v-patel", "reservation_type": "recurring", "starts_at": "2026-06-09 00:00", "ends_at": "2026-06-09 23:59", "purpose": None},
]


def build_schedule(row: dict) -> str:
    if row.get("purpose") == "Permanent":
        return "24/7 (Permanent)"
    if row.get("purpose") == "Overtimes only":
        return "Sat-Sun (Overtimes only)"
    return schedule_label(row)


def print_table(rows: list[dict], use_sample: bool):
    cols = ["Host", "Product", "User", "Schedule", "Status"]
    data = []
    for r in rows:
        data.append({
            "Host":     r["hostname"],
            "Product":  r.get("product") or "—",
            "User":     r.get("user") or "—",
            "Schedule": build_schedule(r),
            "Status":   r.get("status", "—"),
        })

    widths = {c: len(c) for c in cols}
    for row in data:
        for c in cols:
            widths[c] = max(widths[c], len(row[c]))

    sep = "+" + "+".join("-" * (widths[c] + 2) for c in cols) + "+"
    header = "|" + "|".join(f" {BOLD}{WHITE}{c:<{widths[c]}}{RESET} " for c in cols) + "|"

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = f"  HostBook — Active Reservations   {DIM}{now}{RESET}"
    if use_sample:
        title += f"  {YELLOW}(sample data — no DB found){RESET}"

    print()
    print(f"  {BOLD}{CYAN}{'─' * (sum(widths.values()) + len(cols) * 3 + 1)}{RESET}")
    print(f"  {title}")
    print(f"  {BOLD}{CYAN}{'─' * (sum(widths.values()) + len(cols) * 3 + 1)}{RESET}")
    print()
    print(sep)
    print(header)
    print(sep.replace("-", "="))

    for i, row in enumerate(data):
        bg = BG_DARK if i % 2 == 0 else ""
        line = "|"
        for c in cols:
            val = row[c]
            if c == "Status":
                colored = f"{status_color(val)}{val:<{widths[c]}}{RESET}"
            elif c == "Host":
                colored = f"{BOLD}{val:<{widths[c]}}{RESET}"
            elif c == "User":
                colored = f"{CYAN}{val:<{widths[c]}}{RESET}"
            else:
                colored = f"{val:<{widths[c]}}"
            line += f" {bg}{colored}{RESET} |"
        print(line)

    print(sep)
    print()
    total = len(data)
    active = sum(1 for r in rows if r.get("status") == "in_use")
    reserved = sum(1 for r in rows if r.get("status") == "reserved")
    print(f"  Total: {BOLD}{total}{RESET}   "
          f"In use: {CYAN}{active}{RESET}   "
          f"Reserved: {YELLOW}{reserved}{RESET}")
    print()


def main():
    parser = argparse.ArgumentParser(description="HostBook CLI Dashboard")
    parser.add_argument("--db", default=DB_PATH, help="Path to hostbook.db")
    parser.add_argument("--sample", action="store_true", help="Show sample data")
    args = parser.parse_args()

    rows = [] if args.sample else load_from_db(args.db)
    use_sample = not rows
    if use_sample:
        rows = SAMPLE

    print_table(rows, use_sample)


if __name__ == "__main__":
    main()
