from pydantic import BaseModel


class User(BaseModel):
    """A user account as stored, including the bcrypt-hashed password."""

    user_id: str
    name: str
    surname: str
    username: str
    hashed_password: str
    role: str


class UserPublic(BaseModel):
    """Public view of a user for API responses, never exposing the password hash."""

    user_id: str
    name: str
    surname: str
    username: str
    role: str


class AuthToken(BaseModel):
    """Bearer access token returned on successful login."""

    access_token: str
    token_type: str = "bearer"

class LoginForm(BaseModel):
    """Login credentials, sent as a JSON body rather than query parameters."""

    username: str
    password: str

class RegistrationForm(BaseModel):
    """Details an admin supplies to register a new user account."""

    name: str
    surname: str
    username: str
    password: str
    role: str
