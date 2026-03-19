import msal
from app.config import settings


def build_msal_app(cache=None):
    authority = f"https://login.microsoftonline.com/{settings.MS_TENANT_ID}"

    print("CLIENT_ID:", settings.MS_CLIENT_ID)
    print("TENANT_ID:", settings.MS_TENANT_ID)
    print("SECRET_LEN:", len(settings.MS_CLIENT_SECRET or ""))
    print("SECRET_HEAD:", (settings.MS_CLIENT_SECRET or "")[:6])
    print("SECRET_TAIL:", (settings.MS_CLIENT_SECRET or "")[-6:])
    return msal.ConfidentialClientApplication(
        client_id=settings.MS_CLIENT_ID,
        client_credential=settings.MS_CLIENT_SECRET,
        authority=authority,
        token_cache=cache,
    )

def get_auth_url():
    app = build_msal_app()
    return app.get_authorization_request_url(
        scopes=settings.GRAPH_SCOPES,
        redirect_uri=settings.MS_REDIRECT_URI,
    )

def acquire_token_by_code(code: str):
    app = build_msal_app()
    return app.acquire_token_by_authorization_code(
        code=code,
        scopes=settings.GRAPH_SCOPES,
        redirect_uri=settings.MS_REDIRECT_URI,
    )