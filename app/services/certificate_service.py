import io
from datetime import date

from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas

from app.services.storage_service import StorageService


class CertificateService:
    """Renders PDF certificates and writes them via StorageService."""

    def __init__(self, storage_service: StorageService | None = None) -> None:
        self.storage_service = storage_service or StorageService()

    def render_pdf(
        self,
        recipient_name: str,
        event_name: str,
        issue_date: date,
        cert_id: str,
    ) -> bytes:
        """Draws a clean, styled certificate using ReportLab."""
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=landscape(letter))
        width, height = landscape(letter)

        # Decorative outer & inner border
        c.setStrokeColorRGB(0.12, 0.22, 0.42)
        c.setLineWidth(4)
        c.rect(30, 30, width - 60, height - 60)
        c.setLineWidth(1)
        c.rect(36, 36, width - 72, height - 72)

        # Header Title
        c.setFont("Helvetica-Bold", 30)
        c.drawCentredString(width / 2, height - 120, "CERTIFICATE OF COMPLETION")

        # Subtitle
        c.setFont("Helvetica", 15)
        c.drawCentredString(width / 2, height - 160, "This is proudly presented to")

        # Recipient Name (prominently centered)
        c.setFont("Helvetica-Bold", 26)
        c.drawCentredString(width / 2, height - 210, recipient_name)

        # Event description
        c.setFont("Helvetica", 15)
        c.drawCentredString(
            width / 2,
            height - 260,
            f"for successful participation in {event_name}",
        )

        # Date & Unique Certificate ID
        c.setFont("Helvetica", 11)
        c.drawString(50, 50, f"Date: {issue_date.isoformat()}")
        c.drawRightString(width - 50, 50, f"Certificate ID: {cert_id}")

        c.showPage()
        c.save()
        return buffer.getvalue()

    def generate_and_save(
        self,
        job_id: str,
        cert_id: str,
        recipient_name: str,
        event_name: str,
        issue_date: date,
    ) -> str:
        """Renders and saves a certificate, returning its relative file path."""
        pdf_bytes = self.render_pdf(
            recipient_name=recipient_name,
            event_name=event_name,
            issue_date=issue_date,
            cert_id=cert_id,
        )
        return self.storage_service.save_certificate_pdf(
            job_id=job_id,
            cert_id=cert_id,
            pdf_bytes=pdf_bytes,
        )
