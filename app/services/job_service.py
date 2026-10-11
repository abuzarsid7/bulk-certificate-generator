from sqlalchemy.orm import Session

from app.models.certificate import Certificate, CertificateStatus
from app.models.job import Job, JobStatus
from app.schemas.job import JobCreate


def create_job(db: Session, payload: JobCreate) -> Job:
    """
    Atomically creates a Job record and Certificate records for all recipients.

    Transaction boundaries:
    1. A single transaction encapsulates the insertion of the Job and all associated
       Certificate records.
    2. db.flush() allocates the Job UUID and verifies job-level constraints without committing.
    3. All Certificate objects are added via db.add_all() in the same transaction.
    4. db.commit() commits the entire transaction atomically to PostgreSQL.
    5. In case of any exception or constraint failure, db.rollback() rolls back the
       entire session, ensuring no partial or orphaned records persist.
    """
    try:
        job = Job(
            event_name=payload.event_name,
            issue_date=payload.issue_date,
            status=JobStatus.PENDING,
            total_count=len(payload.recipients),
            success_count=0,
            failure_count=0,
        )
        db.add(job)
        db.flush()

        certificates = [
            Certificate(
                job_id=job.id,
                recipient_name=recipient.name,
                recipient_email=str(recipient.email) if recipient.email else None,
                status=CertificateStatus.PENDING,
            )
            for recipient in payload.recipients
        ]
        db.add_all(certificates)
        db.commit()
        db.refresh(job)
        return job
    except Exception:
        db.rollback()
        raise
