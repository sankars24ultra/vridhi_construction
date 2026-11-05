import asyncio
import json
import logging
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.logging_setup import DailyJsonHandler
from app.api.routes.system import client_logs


def test_daily_json_log(tmp_path):
    record = logging.LogRecord("backend", logging.INFO, "", 0, {"event": "test"}, (), None)
    with patch("app.logging_setup.settings") as settings:
        settings.log_directory = tmp_path
        DailyJsonHandler().emit(record)
    path = tmp_path / datetime.now(timezone.utc).strftime("%Y-%m-%d") / "backend.jsonl"
    entry = json.loads(path.read_text())
    assert entry["event"] == "test"
    assert entry["level"] == "INFO"


def test_client_logs_exclude_sensitive_fields():
    from unittest.mock import AsyncMock
    request = MagicMock()
    request.body = AsyncMock(return_value=json.dumps([{"event": "api_response", "status": 201, "password": "secret", "message": "sensitive", "path": "/?token=secret"}]).encode())
    with patch("app.api.routes.system.frontend_logger") as logger:
        response = asyncio.run(client_logs(request))
    assert response.status_code == 204
    assert logger.info.call_args.args[0] == {"event": "api_response", "status": 201}