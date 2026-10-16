from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers import attempts, auth, content, dashboard, health, practice, trainer

app = FastAPI(title="English-prep API", docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)

api = APIRouter(prefix="/api")
api.include_router(health.router)
api.include_router(auth.router)
api.include_router(content.router)
api.include_router(attempts.router)
api.include_router(practice.router)
api.include_router(trainer.router)
api.include_router(dashboard.router)
app.include_router(api)
# Audio and visuals. Public by URL: they contain no answers (keys and transcripts stay behind the API).
app.mount("/media", StaticFiles(directory=Path(get_settings().content_dir) / "media", check_dir=False), name="media")
