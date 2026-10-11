import uuid
from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Certificate, CertificateStatus, Job, JobStatus


def test_job_and_certificate_roundtrip(db_session):
    job = Job(
        event_name="Bootcamp",
        issue_date=date(2026, 10, 15),
        total_count=2,
        success_count=1,
        failure_count=1,
    )
    cert1 = Certificate(
        recipient_name="Alex",
        recipient_email="alex@example.com",
        status=CertificateStatus.SUCCESS,
        file_path="certificates/test.pdf",
    )
    cert2 = Certificate(
        recipient_name="Jordan",
        recipient_email=None,
        status=CertificateStatus.FAILED,
        error_message="Font rendering failed",
    )
    job.certificates.extend([cert1, cert2])
    db_session.add(job)
    db_session.commit()

    loaded = db_session.get(Job, job.id)
    assert isinstance(loaded.id, uuid.UUID)
    assert loaded.status == JobStatus.PENDING
    assert loaded.total_count == 2
    assert loaded.success_count == 1
    assert loaded.failure_count == 1
    assert loaded.created_at is not None
    assert loaded.updated_at is not None
    assert len(loaded.certificates) == 2

    loaded_cert1 = loaded.certificates[0]
    assert isinstance(loaded_cert1.id, uuid.UUID)
    assert loaded_cert1.job_id == job.id
    assert loaded_cert1.recipient_name == "Alex"
    assert loaded_cert1.recipient_email == "alex@example.com"
    assert loaded_cert1.status == CertificateStatus.SUCCESS
    assert loaded_cert1.file_path == "certificates/test.pdf"

    loaded_cert2 = loaded.certificates[1]
    assert loaded_cert2.recipient_email is None
    assert loaded_cert2.status == CertificateStatus.FAILED
    assert loaded_cert2.error_message == "Font rendering failed"


def test_job_defaults(db_session):
    job = Job(event_name="Seminar", issue_date=date(2026, 5, 1))
    db_session.add(job)
    db_session.commit()

    loaded = db_session.get(Job, job.id)
    assert loaded.status == JobStatus.PENDING
    assert loaded.total_count == 0
    assert loaded.success_count == 0
    assert loaded.failure_count == 0
    assert loaded.completed_at is None


def test_deleting_job_removes_certificates(db_session):
    job = Job(event_name="E", issue_date=date(2026, 1, 1), total_count=1)
    job.certificates.append(Certificate(recipient_name="A", recipient_email="a@example.com"))
    db_session.add(job)
    db_session.commit()

    db_session.delete(job)
    db_session.commit()
    assert db_session.query(Certificate).count() == 0


def test_job_check_constraints(db_session):
    # Total count cannot be negative
    invalid_job = Job(event_name="Invalid", issue_date=date(2026, 1, 1), total_count=-1)
    db_session.add(invalid_job)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Success count cannot be negative
    invalid_job2 = Job(event_name="Invalid2", issue_date=date(2026, 1, 1), success_count=-1)
    db_session.add(invalid_job2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Failure count cannot be negative
    invalid_job3 = Job(event_name="Invalid3", issue_date=date(2026, 1, 1), failure_count=-1)
    db_session.add(invalid_job3)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_certificate_foreign_key_constraint(db_session):
    fake_job_id = uuid.uuid4()
    orphan_cert = Certificate(
        job_id=fake_job_id,
        recipient_name="Ghost",
        recipient_email="ghost@example.com",
    )
    db_session.add(orphan_cert)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_model_indexes_configured():
    from app.models.certificate import Certificate
    from app.models.job import Job

    job_indexes = {idx.name for idx in Job.__table__.indexes}
    assert "ix_jobs_status" in job_indexes
    assert "ix_jobs_created_at" in job_indexes

    cert_indexes = {idx.name for idx in Certificate.__table__.indexes}
    assert "ix_certificates_job_id" in cert_indexes
    assert "ix_certificates_job_status" in cert_indexes
