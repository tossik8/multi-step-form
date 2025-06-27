import os
import re
from pathlib import Path
from typing import Annotated
import uuid
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from jinja2_fragments.fastapi import Jinja2Blocks
from starlette.middleware.sessions import SessionMiddleware
from pydantic import StringConstraints, EmailStr, ValidationError

from session import Session
from sessions import SessionsCache
from data import get_plans, get_add_ons

ROOT_DIR = Path(__file__).resolve().parent


app = FastAPI()
app.mount("/static", StaticFiles(directory=f"{ROOT_DIR}/static"), name="static")
session_middleware_key = os.getenv("SESSION_MIDDLEWARE_KEY")
assert session_middleware_key is not None
app.add_middleware(SessionMiddleware, secret_key=session_middleware_key, max_age=None)

cache = SessionsCache()

templates = Jinja2Blocks(directory=f"{ROOT_DIR}/templates")

TrimmedStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def set_error_template(template_name: str):
    def _set_template(request: Request):
        request.state.template = template_name
    return _set_template


def get_step_context(step) -> dict:
    context: dict = {"form_step_template": f"form-step-{step}.html"}
    if step == 1:
        context["next"] = 1
    elif step == 2:
        context.update({"back": 1, "next": 2, "plans": get_plans()})
    elif step == 3:
        context.update({"back": 2, "next": 3, "add_ons": get_add_ons()})
    elif step == 4:
        context.update({"back": 3, "next": 4})
    return context


@app.exception_handler(RequestValidationError)
async def handle_validation_exception(request: Request, exc: ValidationError):
    match = re.search("\\d", request.state.template)
    if match:
        step = int(match.group(0))
        context = get_step_context(step)
    form_data = await request.form()
    for key in form_data:
        context[key] = form_data.get(key)
    context["errors"] = [error["loc"][1] for error in exc.errors()]
    return templates.TemplateResponse(
        request=request,
        name=request.state.template,
        context=context,
        status_code=422,
        block_name="form_fields"
    )


def get_valid_session(session: dict):
    if "id" not in session:
        return None
    session_data = cache.get_session(session["id"])
    if session_data is None:
        return None
    return session_data


@app.get("/step-1", response_class=HTMLResponse)
async def step1(request: Request):
    context = get_step_context(1)
    session = get_valid_session(request.session)
    if session is not None:
        context["data"] = session
    headers = {}
    block_name = None
    if "Hx-Current-Url" in request.headers:
        block_name = "main_content"
        if request.headers["Hx-Current-Url"].endswith("/step-4"):
            headers.update({"Hx-Retarget": "main", "Hx-Reswap": "innerHTML"})
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context=context,
        block_name=block_name,
        headers=headers
    )


@app.post(
    "/step-1",
    status_code=303,
    response_class=RedirectResponse
)
async def submit_personal_info(
    request: Request,
    name: Annotated[TrimmedStr, Form()],
    email: Annotated[EmailStr, Form()],
    tel: Annotated[TrimmedStr, Form()],
    _ = Depends(set_error_template("form-step-1.html"))
):
    session = get_valid_session(request.session)
    if session:
        session.name = name
        session.email = email
        session.tel = tel
    else:
        session_id = str(uuid.uuid1())
        request.session["id"] = session_id
        session = Session(name, email, tel)
    cache.add_session(session_id, session)
    return "/step-2"


@app.get("/step-2", response_class=HTMLResponse)
async def step2(request: Request, plan: int = 1, yearly: bool = False):
    session = get_valid_session(request.session)
    if not session:
        return RedirectResponse("/step-1", 303)
    context = get_step_context(2)
    context.update({"yearly": session.yearly, "plan_id": session.plan_id})
    template = "index.html"
    block_name = None
    if "Hx-Trigger" in request.headers:
        template = context["form_step_template"]
        block_name = "form_fields"
        if request.headers["Hx-Trigger"] == "toggle":
            context.update({"yearly": yearly, "plan_id": plan})
    elif "Hx-Current-Url" in request.headers:
        block_name = "main_content"
    return templates.TemplateResponse(
        request=request,
        name=template,
        context=context,
        block_name=block_name
    )


@app.post(
    "/step-2",
    status_code=303,
    response_class=RedirectResponse
)
async def submit_billing_plan(
    request: Request,
    plan_id: Annotated[int, Form(alias="plan", validation_alias="plan")],
    yearly: Annotated[bool, Form()] = False
):
    session = get_valid_session(request.session)
    if not session:
        return "/step-1"
    session.plan_id = plan_id
    session.yearly = yearly
    session.find_plan(get_plans())
    cache.add_session(request.session["id"], session)
    return "/step-3"


@app.get("/step-3", response_class=HTMLResponse)
async def step3(request: Request):
    session = get_valid_session(request.session)
    if not session or session._plan == {}:
        return RedirectResponse("/step-1", 303)
    context = get_step_context(3)
    context["data"] = session
    block_name = None
    if "Hx-Current-Url" in request.headers:
        block_name = "main_content"
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context=context,
        block_name=block_name
    )


@app.post("/step-3", status_code=303, response_class=RedirectResponse)
async def submit_add_ons(
    request: Request,
    selected_add_ons: Annotated[list[int], Form(alias="add_ons", validation_alias="add_ons")] = []
):
    session = get_valid_session(request.session)
    if not session or session._plan == {}:
        return "/step-1"
    session.add_on_ids = selected_add_ons
    session.find_add_ons(get_add_ons())
    cache.add_session(request.session["id"], session)
    return "/step-4"


@app.get("/step-4", response_class=HTMLResponse)
async def step4(request: Request):
    session = get_valid_session(request.session)
    if not session or session._plan == {}:
        return RedirectResponse("/step-1", 303)
    context = get_step_context(4)
    context["data"] = session
    total = session.calculate_total()
    if session.yearly:
        context["total"] = {"yearly": total}
    else:
        context["total"] = {"monthly": total}
    block_name = None
    if "Hx-Current-Url" in request.headers:
        block_name = "main_content"
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context=context,
        block_name=block_name
    )


@app.post("/step-4", status_code=303, response_class=RedirectResponse)
async def create_subscription(request: Request):
    session = get_valid_session(request.session)
    if not session or session._plan == {}:
        return "/step-1"
    session.deleted = True
    cache.add_session(request.session["id"], session)
    return "/confirmation"


@app.get("/confirmation", response_class=HTMLResponse)
async def confirmation(request: Request):
    session = get_valid_session(request.session)
    if not session or not session.deleted:
        return RedirectResponse("/step-1", 303)
    cache.delete_session(request.session["id"])
    request.session.clear()
    return templates.TemplateResponse(
        request=request,
        name="confirmation.html",
    )