import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.certificate import CertificateStatus


class RecipientIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr


class CertificateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    recipient_name: str
    recipient_email: str | None = None
    status: CertificateStatus
    file_path: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    generated_at: datetime | None = None
