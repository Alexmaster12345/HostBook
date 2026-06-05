#!/usr/bin/env python3
"""
HostBook Host Agent
Runs on each managed Linux server. Collects metrics and active sessions,
then POSTs them to the HostBook API every INTERVAL seconds.
"""

import os
import time
import socket
import subprocess
import logging
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("hostbook-agent")

API_URL     = os.environ.get("HOSTBOOK_API", "http://192.168.1.10:8080")
AGENT_TOKEN = os.environ.get("AGENT_TOKEN", "changeme-agent-secret")
INTERVAL    = int(os.environ.get("INTERVAL", 60))
HOSTNAME    = socket.gethostname()

HEADERS = {
    "Content-Type": "application/json",
    "X-Agent-Token": AGENT_TOKEN,
}


def get_logged_in_users() -> list[str]:
    try:
        out = subprocess.check_output(["who"], text=True)
        return list({line.split()[0] for line in out.strip().splitlines() if line})
    except Exception:
        return []


def get_cpu_percent() -> float:
    try:
        import psutil
        return psutil.cpu_percent(interval=1)
    except ImportError:
        # Fallback: parse /proc/stat
        with open("/proc/stat") as f:
            fields = list(map(int, f.readline().split()[1:]))
        idle = fields[3]
        total = sum(fields)
        return round((1 - idle / total) * 100, 1)


def get_ram_percent() -> float:
    with open("/proc/meminfo") as f:
        lines = {l.split(":")[0]: int(l.split()[1]) for l in f if ":" in l}
    total = lines.get("MemTotal", 1)
    available = lines.get("MemAvailable", total)
    return round((1 - available / total) * 100, 1)


def get_disk_percent() -> float:
    stat = os.statvfs("/")
    total = stat.f_blocks * stat.f_frsize
    free = stat.f_bfree * stat.f_frsize
    return round((1 - free / total) * 100, 1) if total else 0.0


def get_load_avg() -> float:
    return round(os.getloadavg()[0], 2)


def collect() -> dict:
    users = get_logged_in_users()
    return {
        "hostname":        HOSTNAME,
        "cpu_percent":     get_cpu_percent(),
        "ram_percent":     get_ram_percent(),
        "disk_percent":    get_disk_percent(),
        "active_users":    len(users),
        "load_avg":        get_load_avg(),
        "logged_in_users": users,
    }


def send(payload: dict):
    try:
        r = requests.post(f"{API_URL}/api/v1/agent/heartbeat", json=payload, headers=HEADERS, timeout=10)
        r.raise_for_status()
        log.info("Heartbeat sent — users=%d cpu=%.1f%%", payload["active_users"], payload["cpu_percent"])
    except requests.RequestException as e:
        log.warning("Failed to reach HostBook API: %s", e)


if __name__ == "__main__":
    log.info("HostBook agent starting — host=%s api=%s interval=%ds", HOSTNAME, API_URL, INTERVAL)
    while True:
        send(collect())
        time.sleep(INTERVAL)
