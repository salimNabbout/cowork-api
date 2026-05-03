from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    name: str
    email: EmailStr
    is_active: bool = True


class UserCreate(UserBase):
    """Payload de cadastro. password e opcional para retrocompat - sem ele o user nao consegue logar."""
    password: str | None = None


class UserUpdate(BaseModel):
    """Payload de PATCH parcial."""
    name: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    is_active: bool | None = None


class UserRead(UserBase):
    """Saida publica - NUNCA inclui hashed_password."""
    id: int

    model_config = ConfigDict(from_attributes=True)
