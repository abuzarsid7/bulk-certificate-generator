import os
from pathlib import Path

from app.core.config import get_settings


class StorageService:
    """Handles persistence of generated certificate artifacts to disk."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir or get_settings().storage_dir)

    def save_certificate_pdf(self, job_id: str, cert_id: str, pdf_bytes: bytes) -> str:
        """
        Saves certificate PDF bytes atomically using a temporary file and rename.
        Returns the relative path to the stored file.
        """
        job_dir = self.base_dir / "certificates" / str(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        target_path = job_dir / f"{cert_id}.pdf"
        temp_path = job_dir / f"{cert_id}.tmp"

        with open(temp_path, "wb") as f:
            f.write(pdf_bytes)

        os.replace(temp_path, target_path)
        return str(target_path.relative_to(self.base_dir))

    def get_absolute_path(self, relative_path: str) -> Path:
        return self.base_dir / relative_path
