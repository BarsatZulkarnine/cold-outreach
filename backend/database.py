import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import event
from dotenv import load_dotenv
from models.schemas import Base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./outreach.db")

# Convert sqlite:/// to sqlite+aiosqlite:/// for async support
if DATABASE_URL.startswith("sqlite:///") and "aiosqlite" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Migration: add scheduled_send_at column if it doesn't exist yet
        if "sqlite" in DATABASE_URL:
            from sqlalchemy import text
            try:
                await conn.execute(text("ALTER TABLE messages ADD COLUMN scheduled_send_at DATETIME"))
                print("[DB] Migrated: added scheduled_send_at column.")
            except Exception:
                pass  # Column already exists
    print("[DB] Tables created / verified.")


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
