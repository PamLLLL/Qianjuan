from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import chapters, export, generate, novel_intro, projects, quality, settings as settings_api
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import get_session, init_db
from app.models.project import Project
from app.core.ai import registry
from app.models.global_config import GlobalConfig
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
app.include_router(generate.router)
app.include_router(chapters.router)
app.include_router(quality.router)
app.include_router(export.router)
app.include_router(novel_intro.router)
app.include_router(settings_api.router)


rules_engine = RulesEngine()


@app.get("/")
async def index(request: Request, session: AsyncSession = Depends(get_session)):
    items, total = await project_service.list_projects(session, page=1, size=50)
    return templates.TemplateResponse(request, "index.html", {
        "projects": items,
        "total": total,
    })


@app.get("/create")
async def create_page(request: Request):
    return templates.TemplateResponse(request, "create.html", {
        "platforms": rules_engine.list_available("platforms"),
        "genres": rules_engine.list_available("genres"),
        "styles": rules_engine.list_available("styles"),
    })


@app.get("/project/{project_id}/intro")
async def novel_intro_page(
    project_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    import uuid as _uuid
    from app.models.novel_intro import NovelIntro as NI
    pid = _uuid.UUID(project_id)
    project = await session.get(Project, pid)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    stmt = select(NI).where(NI.project_id == pid)
    result = await session.execute(stmt)
    intro = result.scalar_one_or_none()
    return templates.TemplateResponse(request, "novel_intro.html", {
        "project": project,
        "intro": intro,
    })


@app.get("/settings")
async def settings_page(request: Request, session: AsyncSession = Depends(get_session)):
    config = await session.get(GlobalConfig, 1)
    if not config:
        config = GlobalConfig(id=1)
        session.add(config)
        await session.flush()

    providers_raw = registry.list_providers()
    key_name_map = {
        "deepseek": "deepseek_api_key",
        "claude": "claude_api_key",
        "openai": "openai_api_key",
        "qwen": "dashscope_api_key",
    }
    providers = []
    for p in providers_raw:
        providers.append({
            **p,
            "key_name": key_name_map.get(p["name"], ""),
        })

    return templates.TemplateResponse(request, "settings.html", {
        "config": config,
        "providers": providers,
    })


@app.get("/project/{project_id}")
async def project_workbench(
    project_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    import uuid as _uuid
    pid = _uuid.UUID(project_id)
    stmt = (
        select(Project)
        .where(Project.id == pid)
        .options(
            selectinload(Project.setting),
            selectinload(Project.characters),
            selectinload(Project.worldview),
            selectinload(Project.outline),
            selectinload(Project.volumes),
        )
    )
    result = await session.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    steps = [
        {"key": "settings", "label": "基础设定", "done": project.setting is not None},
        {"key": "characters", "label": "人物体系", "done": len(project.characters) > 0},
        {"key": "worldview", "label": "世界观", "done": project.worldview is not None},
        {"key": "outline", "label": "故事大纲", "done": project.outline is not None},
        {"key": "volumes", "label": "分卷结构", "done": len(project.volumes) > 0},
        {"key": "chapters", "label": "章节大纲", "done": False},
        {"key": "content", "label": "正文撰写", "done": False},
        {"key": "quality", "label": "质量检测", "done": False},
        {"key": "intro", "label": "小说介绍", "done": False},
        {"key": "export", "label": "导出下载", "done": False},
    ]

    return templates.TemplateResponse(request, "project.html", {
        "project": project,
        "steps": steps,
    })
