# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
from typing import Annotated

from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# from un0.auth.routers import router  # type: ignore

from un0.config import settings  # type: ignore


app = FastAPI()

templates = Jinja2Templates(directory="templates")

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)


@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
):  # settings: Annotated[settings, Depends(get_settings)]):
    return templates.TemplateResponse(
        "sa.Index.html",
        {
            "request": request,
            "site_name": settings.SITE_NAME,
        },
    )


@app.get("/app", response_class=HTMLResponse)
async def app_base(
    request: Request,  # , settings: Annotated[settings, Depends(get_settings)]
):
    return templates.TemplateResponse(
        "app.html",
        {
            "request": request,
            "authentication_url": "/api/auth/login",
            "site_name": settings.SITE_NAME,
        },
    )


app.include_router(router)
