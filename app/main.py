from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import projects
from app.config import get_settings
from app.database import get_session, init_db
from app.services import project_service
from app.services.rules_engine import RulesEngine

settings = get_settings()
BASE_DIR = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))

app.include_router(projects.router)


rules_engine = RulesEngine()


@app.get("/")
async def index(request: Request, session: AsyncSession = Depends(get_session)):
    items, total = await project_service.list_projects(session, page=1, size=50)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "projects": items,
        "total": total,
    })


@app.get("/create")
async def create_page(request: Request):
    return templates.TemplateResponse("create.html", {
        "request": request,
        "platforms": rules_engine.list_available("platforms"),
        "genres": rules_engine.list_available("genres"),
        "styles": rules_engine.list_available("styles"),
    })
