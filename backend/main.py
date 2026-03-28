from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import json
import os
from geopy.geocoders import Nominatim
from openai import AsyncOpenAI
from dotenv import load_dotenv
from routers.analyze_router import router

load_dotenv()
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

app.include_router(router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5176"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Claim(BaseModel):
    company: str
    claimed_hectares: float
    location: str
    year_start: int
    year_end: int

class ExplainRequest(BaseModel):
    company: str
    claim_summary: str | None = None
    location: str
    claimed_hectares: float
    year_start: int
    year_end: int
    truth_score: float
    verdict: str
    avg_loss_before_ha: float
    avg_loss_after_ha: float
    reduction_ha: float


MOCK_DATA = {
    "amazon": {
        "avg_loss_before_ha": 48200,
        "avg_loss_after_ha": 51400,
        "reduction_ha": -3200,
        "truth_score": 12.0,
        "verdict": "likely_false",
    },
    "apple": {
        "avg_loss_before_ha": 12000,
        "avg_loss_after_ha": 7800,
        "reduction_ha": 4200,
        "truth_score": 58.0,
        "verdict": "uncertain",
    },
    "microsoft": {
        "avg_loss_before_ha": 31000,
        "avg_loss_after_ha": 5800,
        "reduction_ha": 25200,
        "truth_score": 84.0,
        "verdict": "verified",
    },
    "meta": {
        "avg_loss_before_ha": 22000,
        "avg_loss_after_ha": 19500,
        "reduction_ha": 2500,
        "truth_score": 31.0,
        "verdict": "likely_false",
    },
    "exxon mobil": {
        "avg_loss_before_ha": 9800,
        "avg_loss_after_ha": 10200,
        "reduction_ha": -400,
        "truth_score": 5.0,
        "verdict": "likely_false",
    },
}


def geocode_location(location: str):
    geolocator = Nominatim(user_agent="greenlens")
    loc = geolocator.geocode(location)
    if not loc:
        raise HTTPException(status_code=400, detail=f"Could not geocode location: {location}")

    lat, lon = loc.latitude, loc.longitude
    return {
        "min_lat": lat - 1,
        "max_lat": lat + 1,
        "min_lon": lon - 1,
        "max_lon": lon + 1,
    }


async def query_gfw_loss(bbox: dict, year_start: int, year_end: int):
    url = "https://data-api.globalforestwatch.org/dataset/umd_tree_cover_loss/latest/query"
    sql = f"""
        SELECT umd_tree_cover_loss__year, SUM(umd_tree_cover_loss__ha) as loss_ha
        FROM umd_tree_cover_loss
        WHERE umd_tree_cover_loss__year BETWEEN {year_start} AND {year_end}
        GROUP BY umd_tree_cover_loss__year
        ORDER BY umd_tree_cover_loss__year
    """
    geometry = {
        "type": "Polygon",
        "coordinates": [[
            [bbox["min_lon"], bbox["min_lat"]],
            [bbox["max_lon"], bbox["min_lat"]],
            [bbox["max_lon"], bbox["max_lat"]],
            [bbox["min_lon"], bbox["max_lat"]],
            [bbox["min_lon"], bbox["min_lat"]],
        ]]
    }

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.post(url, json={"sql": sql, "geometry": geometry})
        resp.raise_for_status()
        body = resp.json()
        return body.get("data", [])


def compute_truth_score(loss_rows: list, year_start: int, claimed_hectares: float):
    if not loss_rows:
        return None

    if claimed_hectares <= 0:
        raise HTTPException(status_code=400, detail="claimed_hectares must be greater than 0")

    midpoint = year_start + (loss_rows[-1]["umd_tree_cover_loss__year"] - year_start) // 2
    before = [r for r in loss_rows if r["umd_tree_cover_loss__year"] <= midpoint]
    after = [r for r in loss_rows if r["umd_tree_cover_loss__year"] > midpoint]

    avg_before = sum(r["loss_ha"] for r in before) / len(before) if before else 0
    avg_after = sum(r["loss_ha"] for r in after) / len(after) if after else 0

    reduction = avg_before - avg_after
    score = min(max((reduction / claimed_hectares) * 100, 0), 100)

    if score >= 80:
        verdict = "verified"
    elif score >= 50:
        verdict = "uncertain"
    else:
        verdict = "likely_false"

    return {
        "avg_loss_before_ha": round(avg_before, 2),
        "avg_loss_after_ha": round(avg_after, 2),
        "reduction_ha": round(reduction, 2),
        "truth_score": round(score, 1),
        "verdict": verdict,
    }


@app.get("/")
def root():
    return {"status": "ok"}


@app.post("/explain")
async def explain(req: ExplainRequest):
    prompt = f"""You are an environmental fact-checker. A company made a sustainability pledge, and satellite data was used to verify it.

Company: {req.company}
Claim: {req.claim_summary or "A reforestation/sustainability pledge"}
Location: {req.location}
Claimed hectares: {req.claimed_hectares:,.0f} ha
Period: {req.year_start}–{req.year_end}

Satellite findings:
- Average annual forest loss BEFORE pledge: {req.avg_loss_before_ha:,.0f} ha/yr
- Average annual forest loss AFTER pledge: {req.avg_loss_after_ha:,.0f} ha/yr
- Net reduction in loss: {req.reduction_ha:,.0f} ha
- Truth Score: {req.truth_score}%
- Verdict: {req.verdict}

Write 2-3 sentences in plain English explaining what this data means and whether the company's claim holds up. Be direct and factual. Do not use bullet points or headers."""

    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )

    return {"explanation": response.choices[0].message.content.strip()}


