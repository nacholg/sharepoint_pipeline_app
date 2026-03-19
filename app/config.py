from dotenv import load_dotenv
import os

load_dotenv()


class Settings:
    APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "change-me")
    MS_CLIENT_ID = os.getenv("MS_CLIENT_ID")
    MS_CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET")
    MS_TENANT_ID = os.getenv("MS_TENANT_ID", "common")
    MS_REDIRECT_URI = os.getenv("MS_REDIRECT_URI", "http://localhost:8000/auth/callback")
    GRAPH_SCOPES = os.getenv("GRAPH_SCOPES", "User.Read").split()

    PIPELINE_WORKDIR = os.getenv("PIPELINE_WORKDIR", "").strip()
    PYTHON_EXECUTABLE = os.getenv("PYTHON_EXECUTABLE", "python").strip()
    BRAND_LOGO = os.getenv("BRAND_LOGO", "assets\\brand\\mastercard.png").strip()


settings = Settings()