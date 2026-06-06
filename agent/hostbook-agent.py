#!/usr/bin/env python3
"""
HostBook Host Agent
Runs on each managed Linux server. Collects metrics and active sessions,
then POSTs them to the HostBook API every INTERVAL seconds.

Compatible with Python 3.6+ and all major Linux distributions.
No third-party dependencies required.
"""

import json
import logging
import os
import socket
import subprocess
import time
from urllib.request import Request, urlopen
from urllib.error import URLError

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


def get_os_info():
    # Try /etc/os-release first (systemd-era, all modern distros)
    for path in ("/etc/os-release", "/usr/lib/os-release"):
        try:
            with open(path) as f:
                info = {}
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, _, v = line.partition("=")
                        info[k] = v.strip('"').strip("'")
                pretty = info.get("PRETTY_NAME") or info.get("NAME", "")
                if pretty:
                    return pretty
        except OSError:
            pass

    # Fallback: older distros without os-release
    for path in ("/etc/redhat-release", "/etc/debian_version",
                 "/etc/alpine-release", "/etc/arch-release",
                 "/etc/gentoo-release", "/etc/SuSE-release"):
        try:
            with open(path) as f:
                line = f.readline().strip()
                if line:
                    return line
        except OSError:
            pass

    # Last resort: uname
    try:
        return subprocess.check_output(["uname", "-sr"], text=True).strip()
    except Exception:
        return "Linux"


def get_logged_in_users():
    # Try `who` (util-linux, present on virtually all distros)
    for cmd in (["who"], ["w", "-h"]):
        try:
            out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
            users = list({line.split()[0] for line in out.strip().splitlines() if line})
            if users:
                return users
        except Exception:
            pass

    # Fallback: scan /proc/*/status for real user sessions
    try:
        uids = set()
        for pid in os.listdir("/proc"):
            if not pid.isdigit():
                continue
            try:
                with open(f"/proc/{pid}/status") as f:
                    for line in f:
                        if line.startswith("Uid:"):
                            uid = line.split()[1]
                            if int(uid) >= 1000:
                                uids.add(uid)
                            break
            except OSError:
                pass
        import pwd
        return [pwd.getpwuid(int(u)).pw_name for u in uids]
    except Exception:
        return []


def get_cpu_percent():
    try:
        import psutil
        return psutil.cpu_percent(interval=1)
    except ImportError:
        pass

    try:
        with open("/proc/stat") as f:
            fields = list(map(int, f.readline().split()[1:]))
        idle = fields[3]
        total = sum(fields)
        time.sleep(0.1)
        with open("/proc/stat") as f:
            fields2 = list(map(int, f.readline().split()[1:]))
        idle2 = fields2[3]
        total2 = sum(fields2)
        diff_idle = idle2 - idle
        diff_total = total2 - total
        return round((1 - diff_idle / diff_total) * 100, 1) if diff_total else 0.0
    except Exception:
        return 0.0


def get_ram_percent():
    try:
        with open("/proc/meminfo") as f:
            lines = {}
            for l in f:
                if ":" in l:
                    k, _, v = l.partition(":")
                    lines[k.strip()] = int(v.split()[0])
        total = lines.get("MemTotal", 1)
        available = lines.get("MemAvailable", lines.get("MemFree", total))
        return round((1 - available / total) * 100, 1)
    except Exception:
        return 0.0


def get_disk_percent():
    try:
        stat = os.statvfs("/")
        total = stat.f_blocks * stat.f_frsize
        free  = stat.f_bfree  * stat.f_frsize
        return round((1 - free / total) * 100, 1) if total else 0.0
    except Exception:
        return 0.0


def get_load_avg():
    try:
        return round(os.getloadavg()[0], 2)
    except OSError:
        try:
            with open("/proc/loadavg") as f:
                return round(float(f.read().split()[0]), 2)
        except Exception:
            return 0.0


def get_ip_address():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return None


def collect():
    users = get_logged_in_users()
    return {
        "hostname":        HOSTNAME,
        "os":              get_os_info(),
        "ip_address":      get_ip_address(),
        "cpu_percent":     get_cpu_percent(),
        "ram_percent":     get_ram_percent(),
        "disk_percent":    get_disk_percent(),
        "load_avg":        get_load_avg(),
        "active_users":    len(users),
        "logged_in_users": users,
    }


def send(payload):
    body = json.dumps(payload).encode()
    req  = Request(
        f"{API_URL}/api/v1/agent/heartbeat",
        data=body,
        headers=HEADERS,
        method="POST",
    )
    try:
        with urlopen(req, timeout=10) as resp:
            resp.read()
        log.info("Heartbeat sent — users=%d cpu=%.1f%%",
                 payload["active_users"], payload["cpu_percent"])
    except URLError as e:
        log.warning("Failed to reach HostBook API: %s", e)
    except Exception as e:
        log.warning("Unexpected error sending heartbeat: %s", e)


if __name__ == "__main__":
    log.info("HostBook agent starting — host=%s api=%s interval=%ds os=%s",
             HOSTNAME, API_URL, INTERVAL, get_os_info())
    while True:
        send(collect())
        time.sleep(INTERVAL)