@app.get("/search_claim/{company}")
async def search_claim(company: str):
    prompt = f"""Search the web for {company}'s most recent reforestation or tree planting sustainability commitment.

Extract ONLY real, cited information. Return a JSON object with these fields:
- "claim_summary": one sentence describing what they promised
- "trees_or_hectares": the number (e.g. "1 million trees" or "500000 hectares")
- "hectares": numeric estimate in hectares (convert if needed: 1 tree ≈ 0.001 ha, 1 acre = 0.4047 ha)
- "location": the single most significant or largest location mentioned — if multiple regions, pick the primary one (e.g. "Cerrado, Brazil" not just "Brazil")
- "year_start": the year the pledge was made (as integer)
- "year_end": the target completion year (as integer)
- "source_url": the URL where this information was found

If any field cannot be found, set it to null. Return JSON only, no extra text."""

    response = await openai_client.responses.create(
        model="gpt-4o-mini",
        tools=[{"type": "web_search_preview"}],
        input=prompt,
    )

    raw = response.output_text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Failed to parse OpenAI response: {raw[:300]}")

    # If model returned a list, take the first item
    if isinstance(data, list):
        if not data:
            raise HTTPException(status_code=500, detail="OpenAI returned empty list")
        data = data[0]

    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail=f"Unexpected response format: {type(data)}")

    # Geocode the location to coordinates
    coords = None
    if data.get("location"):
        try:
            bbox = geocode_location(data["location"])
            coords = {
                "lat": (bbox["min_lat"] + bbox["max_lat"]) / 2,
                "lon": (bbox["min_lon"] + bbox["max_lon"]) / 2,
            }
        except Exception:
            pass

    return {"company": company, **data, "coords": coords}


@app.post("/verify")
async def verify(claim: Claim):
    mock = MOCK_DATA.get(claim.company.lower())
    if mock:
        return {
            "company": claim.company,
            "location": claim.location,
            "claimed_hectares": claim.claimed_hectares,
            "year_start": claim.year_start,
            "year_end": claim.year_end,
            **mock,
        }

    bbox = geocode_location(claim.location)
    loss_rows = await query_gfw_loss(bbox, claim.year_start, claim.year_end)
    result = compute_truth_score(loss_rows, claim.year_start, claim.claimed_hectares)

    if result is None:
        raise HTTPException(status_code=404, detail="No satellite data found for this region/timeframe")

    return {
        "company": claim.company,
        "location": claim.location,
        "claimed_hectares": claim.claimed_hectares,
        "year_start": claim.year_start,
        "year_end": claim.year_end,
        **result,
    }