import secrets
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.admin import router as admin_router
from app.api.routes.audit import router as audit_router
from app.api.routes.labor import router as labor_router
from app.api.routes.operations import router as operations_router
from app.api.routes.procurement import router as procurement_router
from app.api.routes.projects import router as projects_router
from app.api.routes.system import router as system_router
from app.core.config import settings
from app.db import engine
from app.logging_setup import backend_logger, request_context
from app.models import Base
from app.services.seed import seed_local_data


@asynccontextmanager
async def lifespan(_: FastAPI):
    backend_logger.info({"event": "startup"})
    settings.upload_directory.mkdir(parents=True, exist_ok=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await seed_local_data()
    try:
        yield
    finally:
        backend_logger.info({"event": "shutdown"})
        await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Local-first construction project ERP API",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = secrets.token_hex(12)
    request.state.request_id = request_id
    context_token = request_context.set(request_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as error:
        backend_logger.error({"event": "request_failed", "request_id": request_id,
                              "method": request.method, "path": request.url.path,
                              "status": 500, "error_type": type(error).__name__})
        raise
    finally:
        request_context.reset(context_token)
    response.headers["X-Request-ID"] = request_id
    if request.url.path != "/api/v1/client-logs":
        backend_logger.info({"event": "request_completed", "request_id": request_id,
                             "method": request.method, "path": request.url.path,
                             "status": response.status_code,
                             "duration_ms": round((time.perf_counter() - started) * 1000, 2)})
    return response


app.include_router(system_router)
app.include_router(projects_router)
app.include_router(procurement_router)
app.include_router(operations_router)
app.include_router(labor_router)
app.include_router(admin_router)
app.include_router(audit_router)