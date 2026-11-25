from fastapi import FastAPI

from server.app.db.session import verify_database_pragmas

app = FastAPI(title="OpenGuard Kids Server", version="0.1.0")


@app.get("/api/v1/health")
def health() -> dict[str, object]:
    return {"status": "ok", "database": verify_database_pragmas()}
