# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from un0.config import settings
from un0.database.models import Model
from un0.database.base import Base
from un0.database.management.db_manager import DBManager
import un0.authorization.models

# try:
#    DBManager().drop_db()
#    DBManager().create_db()
# except Exception as e:
#    print(e)


tags_metadata = [
    {
        "name": "0kui",
        "description": "Zero Knowledge User Interface endpoints.",
        "externalDocs": {
            "description": "un0 0kui docs",
            "url": "http://localhost:8001/okui/",
        },
    },
    {
        "name": "auth",
        "description": "Manage Users, Roles, Groups etc...",
        "externalDocs": {
            "description": "un0 auth docs",
            "url": "http://localhost:8001/auth/models",
        },
    },
]
app = FastAPI(
    openapi_tags=tags_metadata,
    title="Un0 is not an ORM",
    summary="fasterAPI.",
    # description="""
    #    Build fastAPI apps faster and DRYer.
    #    un0 leverages sqlalchemy, postgreSQL, apacheAGE, supa-audit, and pydantic to:
    #        Provide authorization and auditing
    #        Generate routes
    #        Provide a simple mechanism for complex filtering and sorting data
    #    So developers can focus on business logic.
    #    """,
    # version="0.0.1",
    # terms_of_service="http://example.com/terms/",
    # contact={
    #    "name": "Richard Dahl",
    #    "url": "https://notorm.tech",
    #    "email": "info@notorm.tech",
    # },
    # license_info={
    #    "name": "MIT",
    #    "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    # },
)
templates = Jinja2Templates(directory="templates")

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)


@app.get("/app", response_class=HTMLResponse, tags=["0kui"])
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


for model_name, model in Model.registry.items():
    for router in model.routers:
        router.add_to_app(app=app)
