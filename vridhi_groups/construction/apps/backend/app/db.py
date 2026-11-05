from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.core.config import settings
from app.logging_setup import backend_logger, request_context

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@event.listens_for(Session, "after_commit")
def log_database_commit(session: Session) -> None:
    backend_logger.info({"event": "database_commit", "database": engine.url.database, "request_id": request_context.get()})


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session