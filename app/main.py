from fastapi import FastAPI

from app.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
