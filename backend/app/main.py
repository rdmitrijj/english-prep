from fastapi import APIRouter, FastAPI

from app.routers import attempts, auth, content, health

app = FastAPI(title="English-prep API", docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)

api = APIRouter(prefix="/api")
api.include_router(health.router)
api.include_router(auth.router)
api.include_router(content.router)
api.include_router(attempts.router)
app.include_router(api)
