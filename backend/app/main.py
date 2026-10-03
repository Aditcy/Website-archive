from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .db import init
from .api import domains, crawls, urls, submissions, dashboard


app = FastAPI(
    title="Website Archive Repository",
    version="1.0.0",
)

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"


@app.on_event("startup")
def boot():
    init()


app.include_router(domains)
app.include_router(crawls)
app.include_router(urls)
app.include_router(submissions)
app.include_router(dashboard)


if FRONTEND.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(FRONTEND)),
        name="static",
    )


@app.get("/")
def home():
    index = FRONTEND / "index.html"

    if not index.exists():
        return {
            "name": "Website Archive Repository",
            "status": "backend ready",
        }

    return FileResponse(str(index))
