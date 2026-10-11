from fastapi import APIRouter

router = APIRouter(prefix="/certificates", tags=["certificates"])

# Endpoints are added in later steps (metadata, download).
