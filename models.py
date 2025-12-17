from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

class StudentBase(BaseModel):
    student_id: str
    name: str
    branch: str
    year: int
    section: str
    email: EmailStr
    phone: str
    parent_phone: str

class StudentCreate(StudentBase):
    pass

class StudentInDB(StudentBase):
    face_embedding: List[float] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

class StudentUpdate(BaseModel):
    name: Optional[str] = None
    branch: Optional[str] = None
    year: Optional[int] = None
    section: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    parent_phone: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class Admin(BaseModel):
    username: str
    password: str
