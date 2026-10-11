import uuid
from datetime import datetime, timezone

from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.certificate import Certificate, CertificateStatus
from app.models.job import Job, JobStatus
from app.services.certificate_service import CertificateService
from app.workers.celery_app import celery_app


def process_job(
    db: Session,
    job_id: uuid.UUID | str,
    cert_service: CertificateService | None = None,
) -> Job | None:
    """
    Processes a bulk certificate generation job.

    Failure Isolation Guarantee:
    Each recipient is processed in an independent try-except block.
    A failure (e.g. invalid recipient characters, rendering error) during one certificate
    will commit that certificate as FAILED with its error message and increment the
    failure counter, while allowing subsequent recipients in the job to proceed unharmed.
    """
    if isinstance(job_id, str):
        job_id = uuid.UUID(job_id)

    job = db.get(Job, job_id)
    if not job:
        return None

    cert_service = cert_service or CertificateService()

    # Mark job as processing
    if job.status == JobStatus.PENDING:
        job.status = JobStatus.PROCESSING
        db.commit()

    # Query all pending certificates for this job
    pending_certs = (
        db.query(Certificate)
        .filter(
            Certificate.job_id == job.id,
            Certificate.status == CertificateStatus.PENDING,
        )
        .order_by(Certificate.created_at)
        .all()
    )

    for cert in pending_certs:
        cert.status = CertificateStatus.PROCESSING
        db.commit()

        try:
            file_path = cert_service.generate_and_save(
                job_id=str(job.id),
                cert_id=str(cert.id),
                recipient_name=cert.recipient_name,
                event_name=job.event_name,
                issue_date=job.issue_date,
            )
            cert.file_path = file_path
            cert.status = CertificateStatus.SUCCESS
            cert.generated_at = func.now()
            cert.error_message = None

            # Atomically increment success_count
            db.execute(
                update(Job)
                .where(Job.id == job.id)
                .values(success_count=Job.success_count + 1)
            )
            db.commit()

        except Exception as exc:
            db.rollback()
            cert.status = CertificateStatus.FAILED
            cert.error_message = str(exc)

            # Atomically increment failure_count
            db.execute(
                update(Job)
                .where(Job.id == job.id)
                .values(failure_count=Job.failure_count + 1)
            )
            db.commit()

    # Refresh job state and evaluate completion
    db.refresh(job)
    active_count = (
        db.query(Certificate)
        .filter(
            Certificate.job_id == job.id,
            Certificate.status.in_([CertificateStatus.PENDING, CertificateStatus.PROCESSING]),
        )
        .count()
    )

    if active_count == 0:
        job.completed_at = datetime.now(timezone.utc)
        if job.failure_count > 0:
            job.status = JobStatus.COMPLETED_WITH_ERRORS
        else:
            job.status = JobStatus.COMPLETED
        db.commit()
        db.refresh(job)

    return job


@celery_app.task(name="process_certificate_job", bind=True)
def process_certificate_job(self, job_id: str) -> str:
    """
    Celery background worker entry point.
    """
    db = SessionLocal()
    try:
        job = process_job(db=db, job_id=job_id)
        return str(job.status.value) if job else "not_found"
    finally:
        db.close()
