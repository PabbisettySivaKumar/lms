from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class UserDocument(BaseModel):
    """Model for user_documents table"""
    id: Optional[int] = None
    user_id: int = Field(..., description="References users.id")
    name: str
    url: str = Field(..., description="Document URL/path")
    uploaded_at: Optional[datetime] = None

class UserDocumentCreate(BaseModel):
    """Model for creating user documents"""
    name: str
    url: str

class LeaveAttachment(BaseModel):
    """Model for leave_attachments table"""
    id: Optional[int] = None
    leave_id: int = Field(..., description="References leave_requests.id")
    name: str
    url: str
    file_type: Optional[str] = None
    file_size: Optional[int] = Field(None, description="File size in bytes")
    uploaded_by: int = Field(..., description="References users.id")
    uploaded_at: Optional[datetime] = None

class LeaveAttachmentCreate(BaseModel):
    """Model for creating leave attachments"""
    name: str
    url: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None