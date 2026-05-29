from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=1, max_length=255)


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=64)
    new_password: str = Field(min_length=8, max_length=128)


class AuthenticatedUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthenticatedUserResponse