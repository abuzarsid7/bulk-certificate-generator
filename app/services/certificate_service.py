import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas

from app.services.storage_service import StorageService


class CertificateService:
    """
    Renders PDF certificates based on a predefined template and persists them
    via StorageService.

    Architecture Note:
    This service is strictly decoupled from the database layer. It only accepts
    domain-level values and does not import or execute any database ORM models or queries,
    making it completely deterministic and unit-testable in isolation.
    """

    def __init__(self, storage_service: StorageService | None = None) -> None:
        self.storage_service = storage_service or StorageService()

    def render_pdf(
        self,
        recipient_name: str,
        event_name: str,
        issue_date: date,
        cert_id: str,
    ) -> bytes:
        """
        Renders a deterministic certificate PDF into in-memory bytes using ReportLab.
        Uses a predefined landscape template layout with double borders, title,
        dynamic recipient text, event description, date, and unique certificate ID.
        """
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=landscape(letter))
        width, height = landscape(letter)

        # 1. Outer Dark Navy Border
        c.setStrokeColor(colors.HexColor("#1A365D"))
        c.setLineWidth(5)
        c.rect(30, 30, width - 60, height - 60)

        # 2. Inner Gold Accent Border
        c.setStrokeColor(colors.HexColor("#D69E2E"))
        c.setLineWidth(1.5)
        c.rect(38, 38, width - 76, height - 76)

        # 3. Corner Accent Flourishes
        c.setFillColor(colors.HexColor("#1A365D"))
        c.circle(48, 48, 4, fill=1, stroke=0)
        c.circle(width - 48, 48, 4, fill=1, stroke=0)
        c.circle(48, height - 48, 4, fill=1, stroke=0)
        c.circle(width - 48, height - 48, 4, fill=1, stroke=0)

        # 4. Header: Predefined Certificate Title
        c.setFillColor(colors.HexColor("#1A365D"))
        c.setFont("Helvetica-Bold", 30)
        c.drawCentredString(width / 2, height - 120, "CERTIFICATE OF COMPLETION")

        # 5. Subtitle
        c.setFillColor(colors.HexColor("#4A5568"))
        c.setFont("Helvetica", 15)
        c.drawCentredString(width / 2, height - 165, "This is proudly presented to")

        # 6. Recipient Name (with dynamic scaling for length)
        c.setFillColor(colors.HexColor("#2B6CB0"))
        name_len = len(recipient_name)
        if name_len > 35:
            name_font_size = 18
        elif name_len > 25:
            name_font_size = 22
        else:
            name_font_size = 28
        c.setFont("Helvetica-Bold", name_font_size)
        c.drawCentredString(width / 2, height - 215, recipient_name)

        # Decorative line under name
        c.setStrokeColor(colors.HexColor("#CBD5E0"))
        c.setLineWidth(1)
        name_width = min(max(c.stringWidth(recipient_name, "Helvetica-Bold", name_font_size) + 40, 200), width - 160)
        c.line((width - name_width) / 2, height - 225, (width + name_width) / 2, height - 225)

        # 7. Event Description (with scaling)
        c.setFillColor(colors.HexColor("#4A5568"))
        event_len = len(event_name)
        event_font_size = 13 if event_len > 50 else 15
        c.setFont("Helvetica", event_font_size)
        c.drawCentredString(
            width / 2,
            height - 270,
            f"for successful participation in {event_name}",
        )

        # 8. Footer: Issue Date & Unique Certificate ID
        c.setFillColor(colors.HexColor("#718096"))
        c.setFont("Helvetica", 10)
        c.drawString(55, 55, f"Issued Date: {issue_date.isoformat()}")
        c.drawRightString(width - 55, 55, f"Certificate ID: {cert_id}")

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
        """
        Generates the certificate PDF and saves it to the configured storage directory.
        Returns the relative path of the created file.
        """
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
