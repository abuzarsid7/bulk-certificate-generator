from fastapi import APIRouter

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Endpoints are added in later steps (create job, status, list certificates, download).
