import os
import sys
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

# Add backend dir to path so imports work when run from project root
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db
from config import BACKEND_PORT, FRONTEND_PORT
from routers import discovery, messaging, sending, tracking, persona


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[{datetime.utcnow().isoformat()}] Starting Cold Outreach Bot backend...")
    await init_db()

    # Start follow-up scheduler
    try:
        from scheduler.followup_scheduler import start_scheduler
        start_scheduler()
        print("[Scheduler] Follow-up scheduler started.")
    except Exception as e:
        print(f"[Scheduler] Could not start scheduler: {e}")

    yield

    print(f"[{datetime.utcnow().isoformat()}] Shutting down.")


app = FastAPI(
    title="Cold Outreach Bot",
    description="Automated job outreach system for Barsat",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{FRONTEND_PORT}",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(discovery.router)
app.include_router(messaging.router)
app.include_router(sending.router)
app.include_router(tracking.router)
app.include_router(persona.router)


@app.get("/")
async def root():
    return {
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": [
            "POST /discover/maps",
            "POST /discover/linkedin",
            "POST /discover/enrich/{target_id}",
            "POST /message/generate/{target_id}",
            "POST /message/generate/batch",
            "PATCH /message/approve/{message_id}",
            "DELETE /message/{message_id}",
            "POST /send/email/{message_id}",
            "POST /send/linkedin/{message_id}",
            "POST /send/batch",
            "GET /targets",
            "GET /targets/stats",
            "GET /targets/{id}",
            "PATCH /targets/{id}",
        ],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=BACKEND_PORT,
        reload=True,
    )
