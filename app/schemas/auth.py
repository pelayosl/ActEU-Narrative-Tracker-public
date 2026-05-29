from pydantic import BaseModel


class User(BaseModel):
    user_id: str
    name: str
    surname: str
    username: str
    hashed_password: str
    role: str


class UserPublic(BaseModel):
    user_id: str
    name: str
    surname: str
    username: str
    role: str


class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginForm(BaseModel):
    username: str
    password: str

class RegistrationForm(BaseModel):
    name: str
    surname: str
    username: str
    password: str
    role: str
