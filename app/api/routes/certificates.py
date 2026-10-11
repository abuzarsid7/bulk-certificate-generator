import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.certificate import Certificate, CertificateStatus
from app.services.storage_service import StorageService, get_storage_service

router = APIRouter(prefix="/certificates", tags=["certificates"])


@router.get(
    "/{certificate_id}",
    response_class=FileResponse,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Returns the generated certificate PDF file.",
        },
        404: {"description": "Certificate not found or file missing on disk."},
        409: {"description": "Certificate generation has not completed or failed."},
        403: {"description": "Access forbidden or integrity violation."},
    },
)
def get_certificate(
    certificate_id: uuid.UUID,
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> FileResponse:
    cert = db.get(Certificate, certificate_id)
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found",
        )

    # 409 if generation has not completed
    if cert.status in (CertificateStatus.PENDING, CertificateStatus.PROCESSING):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Certificate generation has not completed (status: {cert.status.value})",
        )

    if cert.status == CertificateStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Certificate generation failed: {cert.error_message or 'Generation error'}",
        )

    if cert.status != CertificateStatus.SUCCESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Certificate generation has not completed (status: {cert.status.value})",
        )

    # Verify that a file path is recorded
    if not cert.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate file not found",
        )

    # Security check: Ensure the requested file belongs strictly to this generated certificate record
    # The file path must match the certificate ID and belong to the job's directory
    file_path_obj = Path(cert.file_path)
    if file_path_obj.name != f"{cert.id}.pdf" or str(cert.job_id) not in file_path_obj.parts:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Certificate file does not belong to the requested record",
        )

    # Prevent arbitrary filesystem paths outside the configured storage directory
    try:
        abs_path = storage.resolve_safe_path(cert.file_path)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid certificate storage path",
        )

    # Ensure file physically exists on disk
    if not abs_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate file not found",
        )

    return FileResponse(
        path=abs_path,
        media_type="application/pdf",
        filename=f"certificate-{cert.id}.pdf",
    )

