from datetime import date

from app.models import Certificate, CertificateStatus, Job, JobStatus


def test_job_and_certificate_roundtrip(db_session):
    job = Job(event_name="Bootcamp", issue_date=date(2026, 10, 15), total_count=1)
    job.certificates.append(Certificate(recipient_name="Alex", recipient_email="alex@example.com"))
    db_session.add(job)
    db_session.commit()

    loaded = db_session.get(Job, job.id)
    assert loaded.status == JobStatus.PENDING
    assert loaded.created_at is not None
    assert loaded.certificates[0].status == CertificateStatus.PENDING


def test_deleting_job_removes_certificates(db_session):
    job = Job(event_name="E", issue_date=date(2026, 1, 1), total_count=1)
    job.certificates.append(Certificate(recipient_name="A", recipient_email="a@example.com"))
    db_session.add(job)
    db_session.commit()

    db_session.delete(job)
    db_session.commit()
    assert db_session.query(Certificate).count() == 0
