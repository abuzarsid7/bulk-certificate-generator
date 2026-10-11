"""create jobs and certificates

Revision ID: 0001
Revises:
Create Date: 2026-10-11
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

JOB_STATUSES = ("pending", "processing", "completed", "completed_with_errors", "failed")
CERT_STATUSES = ("pending", "processing", "success", "failed")


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event_name", sa.String(255), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(*JOB_STATUSES, name="jobstatus", native_enum=False, length=32),
            nullable=False,
        ),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("total_count >= 0", name="ck_jobs_total_nonneg"),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"])

    op.create_table(
        "certificates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recipient_name", sa.String(255), nullable=False),
        sa.Column("recipient_email", sa.String(255), nullable=False),
        sa.Column(
            "status",
            sa.Enum(*CERT_STATUSES, name="certificatestatus", native_enum=False, length=32),
            nullable=False,
        ),
        sa.Column("file_path", sa.String(512)),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_certificates_job_status", "certificates", ["job_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_certificates_job_status", table_name="certificates")
    op.drop_table("certificates")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_table("jobs")
