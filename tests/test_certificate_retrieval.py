import io
import tempfile
import uuid
from datetime import date

import pytest
from pypdf import PdfReader

from app.main import app
from app.models.certificate import Certificate, CertificateStatus
from app.models.job import Job, JobStatus
from app.services.certificate_service import CertificateService
from app.services.storage_service import StorageService, get_storage_service


@pytest.fixture
def temp_storage():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = StorageService(base_dir=tmpdir)
        app.dependency_overrides[get_storage_service] = lambda: storage
        try:
            yield storage
        finally:
            app.dependency_overrides.pop(get_storage_service, None)


def test_get_certificate_not_found(client):
    """GET /api/v1/certificates/{id} returns 404 when certificate does not exist."""
    random_id = uuid.uuid4()
    response = client.get(f"/api/v1/certificates/{random_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Certificate not found"


def test_get_certificate_invalid_uuid(client):
    """GET /api/v1/certificates/{id} returns 422 when path param is not a valid UUID."""
    response = client.get("/api/v1/certificates/not-a-uuid")
    assert response.status_code == 422


def test_get_certificate_pending_status_returns_409(client, db_session):
    """GET /api/v1/certificates/{id} returns 409 Conflict when status is PENDING."""
    job = Job(event_name="Workshop", issue_date=date(2026, 10, 15), status=JobStatus.PENDING)
    cert = Certificate(
        job=job,
        recipient_name="Alice",
        recipient_email="alice@example.com",
        status=CertificateStatus.PENDING,
    )
    db_session.add_all([job, cert])
    db_session.commit()

    response = client.get(f"/api/v1/certificates/{cert.id}")
    assert response.status_code == 409
    assert "not completed" in response.json()["detail"].lower()
    assert "pending" in response.json()["detail"].lower()


def test_get_certificate_processing_status_returns_409(client, db_session):
    """GET /api/v1/certificates/{id} returns 409 Conflict when status is PROCESSING."""
    job = Job(event_name="Workshop", issue_date=date(2026, 10, 15), status=JobStatus.PROCESSING)
    cert = Certificate(
        job=job,
        recipient_name="Bob",
        recipient_email="bob@example.com",
        status=CertificateStatus.PROCESSING,
    )
    db_session.add_all([job, cert])
    db_session.commit()

    response = client.get(f"/api/v1/certificates/{cert.id}")
    assert response.status_code == 409
    assert "not completed" in response.json()["detail"].lower()
    assert "processing" in response.json()["detail"].lower()


def test_get_certificate_failed_status_returns_409(client, db_session):
    """GET /api/v1/certificates/{id} returns 409 Conflict with error details when status is FAILED."""
    job = Job(event_name="Workshop", issue_date=date(2026, 10, 15), status=JobStatus.FAILED)
    cert = Certificate(
        job=job,
        recipient_name="Charlie",
        recipient_email="charlie@example.com",
        status=CertificateStatus.FAILED,
        error_message="Font descriptor rendering failure",
    )
    db_session.add_all([job, cert])
    db_session.commit()

    response = client.get(f"/api/v1/certificates/{cert.id}")
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "failed" in detail.lower()
    assert "Font descriptor rendering failure" in detail


def test_get_certificate_success_returns_pdf(client, db_session, temp_storage):
    """
    GET /api/v1/certificates/{id} returns 200 OK and valid PDF bytes
    when generation completed successfully.
    """
    job = Job(
        event_name="Void Excel Cloud Architecture",
        issue_date=date(2026, 10, 12),
        status=JobStatus.COMPLETED,
    )
    cert_id = uuid.uuid4()
    cert = Certificate(
        id=cert_id,
        job=job,
        recipient_name="Dana Scott",
        recipient_email="dana@example.com",
        status=CertificateStatus.SUCCESS,
    )
    db_session.add_all([job, cert])
    db_session.commit()

    # Generate and store physical PDF in temp storage
    cert_service = CertificateService(storage_service=temp_storage)
    file_path = cert_service.generate_and_save(
        job_id=str(job.id),
        cert_id=str(cert.id),
        recipient_name=cert.recipient_name,
        event_name=job.event_name,
        issue_date=job.issue_date,
    )
    cert.file_path = file_path
    db_session.commit()

    response = client.get(f"/api/v1/certificates/{cert.id}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")

    # Verify readable PDF content
    reader = PdfReader(io.BytesIO(response.content))
    assert len(reader.pages) == 1
    extracted_text = reader.pages[0].extract_text()
    assert "Dana Scott" in extracted_text
    assert "Void Excel Cloud Architecture" in extracted_text


def test_get_certificate_success_missing_file_on_disk_returns_404(client, db_session, temp_storage):
    """
    GET /api/v1/certificates/{id} returns 404 without leaking server paths
    when the database status is SUCCESS but the file is missing from disk.
    """
    job_id = uuid.uuid4()
    job = Job(
        id=job_id,
        event_name="Workshop",
        issue_date=date(2026, 10, 15),
        status=JobStatus.COMPLETED,
    )
    cert_id = uuid.uuid4()
    cert = Certificate(
        id=cert_id,
        job=job,
        recipient_name="Eve",
        recipient_email="eve@example.com",
        status=CertificateStatus.SUCCESS,
        file_path=f"certificates/{job_id}/{cert_id}.pdf",
    )
    db_session.add_all([job, cert])
    db_session.commit()

    response = client.get(f"/api/v1/certificates/{cert.id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Certificate file not found"
    # Verify no arbitrary server filesystem paths are exposed
    assert str(temp_storage.base_dir) not in response.text


def test_get_certificate_security_prevents_arbitrary_path_traversal(client, db_session, temp_storage):
    """
    GET /api/v1/certificates/{id} refuses to serve files if file_path attempts traversal.
    """
    job_id = uuid.uuid4()
    job = Job(
        id=job_id,
        event_name="Workshop",
        issue_date=date(2026, 10, 15),
        status=JobStatus.COMPLETED,
    )
    cert_id = uuid.uuid4()
    cert = Certificate(
        id=cert_id,
        job=job,
        recipient_name="Frank",
        recipient_email="frank@example.com",
        status=CertificateStatus.SUCCESS,
        file_path=f"../../certificates/{job_id}/{cert_id}.pdf",
    )
    db_session.add_all([job, cert])
    db_session.commit()

    response = client.get(f"/api/v1/certificates/{cert.id}")
    assert response.status_code == 403
    assert str(temp_storage.base_dir) not in response.text


def test_get_certificate_ensures_file_belongs_to_requested_record(client, db_session, temp_storage):
    """
    GET /api/v1/certificates/{id} verifies that the target file path strictly matches
    the queried certificate record ID and job ID.
    """
    job = Job(
        event_name="Security Summit",
        issue_date=date(2026, 10, 12),
        status=JobStatus.COMPLETED,
    )
    cert_a_id = uuid.uuid4()
    cert_b_id = uuid.uuid4()
    cert_a = Certificate(
        id=cert_a_id,
        job=job,
        recipient_name="Grace",
        recipient_email="grace@example.com",
        status=CertificateStatus.SUCCESS,
    )
    cert_b = Certificate(
        id=cert_b_id,
        job=job,
        recipient_name="Heidi",
        recipient_email="heidi@example.com",
        status=CertificateStatus.SUCCESS,
    )
    db_session.add_all([job, cert_a, cert_b])
    db_session.commit()

    # Create actual file for cert_b
    cert_service = CertificateService(storage_service=temp_storage)
    b_path = cert_service.generate_and_save(
        job_id=str(job.id),
        cert_id=str(cert_b.id),
        recipient_name=cert_b.recipient_name,
        event_name=job.event_name,
        issue_date=job.issue_date,
    )
    cert_b.file_path = b_path

    # Deliberately point cert_a's file_path to cert_b's file
    cert_a.file_path = b_path
    db_session.commit()

    # Requesting cert_a should be rejected because file path does not belong to cert_a
    response = client.get(f"/api/v1/certificates/{cert_a.id}")
    assert response.status_code == 403
    assert "does not belong to the requested record" in response.json()["detail"]
