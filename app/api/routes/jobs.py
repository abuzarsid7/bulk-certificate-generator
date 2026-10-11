from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.job import JobCreate, JobCreateResponse
from app.services.job_service import create_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
def create_generation_job(
    payload: JobCreate,
    response: Response,
    db: Session = Depends(get_db),
) -> JobCreateResponse:
    job = create_job(db, payload)
    response.headers["Location"] = f"/api/v1/jobs/{job.id}"
    try:
        from app.workers.tasks import process_certificate_job
        process_certificate_job.delay(str(job.id))
    except Exception:
        pass
    return job
