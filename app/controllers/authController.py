from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.authSchema import AuthRequest, UserProfileUpdate
from app.services.auth_service import current_user, get_account_id_for_token, login_user, logout_user, register_user
from app.services.user_profile_service import get_profile, update_profile

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


@router.get("/profile", include_in_schema=False)
def profile(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user_id = get_account_id_for_token(db, authorization)
    if user_id is None:
        return {"authenticated": False}
    return {"authenticated": True, "profile": get_profile(db, user_id)}


@router.put("/profile", include_in_schema=False)
def save_profile(
    request: UserProfileUpdate,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user_id = get_account_id_for_token(db, authorization)
    if user_id is None:
        return {"authenticated": False}
    return {"authenticated": True, "profile": update_profile(db, user_id, request)}
