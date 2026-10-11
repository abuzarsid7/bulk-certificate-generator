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
    recipient_email: str
    status: CertificateStatus
    error_message: str | None = None
    created_at: datetime
    generated_at: datetime | None = None
