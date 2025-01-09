from pydantic import BaseModel
from datetime import date,datetime

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    dob: date
    disabled: bool = False


class UserInDb(User):
    hashed_password: str


class UserInfo(BaseModel):
    username: str | None = None
    dob: date
    password: str


class Post(BaseModel):
    title: str
    user_id: int | None = None
    created_on: datetime


class Comment(BaseModel):
    user_id: int
    post_id: int | None = None
    comment: str
    commented_on: datetime