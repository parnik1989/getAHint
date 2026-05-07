import hashlib
import hmac
import os
import secrets

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import UserAccount, UserSession
from app.schemas.authSchema import AuthRequest

PBKDF2_ITERATIONS = 120_000


def register_user(db: Session, request: AuthRequest) -> dict:
    username = _normalize_username(request.username)
    _validate_password(request.password)

    existing = db.query(UserAccount).filter(UserAccount.username == username).one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    user = UserAccount(username=username, password_hash=_hash_password(request.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return _create_session(db, user)


def login_user(db: Session, request: AuthRequest) -> dict:
    username = _normalize_username(request.username)
    user = db.query(UserAccount).filter(UserAccount.username == username).one_or_none()
    if not user or not _verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    return _create_session(db, user)


def logout_user(db: Session, token: str | None) -> dict:
    token = _clean_token(token)
    if token:
        db.query(UserSession).filter(UserSession.token == token).delete()
        db.commit()
    return {"status": "logged_out"}


def get_user_id_for_token(db: Session, token: str | None) -> str | None:
    token = _clean_token(token)
    if not token:
        return None

    session = db.query(UserSession).filter(UserSession.token == token).one_or_none()
    if not session:
        return None
    return f"user-{session.user_id}"


def current_user(db: Session, token: str | None) -> dict | None:
    token = _clean_token(token)
    if not token:
        return None

    row = (
        db.query(UserAccount, UserSession)
        .join(UserSession, UserSession.user_id == UserAccount.id)
        .filter(UserSession.token == token)
        .one_or_none()
    )
    if not row:
        return None

    user, _ = row
    return {"user_id": f"user-{user.id}", "username": user.username}


def _create_session(db: Session, user: UserAccount) -> dict:
    session = UserSession(user_id=user.id, token=secrets.token_urlsafe(32))
    db.add(session)
    db.commit()
    return {"token": session.token, "user_id": f"user-{user.id}", "username": user.username}


def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_hex, digest_hex = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations_text),
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False


def _normalize_username(username: str) -> str:
    normalized = username.strip().lower()
    if len(normalized) < 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username must be at least 3 characters")
    if len(normalized) > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username is too long")
    return normalized


def _validate_password(password: str) -> None:
    if len(password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 6 characters")


def _clean_token(token: str | None) -> str | None:
    if not token:
        return None
    token = token.strip()
    if token.lower().startswith("bearer "):
        return token.split(" ", 1)[1].strip()
    return token
