from fastapi import APIRouter
from services.vector_pipeline import analyze_pdf  # ✅ updated import
import os

router = APIRouter()

@router.post("/analyze")
def analyze(company: dict):
    company_name = company.get("company").lower()

    folder = "data/reports"

    # ✅ find matching file (handles amazon_2024.pdf etc.)
    file = None
    for f in os.listdir(folder):
        if f.lower().startswith(company_name):
            file = f
            break

    if not file:
        return {"error": "PDF not found"}

    pdf_path = os.path.join(folder, file)

    results = analyze_pdf(pdf_path)

    return {
        "company": company_name,
        "file_used": file,
        "matches": results
    }