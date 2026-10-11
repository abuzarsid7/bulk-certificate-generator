import uuid
from unittest.mock import patch

import pytest

from app.models.certificate import Certificate, CertificateStatus
from app.models.job import Job, JobStatus


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_routers_mounted(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/health" in paths
    assert "/api/v1/jobs" in paths


def test_unknown_job_route_is_404(client):
    assert client.get("/api/v1/jobs/does-not-exist").status_code == 404


def test_create_job_success(client, db_session):
    payload = {
        "event_name": "Cloud Architecture Workshop",
        "issue_date": "2026-10-15",
        "recipients": [
            {"name": "Alice Smith", "email": "alice@example.com"},
            {"name": "Bob Jones", "email": "bob@example.com"},
            {"name": "Charlie Brown", "email": "charlie@example.com"},
        ],
    }

    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202

    data = response.json()
    job_id = data["job_id"]
    assert data["id"] == job_id
    assert uuid.UUID(job_id)
    assert data["status"] == "pending"
    assert data["total_count"] == 3
    assert data["event_name"] == "Cloud Architecture Workshop"
    assert response.headers.get("Location") == f"/api/v1/jobs/{job_id}"

    # Verify Job record in database
    db_job = db_session.get(Job, uuid.UUID(job_id))
    assert db_job is not None
    assert db_job.status == JobStatus.PENDING
    assert db_job.total_count == 3
    assert db_job.success_count == 0
    assert db_job.failure_count == 0
    assert db_job.completed_at is None

    # Verify Certificate records in database
    certs = (
        db_session.query(Certificate)
        .filter(Certificate.job_id == db_job.id)
        .order_by(Certificate.recipient_name)
        .all()
    )
    assert len(certs) == 3
    for cert in certs:
        assert cert.status == CertificateStatus.PENDING
        assert cert.file_path is None  # Verifies NO PDFs were generated synchronously
        assert cert.error_message is None

    assert certs[0].recipient_name == "Alice Smith"
    assert certs[0].recipient_email == "alice@example.com"
    assert certs[1].recipient_name == "Bob Jones"
    assert certs[1].recipient_email == "bob@example.com"
    assert certs[2].recipient_name == "Charlie Brown"
    assert certs[2].recipient_email == "charlie@example.com"


def test_create_job_rejects_malformed_recipient_email(client, db_session):
    payload = {
        "event_name": "Workshop",
        "issue_date": "2026-10-15",
        "recipients": [
            {"name": "Alice", "email": "not-a-valid-email"},
        ],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
    assert db_session.query(Job).count() == 0
    assert db_session.query(Certificate).count() == 0


def test_create_job_rejects_empty_recipient_name(client, db_session):
    payload = {
        "event_name": "Workshop",
        "issue_date": "2026-10-15",
        "recipients": [
            {"name": "", "email": "alice@example.com"},
        ],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
    assert db_session.query(Job).count() == 0
    assert db_session.query(Certificate).count() == 0


def test_create_job_rejects_empty_recipients_list(client, db_session):
    payload = {
        "event_name": "Workshop",
        "issue_date": "2026-10-15",
        "recipients": [],
    }
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
    assert db_session.query(Job).count() == 0
    assert db_session.query(Certificate).count() == 0


def test_create_job_transactional_rollback_on_error(db_session):
    from app.schemas.job import JobCreate
    from app.services.job_service import create_job

    payload = JobCreate(
        event_name="Workshop",
        issue_date="2026-10-15",
        recipients=[
            {"name": "Alice", "email": "alice@example.com"},
        ],
    )

    # Simulate an error during certificate creation to verify rollback
    with patch("app.services.job_service.Certificate", side_effect=RuntimeError("Simulated DB failure")):
        with pytest.raises(RuntimeError, match="Simulated DB failure"):
            create_job(db_session, payload)

    # Assert neither Job nor Certificate was persisted
    assert db_session.query(Job).count() == 0
    assert db_session.query(Certificate).count() == 0
