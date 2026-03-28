# backend/routers/analyze_router.py

from fastapi import APIRouter, HTTPException
from services.vector_pipeline import analyze_pdf
import os

router = APIRouter()


@router.post("/analyze")
def analyze(company: dict):
    company_name = company.get("company", "").lower().strip()

    if not company_name:
        raise HTTPException(status_code=400, detail="Missing company name")

    folder = "data/reports"

    if not os.path.exists(folder):
        raise HTTPException(status_code=500, detail="data/reports folder not found")

    file = None
    for f in os.listdir(folder):
        if f.lower().startswith(company_name):
            file = f
            break

    if not file:
        raise HTTPException(status_code=404, detail="PDF not found")

    pdf_path = os.path.join(folder, file)
    extracted = analyze_pdf(pdf_path, company_name)

    return {
        "company": company_name,
        "file_used": file,
        **extracted
    }