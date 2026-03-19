from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def home(request: Request):
    print("HOME SESSION FULL:", dict(request.session))

    user = request.session.get("user")

    print("HOME USER:", user)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user
    })