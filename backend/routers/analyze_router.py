from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.source_pipeline import analyze_company, select_best_source

router = APIRouter()


class CompanyRequest(BaseModel):
    company: str


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.post("/select-best-source")
def select_best_source_route(payload: CompanyRequest):
    try:
        return select_best_source(payload.company)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/analyze-company")
def analyze_company_route(payload: CompanyRequest):
    try:
        return analyze_company(payload.company)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))