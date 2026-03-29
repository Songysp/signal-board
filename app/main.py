from app.config import settings


def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}
