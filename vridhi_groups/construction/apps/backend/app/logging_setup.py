import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone

from app.core.config import settings

request_context: ContextVar[str | None] = ContextVar("request_id", default=None)


class DailyJsonHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            now = datetime.now(timezone.utc)
            directory = settings.log_directory / now.strftime("%Y-%m-%d")
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / f"{record.name}.jsonl"
            entry = {"timestamp": now.isoformat(), "level": record.levelname, **record.msg}
            with path.open("a", encoding="utf-8") as output:
                output.write(json.dumps(entry, ensure_ascii=True) + "\n")
        except Exception:
            self.handleError(record)


def application_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(DailyJsonHandler())
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


backend_logger = application_logger("backend")
frontend_logger = application_logger("frontend")