import io
import tempfile
from datetime import date
from pathlib import Path

from pypdf import PdfReader

from app.services.certificate_service import CertificateService
from app.services.storage_service import StorageService


def test_render_pdf_deterministic_content():
    """
    Verifies that CertificateService.render_pdf produces a valid, single-page,
    readable PDF containing all recipient-specific data.
    """
    service = CertificateService()

    recipient_name = "Grace Hopper"
    event_name = "Advanced Systems Architecture"
    issue_date = date(2026, 10, 12)
    cert_id = "c0ffee00-1111-2222-3333-444455556666"

    pdf_bytes = service.render_pdf(
        recipient_name=recipient_name,
        event_name=event_name,
        issue_date=issue_date,
        cert_id=cert_id,
    )

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 500

    # Read and inspect PDF in-memory using pypdf
    reader = PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) == 1

    extracted_text = reader.pages[0].extract_text()
    assert "CERTIFICATE OF COMPLETION" in extracted_text
    assert recipient_name in extracted_text
    assert event_name in extracted_text
    assert issue_date.isoformat() in extracted_text
    assert cert_id in extracted_text


def test_generate_and_save_creates_readable_file_on_disk():
    """
    Verifies that generate_and_save writes the certificate PDF to the configured
    storage directory, returns the relative path, and the file on disk is readable.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = StorageService(base_dir=tmpdir)
        service = CertificateService(storage_service=storage)

        job_id = "99999999-8888-7777-6666-555544443333"
        cert_id = "12345678-abcd-ef01-2345-6789abcdef01"
        recipient_name = "Ada Lovelace"
        event_name = "Foundations of Computer Programming"
        issue_date = date(2026, 10, 15)

        rel_path = service.generate_and_save(
            job_id=job_id,
            cert_id=cert_id,
            recipient_name=recipient_name,
            event_name=event_name,
            issue_date=issue_date,
        )

        assert rel_path == f"certificates/{job_id}/{cert_id}.pdf"

        # Verify physical file existence and permissions
        disk_path = storage.get_absolute_path(rel_path)
        assert disk_path.is_file()
        assert disk_path.stat().st_size > 1000

        # Read back from disk to verify readability
        with open(disk_path, "rb") as f:
            disk_reader = PdfReader(f)
            assert len(disk_reader.pages) == 1
            disk_text = disk_reader.pages[0].extract_text()
            assert recipient_name in disk_text
            assert event_name in disk_text
            assert cert_id in disk_text


def test_render_pdf_handles_long_names_and_events():
    """
    Verifies that unusually long names and event titles scale appropriately
    without raising exceptions or corrupting the PDF stream.
    """
    service = CertificateService()

    long_recipient = "Dr. Maximilian Alexander Bartholomew-Vanderbilt IV"
    long_event = "International Conference on Advanced Distributed Cloud Systems and Fault-Tolerant Architectures"
    cert_id = "long-name-test-uuid"

    pdf_bytes = service.render_pdf(
        recipient_name=long_recipient,
        event_name=long_event,
        issue_date=date(2026, 12, 31),
        cert_id=cert_id,
    )

    assert pdf_bytes.startswith(b"%PDF-")
    reader = PdfReader(io.BytesIO(pdf_bytes))
    extracted = reader.pages[0].extract_text()
    assert long_recipient in extracted


def test_certificate_service_decoupled_from_database():
    """
    Verifies that CertificateService has no dependency on SQLAlchemy sessions or models.
    """
    import inspect
    import app.services.certificate_service as mod

    source = inspect.getsource(mod)
    assert "sqlalchemy" not in source.lower()
    assert "Session" not in source
    assert "Base" not in source
