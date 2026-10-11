import enum
import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, Enum, Index, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint("total_count >= 0", name="ck_jobs_total_nonneg"),
        CheckConstraint("success_count >= 0", name="ck_jobs_success_nonneg"),
        CheckConstraint("failure_count >= 0", name="ck_jobs_failure_nonneg"),
        Index("ix_jobs_status", "status"),
        Index("ix_jobs_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_name: Mapped[str] = mapped_column(String(255))
    issue_date: Mapped[date] = mapped_column(Date)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, native_enum=False, length=32, values_callable=lambda e: [m.value for m in e]),
        default=JobStatus.PENDING,
    )
    total_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    certificates: Mapped[list["Certificate"]] = relationship(  # noqa: F821
        back_populates="job", cascade="all, delete-orphan", passive_deletes=True
    )

    @property
    def job_id(self) -> uuid.UUID:
        return self.id
