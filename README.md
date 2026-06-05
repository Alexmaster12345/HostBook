# HostBook

A centralized platform for managing, tracking, and reserving Linux servers, lab machines, and test environments across an organization. HostBook provides real-time visibility into server availability, active users, reservations, and historical usage — eliminating spreadsheets and manual coordination.

---

## Features

| Feature | Description |
|---|---|
| Server Inventory | Full asset registry — physical, VM, workstation, lab |
| Reservation System | Hourly, daily, multi-day reservations with conflict detection |
| Real-Time Monitoring | Active SSH sessions, logged-in users, CPU/RAM/disk metrics |
| Availability Dashboard | Live status across all servers with filtering |
| Analytics | Utilization reports, idle host detection, reservation stats |
| Role-Based Access | Admin, Infra Engineer, Team Lead, Standard User |
| Host Agent | Lightweight agent installed on each managed server |
| REST API | Full API with JWT authentication |

---

## Architecture

```
┌─────────────┐     HTTP      ┌──────────────────┐     SQLite/PG    ┌──────────┐
│  React UI   │ ◄──────────► │  FastAPI Backend  │ ◄─────────────► │ Database │
└─────────────┘              └──────────────────┘                   └──────────┘
                                      ▲
                               Heartbeat (60s)
                                      │
                         ┌────────────────────────┐
                         │  hostbook-agent.py      │
                         │  (runs on each server)  │
                         └────────────────────────┘
```

---

## Project Structure

```
HostBook/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app entry point
│   │   ├── models.py          # SQLAlchemy ORM models
│   │   ├── schemas.py         # Pydantic request/response schemas
│   │   ├── database.py        # DB engine and session
│   │   ├── auth.py            # JWT authentication
│   │   └── routers/
│   │       ├── auth.py        # /api/v1/auth — register, login
│   │       ├── users.py       # /api/v1/users — profile, teams
│   │       ├── assets.py      # /api/v1/assets — server inventory
│   │       ├── reservations.py# /api/v1/reservations — booking
│   │       ├── agent.py       # /api/v1/agent — heartbeat, metrics
│   │       └── reports.py     # /api/v1/reports — analytics
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js             # Axios API client
│   │   ├── pages/
│   │   │   ├── Login.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Inventory.jsx
│   │   │   ├── Reservations.jsx
│   │   │   └── Analytics.jsx
│   │   └── components/
│   │       └── Layout.jsx
│   ├── package.json
│   └── Dockerfile
├── agent/
│   ├── hostbook-agent.py      # Host monitoring agent
│   └── hostbook-agent.service # systemd unit file
├── docker-compose.yml
└── Jenkinsfile
```

---

## Quick Start

### Option 1 — Docker Compose (Recommended)

```bash
git clone https://github.com/Alexmaster12345/HostBook.git
cd HostBook
docker compose up -d
```

- **Frontend:** http://localhost:3000
- **API:** http://localhost:8080
- **API Docs:** http://localhost:8080/docs

### Option 2 — Local Development

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## CLI Dashboard (`dashboard.py`)

The CLI dashboard is a standalone terminal tool for managing server reservations without the web UI. It uses a local SQLite file (`hostbook_local.db`) and requires no backend server running.

### Launch

```bash
# Live auto-refresh table (updates every 3s — press q to quit)
python3 dashboard.py live

# One-shot snapshot
python3 dashboard.py show
```

**Live mode** displays a centered table with a real-time countdown in the Schedule column. The countdown color changes as time runs out:

| Color | Meaning |
|---|---|
| Green | More than 1 hour remaining |
| Yellow | Less than 5 minutes remaining |
| Red | Expired |

---

### Managing Hosts

```bash
# Add a host to the inventory
python3 dashboard.py add --host host-prod-01 --product "WebSphere v9.0"

# Remove a host (also removes its reservation)
python3 dashboard.py remove --host host-prod-01
```

---

### Reserving a Host

Reserves a machine for a set duration. If the host is already taken, the command shows who has it and how much time is left — no double-booking is possible.

**Fully interactive (recommended):**
```bash
python3 dashboard.py reserve --host host-prod-01
```
The tool will prompt step by step:
```
  User      : alex
  Duration unit:
  1  Minutes
  2  Hours
  Choose [1/2] : 2
  Hours       : 1.5
```

**With flags (for scripting):**
```bash
# Reserve for 45 minutes
python3 dashboard.py reserve --host host-prod-01 --user alice --minutes 45

# Reserve for 2 hours
python3 dashboard.py reserve --host host-prod-01 --user alice --hours 2

# Reserve for 1.5 hours (decimals supported)
python3 dashboard.py reserve --host host-prod-01 --user alice --hours 1.5
```

**Auto-detect the currently logged-in user with `$(whoami)`:**
```bash
python3 dashboard.py reserve --host host-prod-01 --user $(whoami) --hours 2
```
`$(whoami)` automatically fills in your Linux username so you never have to type it manually.

