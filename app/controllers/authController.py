from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.authSchema import AuthRequest
from app.services.auth_service import current_user, login_user, logout_user, register_user

router = APIRouter()


@router.post("/register", include_in_schema=False)
def register(request: AuthRequest, db: Session = Depends(get_db)):
    return register_user(db, request)


@router.post("/login", include_in_schema=False)
def login(request: AuthRequest, db: Session = Depends(get_db)):
    return login_user(db, request)


@router.get("/me", include_in_schema=False)
def me(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    return current_user(db, authorization) or {"user_id": None, "username": None}


@router.post("/logout", include_in_schema=False)
def logout(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    return logout_user(db, authorization)
