from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
from app.auth import get_auth_url, acquire_token_by_code
from app.graph import GraphService
from app.token_store import save_user_token, delete_user_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
def login():
    return RedirectResponse(get_auth_url())


@router.get("/callback")
def callback(
    request: Request,
    code: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
):
    if error:
        print("AUTH ERROR:", error)
        print("AUTH ERROR DESCRIPTION:", error_description)
        return JSONResponse(
            {
                "ok": False,
                "error": error,
                "error_description": error_description,
            },
            status_code=400,
        )

    if not code:
        print("AUTH ERROR: missing code")
        return JSONResponse(
            {
                "ok": False,
                "error": "missing_code",
                "error_description": "Microsoft no devolvió el parámetro 'code'.",
            },
            status_code=400,
        )

    token_result = acquire_token_by_code(code)
    print("TOKEN RESULT KEYS:", list(token_result.keys()))

    if "access_token" not in token_result:
        print("TOKEN RESULT FULL:", token_result)
        return JSONResponse(token_result, status_code=400)

    access_token = token_result["access_token"]
    graph = GraphService(access_token)
    me = graph.me()

    print("ME:", me)

    user_email = me.get("mail") or me.get("userPrincipalName")
    user_name = me.get("displayName")

    save_user_token(user_email, access_token)

    request.session["user"] = {
        "name": user_name,
        "email": user_email,
    }

    print("SESSION USER SAVED:", request.session["user"])

    return RedirectResponse("/", status_code=302)


@router.get("/logout")
def logout(request: Request):
    user = request.session.get("user")
    if user and user.get("email"):
        delete_user_token(user["email"])

    request.session.clear()
    return RedirectResponse("/", status_code=302)