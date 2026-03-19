from __future__ import annotations

from typing import Dict, Optional

TOKEN_STORE: Dict[str, str] = {}


def save_user_token(user_email: str, access_token: str) -> None:
    TOKEN_STORE[user_email] = access_token


def get_user_token(user_email: str) -> Optional[str]:
    return TOKEN_STORE.get(user_email)


def delete_user_token(user_email: str) -> None:
    TOKEN_STORE.pop(user_email, None)