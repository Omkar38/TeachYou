from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.deps import engine
from db.models import Base
from apps.api.routes.health import router as health_router
from apps.api.routes.documents import router as documents_router
from apps.api.routes.jobs import router as jobs_router
from apps.api.routes.assets import router as assets_router  # NEW

app = FastAPI(title="GenAI Paper-to-Explainer")

# Dev-friendly CORS (frontend typically runs on http://127.0.0.1:5173).
# If you deploy, tighten this.
import os as _os

_extra_origins = [o.strip() for o in _os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        *_extra_origins,
    ],
    # Matches https://<anything>.vercel.app (preview + production deployments)
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


app.include_router(health_router)
app.include_router(documents_router)
app.include_router(jobs_router)
app.include_router(assets_router)  # NEW
