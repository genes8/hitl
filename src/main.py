from fastapi import FastAPI

from src.api.v1.router import router as v1_router


def create_app() -> FastAPI:
    app = FastAPI(title="HITL Credit Approval System API")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    app.include_router(v1_router, prefix="/api/v1")
    return app


app = create_app()
