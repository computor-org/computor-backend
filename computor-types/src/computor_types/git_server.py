from pydantic import BaseModel, EmailStr


class CreateGitUserRequest(BaseModel):
    username: str
    email: EmailStr
    display_name: str
    password: str | None = None


class UpdateGitUserRequest(BaseModel):
    email: EmailStr | None = None
    display_name: str | None = None


class GitUser(BaseModel):
    id: int
    username: str
    email: str
    display_name: str
    is_active: bool


class GitServerHealthResponse(BaseModel):
    status: str
    server_type: str
    version: str | None = None
