import re
import threading
from pathlib import Path
from typing import Annotated
from contextlib import asynccontextmanager
import uuid

from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from jinja2_fragments.fastapi import Jinja2Blocks
from starlette.middleware.sessions import SessionMiddleware
from pydantic import StringConstraints, ValidationError

from session import sessions, Session, clear_inactive_sessions, is_session_valid
from data import get_plans, get_add_ons

ROOT_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    t = threading.Thread(target=clear_inactive_sessions)
    t.start()
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=f"{ROOT_DIR}/static"), name="static")
app.add_middleware(SessionMiddleware, secret_key="mysecret", max_age=None)


templates = Jinja2Blocks(directory=f"{ROOT_DIR}/templates")

TrimmedStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def set_error_template(template_name: str):
    def _set_template(request: Request):
        request.state.template = template_name
    return _set_template


def get_step_context(step, session: Session | None = None) -> dict:
    context: dict = {"form_step_template": f"form-step-{step}.html"}
    if session:
        context["data"] = session
    if step == 1:
        context["next"] = 1
    elif step == 2:
        context.update({"back": 1, "next": 2, "plans": get_plans()})
        if session:
            context.update({"yearly": session.yearly, "plan_id": session.plan_id})
    elif step == 3:
        context.update({"back": 2, "next": 3, "add_ons": get_add_ons()})
    elif step == 4:
        context.update({"back": 3, "next": 4})
    return context


@app.exception_handler(RequestValidationError)
async def handle_validation_exception(request: Request, exc: ValidationError):
    step = re.search("\\d", request.state.template)
    if step:
        context = get_step_context(int(step.group(0)), sessions[request.session["id"]])
    fields = [error["loc"][1] for error in exc.errors()]
    form_data = await request.form()
    for key in form_data:
        context[key] = form_data.get(key)
    context["errors"] = fields
    return templates.TemplateResponse(
        request=request,
        name=request.state.template,
        context=context,
        status_code=422,
        block_name="form_fields"
    )


@app.get("/step-1", response_class=HTMLResponse)
async def step1(request: Request):
    if is_session_valid(request.session):
        session = sessions[request.session["id"]]
        session.update_last_activity_time()
        context = get_step_context(1, session)
    else:
        context = get_step_context(1) 
    block_name = None
    if "Hx-Current-Url" in request.headers:
        block_name = "main_content"
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context=context,
        block_name=block_name
    )


@app.post(
    "/step-1",
    status_code=303,
    response_class=RedirectResponse
)
async def submit_personal_info(
    request: Request,
    name: Annotated[TrimmedStr, Form()],
    email: Annotated[TrimmedStr, Form()],
    tel: Annotated[TrimmedStr, Form()],
    _ = Depends(set_error_template("form-step-1.html"))
):
    if is_session_valid(request.session):
        session_id = request.session["id"]
        sessions[session_id].update_last_activity_time()
    else:
        session_id = str(uuid.uuid1())
        request.session["id"] = session_id
        sessions[session_id] = Session(name, email, tel)
    return "/step-2"


@app.get("/step-2", response_class=HTMLResponse)
async def step2(request: Request, plan: int = 1, yearly: bool = False):
    if not is_session_valid(request.session):
        return RedirectResponse("/step-1", status_code=303)
    session = sessions[request.session["id"]]
    session.update_last_activity_time()
    context = get_step_context(2, session)
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
    if not is_session_valid(request.session):
        return "/step-1"
    session = sessions[request.session["id"]]
    session.update_last_activity_time()
    session.plan_id = plan_id
    session.yearly = yearly
    session.find_plan(get_plans())
    return "/step-3"


@app.get("/step-3", response_class=HTMLResponse)
async def step3(request: Request):
    if not is_session_valid(request.session):
        return RedirectResponse("/step-1", status_code=303)
    session = sessions[request.session["id"]]
    session.update_last_activity_time()
    context = get_step_context(3, session)
    template = "index.html"
    block_name = None
    if "Hx-Current-Url" in request.headers:
        block_name = "main_content"
    return templates.TemplateResponse(
        request=request,
        name=template,
        context=context,
        block_name=block_name
    )


@app.post("/step-3", status_code=303, response_class=RedirectResponse)
async def submit_add_ons(
    request: Request,
    selected_add_ons: Annotated[list[int], Form(alias="add_ons", validation_alias="add_ons")] = []
):
    if not is_session_valid(request.session):
        return RedirectResponse("/step-1", status_code=303)
    session = sessions[request.session["id"]]
    session.add_on_ids = selected_add_ons
    session.find_add_ons(get_add_ons())
    return "/step-4"


@app.get("/step-4", response_class=HTMLResponse)
async def step4(request: Request):
    if not is_session_valid(request.session):
        return RedirectResponse("/step-1", status_code=303)
    session = sessions[request.session["id"]]
    context = get_step_context(4, session)
    total = session.calculate_total()
    if session.yearly:
        context["total"] = {"yearly": total}
    else:
        context["total"] = {"monthly": total}
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context=context,
        block_name="main_content"
    )