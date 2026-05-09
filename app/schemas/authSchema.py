from pydantic import BaseModel


class AuthRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user_id: str
    username: str


class UserProfileUpdate(BaseModel):
    display_name: str | None = None
    city: str | None = None
    preferred_categories: list[str] = []
