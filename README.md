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
