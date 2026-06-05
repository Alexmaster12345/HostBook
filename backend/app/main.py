from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import auth, assets, reservations, agent, reports, users

app = FastAPI(
    title="HostBook API",
    description="Linux Server Reservation and Usage Tracking Platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(assets.router)
app.include_router(reservations.router)
app.include_router(agent.router)
app.include_router(reports.router)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/healthz")
def health():
    return {"status": "ok", "service": "HostBook"}
