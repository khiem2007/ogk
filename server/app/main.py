from fastapi import FastAPI

from server.app.api.auth import router as auth_router
from server.app.api.devices import router as devices_router
from server.app.db.session import verify_database_pragmas

app = FastAPI(title="OpenGuard Kids Server", version="0.1.0")
app.include_router(auth_router, prefix="/api/v1/auth")
app.include_router(auth_router, prefix="/auth")
app.include_router(devices_router, prefix="/api/v1")


@app.get("/api/v1/health")
def health() -> dict[str, object]:
    return {"status": "ok", "database": verify_database_pragmas()}
