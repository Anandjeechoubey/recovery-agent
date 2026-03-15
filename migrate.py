"""Standalone database migration script.

Adds new columns to existing tables without Alembic.
Each migration is idempotent — safe to re-run.

Usage:
    python migrate.py
"""

from __future__ import annotations

import asyncio
import logging

from dotenv import load_dotenv

load_dotenv()

from src.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


MIGRATIONS: list[tuple[str, str]] = [
    # (description, SQL)
    (
        "Add current_stage column to borrowers",
        "ALTER TABLE borrowers ADD COLUMN IF NOT EXISTS current_stage VARCHAR(50)",
    ),
    (
        "Add outcome column to borrowers",
        "ALTER TABLE borrowers ADD COLUMN IF NOT EXISTS outcome VARCHAR(50)",
    ),
]


async def run_migrations() -> None:
    import asyncpg  # type: ignore

    # Convert SQLAlchemy URL to plain asyncpg DSN
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

    logger.info(f"Connecting to {dsn.split('@')[-1]}...")
    conn = await asyncpg.connect(dsn)

    try:
        for description, sql in MIGRATIONS:
            logger.info(f"  → {description}")
            await conn.execute(sql)
            logger.info(f"     OK")
    finally:
        await conn.close()

    logger.info("All migrations complete.")


if __name__ == "__main__":
    asyncio.run(run_migrations())
