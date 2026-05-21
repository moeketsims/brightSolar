import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt

from app.auth import token_from_request

from app.config import settings
from app.db import Base, engine
from app.routers import activities, auth as auth_router, clients, expenses, exports, invoices, monitoring, outbound, projects, settings as settings_router, technicians, templates, trips, variations, vehicles

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/app/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Bright Solar Power Operations API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.effective_cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


EXEMPT_PREFIXES = (
    "/auth/login",
    "/auth/logout",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/uploads",
)


@app.middleware("http")
async def require_auth(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)
    path = request.url.path
    if any(path.startswith(p) for p in EXEMPT_PREFIXES):
        return await call_next(request)
    tok = token_from_request(request)
    if not tok:
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)
    try:
        jwt.decode(tok, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return JSONResponse({"detail": "Invalid or expired token"}, status_code=401)
    return await call_next(request)

app.include_router(auth_router.router)
app.include_router(settings_router.router)
app.include_router(clients.router)
app.include_router(technicians.router)
app.include_router(vehicles.router)
app.include_router(projects.router)
app.include_router(expenses.router)
app.include_router(activities.router)
app.include_router(templates.router)
app.include_router(invoices.router)
app.include_router(trips.router)
app.include_router(exports.router)
app.include_router(variations.router)
app.include_router(outbound.router)
app.include_router(monitoring.router)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.get("/health")
async def health():
    return {"status": "ok"}
