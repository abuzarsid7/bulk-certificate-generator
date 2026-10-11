import tempfile
from datetime import date
from unittest.mock import MagicMock

from app.models.certificate import Certificate, CertificateStatus
from app.models.job import Job, JobStatus
from app.services.certificate_service import CertificateService
from app.services.storage_service import StorageService
from app.workers.tasks import process_job


def test_individual_recipient_failure_isolation(db_session):
    """
    Verifies that when an individual recipient fails during generation,
    subsequent recipients continue to process, the failed recipient is recorded
    with a useful error message, and the job transitions to COMPLETED_WITH_ERRORS.
    """
    job = Job(
        event_name="Machine Learning Bootcamp",
        issue_date=date(2026, 10, 15),
        status=JobStatus.PENDING,
        total_count=3,
        success_count=0,
        failure_count=0,
    )
    cert1 = Certificate(recipient_name="Alice Smith", recipient_email="alice@example.com")
    cert2 = Certificate(recipient_name="Bob Error", recipient_email="bob@example.com")
    cert3 = Certificate(recipient_name="Charlie Brown", recipient_email="charlie@example.com")
    job.certificates.extend([cert1, cert2, cert3])
    db_session.add(job)
    db_session.commit()

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = StorageService(base_dir=tmpdir)
        cert_service = CertificateService(storage_service=storage)

        # Mock generate_and_save to fail specifically for "Bob Error"
        original_gen = cert_service.generate_and_save

        def faulty_generate(job_id, cert_id, recipient_name, event_name, issue_date):
            if recipient_name == "Bob Error":
                raise ValueError("Corrupt character encoding for recipient Bob Error")
            return original_gen(job_id, cert_id, recipient_name, event_name, issue_date)

        cert_service.generate_and_save = faulty_generate

        # Execute processing
        processed_job = process_job(db=db_session, job_id=job.id, cert_service=cert_service)

        assert processed_job is not None
        assert processed_job.status == JobStatus.COMPLETED_WITH_ERRORS
        assert processed_job.total_count == 3
        assert processed_job.success_count == 2
        assert processed_job.failure_count == 1
        assert processed_job.completed_at is not None

        # Verify Alice (Recipient 1) succeeded
        db_cert1 = db_session.get(Certificate, cert1.id)
        assert db_cert1.status == CertificateStatus.SUCCESS
        assert db_cert1.file_path is not None
        assert db_cert1.error_message is None
        assert storage.get_absolute_path(db_cert1.file_path).exists()

        # Verify Bob (Recipient 2) failed with descriptive message
        db_cert2 = db_session.get(Certificate, cert2.id)
        assert db_cert2.status == CertificateStatus.FAILED
        assert db_cert2.file_path is None
        assert "Corrupt character encoding for recipient Bob Error" in db_cert2.error_message

        # Verify Charlie (Recipient 3) succeeded despite Recipient 2 failing
        db_cert3 = db_session.get(Certificate, cert3.id)
        assert db_cert3.status == CertificateStatus.SUCCESS
        assert db_cert3.file_path is not None
        assert db_cert3.error_message is None
        assert storage.get_absolute_path(db_cert3.file_path).exists()


def test_all_recipients_succeed(db_session):
    """Verifies that a job with 100% successful recipients transitions to COMPLETED."""
    job = Job(
        event_name="Cloud Workshop",
        issue_date=date(2026, 10, 15),
        status=JobStatus.PENDING,
        total_count=2,
    )
    cert1 = Certificate(recipient_name="Alice", recipient_email="alice@example.com")
    cert2 = Certificate(recipient_name="Bob", recipient_email="bob@example.com")
    job.certificates.extend([cert1, cert2])
    db_session.add(job)
    db_session.commit()

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = StorageService(base_dir=tmpdir)
        cert_service = CertificateService(storage_service=storage)

        processed_job = process_job(db=db_session, job_id=job.id, cert_service=cert_service)

        assert processed_job.status == JobStatus.COMPLETED
        assert processed_job.total_count == 2
        assert processed_job.success_count == 2
        assert processed_job.failure_count == 0
        assert processed_job.completed_at is not None


def test_all_recipients_fail(db_session):
    """Verifies that a job where all recipients fail transitions to COMPLETED_WITH_ERRORS."""
    job = Job(
        event_name="Workshop",
        issue_date=date(2026, 10, 15),
        status=JobStatus.PENDING,
        total_count=2,
    )
    cert1 = Certificate(recipient_name="Alice", recipient_email="alice@example.com")
    cert2 = Certificate(recipient_name="Bob", recipient_email="bob@example.com")
    job.certificates.extend([cert1, cert2])
    db_session.add(job)
    db_session.commit()

    mock_service = MagicMock(spec=CertificateService)
    mock_service.generate_and_save.side_effect = RuntimeError("Storage volume unmounted")

    processed_job = process_job(db=db_session, job_id=job.id, cert_service=mock_service)

    assert processed_job.status == JobStatus.COMPLETED_WITH_ERRORS
    assert processed_job.total_count == 2
    assert processed_job.success_count == 0
    assert processed_job.failure_count == 2
    assert processed_job.completed_at is not None

    certs = db_session.query(Certificate).filter(Certificate.job_id == job.id).all()
    for cert in certs:
        assert cert.status == CertificateStatus.FAILED
        assert "Storage volume unmounted" in cert.error_message