**If the host is already reserved**, the command shows:
```
  ⚠  RESERVED  —  host-prod-01 is already booked

  User      :  jsmith
  Schedule  :  2h 0m  (until 21:00 UTC)
  Since     :  2026-06-05 19:00:00
  Remaining :  1h 25m left

  To release: python3 dashboard.py release --host host-prod-01
```

---

### Schedule / Duration Reference

| Flag | Example | Result |
|---|---|---|
| `--minutes` | `--minutes 30` | 30-minute reservation |
| `--minutes` | `--minutes 90` | 1h 30m reservation |
| `--hours` | `--hours 1` | 1-hour reservation |
| `--hours` | `--hours 2.5` | 2h 30m reservation |
| *(none)* | *(interactive)* | Prompts for unit and value |

The Schedule column in the table always shows a live countdown (`1h 25m 52s`) for active reservations.

---

### Check & Release

```bash
# See who is using a host and how much time remains
python3 dashboard.py status --host host-prod-01

# Release a reservation when done
python3 dashboard.py release --host host-prod-01
```

---

### Full Command Reference

| Command | Description |
|---|---|
| `python3 dashboard.py` | Start live dashboard (default) |
| `python3 dashboard.py live` | Live auto-refresh, `q` to quit |
| `python3 dashboard.py show` | Print table once and exit |
| `python3 dashboard.py add --host NAME --product PRODUCT` | Add a host |
| `python3 dashboard.py remove --host NAME` | Remove a host |
| `python3 dashboard.py reserve --host NAME --user USER --minutes N` | Reserve for N minutes |
| `python3 dashboard.py reserve --host NAME --user USER --hours N` | Reserve for N hours |
| `python3 dashboard.py status --host NAME` | Show who holds a host |
| `python3 dashboard.py release --host NAME` | Free a reservation |

---

## API Reference

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Create a new user account | Public |
| `POST` | `/api/v1/auth/login` | Get JWT token | Public |
| `GET` | `/api/v1/users/me` | Current user profile | User |
| `GET` | `/api/v1/assets` | List all servers (filterable) | User |
| `POST` | `/api/v1/assets` | Register a new server | Admin |
| `PATCH` | `/api/v1/assets/{id}` | Update server details/status | Admin |
| `GET` | `/api/v1/reservations` | List reservations | User |
| `POST` | `/api/v1/reservations` | Create a reservation | User |
| `DELETE`| `/api/v1/reservations/{id}` | Cancel a reservation | User/Admin |
| `POST` | `/api/v1/reservations/expire` | Expire past reservations | User |
| `POST` | `/api/v1/agent/heartbeat` | Agent metric push | Agent token |
| `GET` | `/api/v1/agent/metrics/{host}` | Host metric history | User |
| `GET` | `/api/v1/reports/summary` | Fleet status summary | User |
| `GET` | `/api/v1/reports/utilization` | Per-server utilization | User |
| `GET` | `/api/v1/reports/idle` | Servers idle for 24h+ | User |
| `GET` | `/healthz` | Health check | Public |

Full interactive docs at `/docs` (Swagger UI).

---

## Host Agent Setup

Install the agent on each managed server:

```bash
# Copy agent to server
scp agent/hostbook-agent.py root@your-server:/opt/hostbook/

# Install dependencies
pip3 install requests

# Configure and enable as systemd service
cp agent/hostbook-agent.service /etc/systemd/system/
# Edit HOSTBOOK_API and AGENT_TOKEN in the service file
systemctl daemon-reload
systemctl enable --now hostbook-agent
```

The agent sends a heartbeat every 60 seconds containing:
- CPU, RAM, and disk utilisation
- Current load average
- List of logged-in users (from `who`)

---

## Environment Variables

**Backend:**

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./db/hostbook.db` | Database connection string |
| `SECRET_KEY` | `changeme` | JWT signing secret |
| `AGENT_TOKEN` | `changeme-agent-secret` | Shared token for agent authentication |
| `TOKEN_EXPIRE_MINUTES` | `480` | JWT token lifetime in minutes |

**Agent:**

| Variable | Default | Description |
|---|---|---|
| `HOSTBOOK_API` | `http://192.168.1.10:8080` | HostBook API URL |
| `AGENT_TOKEN` | `changeme-agent-secret` | Must match backend token |
| `INTERVAL` | `60` | Heartbeat interval in seconds |

---

## Roles

| Role | Permissions |
|---|---|
| `admin` | Full access — manage assets, users, teams |
| `infra_engineer` | Manage assets and reservations |
| `team_lead` | View all, manage team reservations |
| `user` | View assets, create/cancel own reservations |

---

## CI/CD (Jenkins)

The included `Jenkinsfile` pipeline:
1. Installs backend and frontend dependencies
2. Runs lint (flake8) and API health check in parallel
3. Builds Docker images (on `main` branch)
4. Deploys with Docker Compose and verifies the health endpoint
