from datetime import datetime
import json
import os
import re

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from geopy.geocoders import Nominatim
from openai import AsyncOpenAI
from pydantic import BaseModel

from routers.analyze_router import router
from services.source_pipeline import _extract_primary_location

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
GFW_API_KEY = os.getenv("GFW_API_KEY", "").strip()

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

app = FastAPI()

app.include_router(router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5176"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# IMPORTANT:
# v1.12 supports loss years through 2024 based on the current dataset notes.
# If you later switch to a newer dataset version, update this constant.
GFW_TREE_COVER_LOSS_MAX_YEAR = 2024


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


def geocode_location(location: str) -> dict:
    geolocator = Nominatim(user_agent="greenlens")
    loc = geolocator.geocode(location)

    if not loc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not geocode location: {location}"
        )

    lat, lon = loc.latitude, loc.longitude

    return {
        "min_lat": lat - 1,
        "max_lat": lat + 1,
        "min_lon": lon - 1,
        "max_lon": lon + 1,
    }


def build_bbox_polygon(bbox: dict) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [[
            [bbox["min_lon"], bbox["min_lat"]],
            [bbox["max_lon"], bbox["min_lat"]],
            [bbox["max_lon"], bbox["max_lat"]],
            [bbox["min_lon"], bbox["max_lat"]],
            [bbox["min_lon"], bbox["min_lat"]],
        ]]
    }


def clamp_loss_years(year_start: int, year_end: int) -> tuple[int, int]:
    if year_end < year_start:
        raise HTTPException(
            status_code=400,
            detail="year_end must be greater than or equal to year_start"
        )

    # Tree cover loss starts in 2001 for this dataset family.
    year_start = max(year_start, 2001)
    year_end = min(year_end, GFW_TREE_COVER_LOSS_MAX_YEAR)

    if year_start > year_end:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No supported GFW tree cover loss years in requested range. "
                f"Supported range is 2001-{GFW_TREE_COVER_LOSS_MAX_YEAR}."
            )
        )

    return year_start, year_end


async def query_gfw_loss(bbox: dict, year_start: int, year_end: int) -> list:
    if not GFW_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Missing GFW_API_KEY in environment."
        )

    year_start, year_end = clamp_loss_years(year_start, year_end)

    url = "https://data-api.globalforestwatch.org/dataset/umd_tree_cover_loss/latest/query/json"

    sql = f"""
        SELECT
            umd_tree_cover_loss__year,
            SUM(umd_tree_cover_loss__ha) AS loss_ha
        FROM umd_tree_cover_loss
        WHERE umd_tree_cover_loss__year >= {year_start}
          AND umd_tree_cover_loss__year <= {year_end}
        GROUP BY umd_tree_cover_loss__year
        ORDER BY umd_tree_cover_loss__year
    """

    geometry = build_bbox_polygon(bbox)

    headers = {
        "Content-Type": "application/json",
        "x-api-key": GFW_API_KEY,
        "Origin": "http://localhost",
    }

    payload = {
        "sql": sql,
        "geometry": geometry,
    }

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        try:
            print(f"DEBUG: GFW key starts with: {GFW_API_KEY[:10]}...")
            print(f"DEBUG: Querying GFW URL: {url}")
            print(f"DEBUG: Clamped years: {year_start} to {year_end}")
            print(f"DEBUG: SQL: {sql}")

            resp = await client.post(url, json=payload, headers=headers)

            print(f"DEBUG: GFW status: {resp.status_code}")
            print(f"DEBUG: GFW response body: {resp.text[:1000]}")

            resp.raise_for_status()

            body = resp.json()
            return body.get("data", [])

        except httpx.HTTPStatusError as e:
            error_text = e.response.text[:1000] if e.response is not None else str(e)

            # If GFW still complains about year encoding, surface a cleaner message.
            if "pixel encoding" in error_text.lower():
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Requested years exceed supported GFW data range. "
                        f"Supported range for this dataset is 2001-{GFW_TREE_COVER_LOSS_MAX_YEAR}."
                    )
                )

            raise HTTPException(
                status_code=502,
                detail=f"GFW API request failed: {error_text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Could not reach GFW API: {str(e)}"
            )


def compute_truth_score(loss_rows: list, year_start: int, claimed_hectares: float):
    if not loss_rows:
        return None

    if claimed_hectares <= 0:
        raise HTTPException(
            status_code=400,
            detail="claimed_hectares must be greater than 0"
        )

    last_year = loss_rows[-1]["umd_tree_cover_loss__year"]
    midpoint = year_start + (last_year - year_start) // 2

    before = [r for r in loss_rows if r["umd_tree_cover_loss__year"] <= midpoint]
    after = [r for r in loss_rows if r["umd_tree_cover_loss__year"] > midpoint]

    avg_before = sum(r["loss_ha"] for r in before) / len(before) if before else 0
    avg_after = sum(r["loss_ha"] for r in after) / len(after) if after else 0

    reduction = avg_before - avg_after
    score = min(max((reduction / claimed_hectares) * 100, 0), 100)

    if score >= 80:
        verdict = "consistent"
    elif score >= 50:
        verdict = "inconclusive"
    else:
        verdict = "inconsistent"

    return {
        "avg_loss_before_ha": round(avg_before, 2),
        "avg_loss_after_ha": round(avg_after, 2),
        "reduction_ha": round(reduction, 2),
        "truth_score": round(score, 1),
        "verdict": verdict,
    }


@app.get("/")
def root():
    return {
        "status": "ok",
        "openai_configured": bool(OPENAI_API_KEY),
        "gfw_configured": bool(GFW_API_KEY),
        "gfw_loss_max_year": GFW_TREE_COVER_LOSS_MAX_YEAR,
    }


@app.post("/explain")
async def explain(req: ExplainRequest):
    if not openai_client:
        raise HTTPException(
            status_code=500,
            detail="Missing OPENAI_API_KEY in environment."
        )

    prompt = f"""You are an environmental data analyst. A company made a sustainability pledge, and satellite forest-loss data was used to assess it.

Company: {req.company}
Claim: {req.claim_summary or "A reforestation/sustainability pledge"}
Location: {req.location}
Claimed hectares: {req.claimed_hectares:,.0f} ha
Period: {req.year_start}–{req.year_end}

Satellite findings:
- Average annual forest loss BEFORE pledge period: {req.avg_loss_before_ha:,.0f} ha/yr
- Average annual forest loss AFTER pledge period: {req.avg_loss_after_ha:,.0f} ha/yr
- Net change in loss: {req.reduction_ha:,.0f} ha
- Truth Score: {req.truth_score}%
- Verdict: {req.verdict}

Write 2-3 sentences in plain English describing what the satellite data shows. Be honest that this data measures correlation, not causation — changes in forest loss in the region could reflect the company's efforts, but may also be influenced by factors outside their control such as natural disasters, drought, government policy changes, or broader land-use trends. Do not declare the company guilty or innocent. Do not use bullet points or headers."""

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return {"explanation": response.choices[0].message.content.strip()}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"OpenAI explanation failed: {str(e)}"
        )


@app.get("/search_claim/{company}")
async def search_claim(company: str):
    if not openai_client:
        raise HTTPException(
            status_code=500,
            detail="Missing OPENAI_API_KEY in environment."
        )

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

    try:
        response = await openai_client.responses.create(
            model="gpt-4o-mini",
            tools=[{"type": "web_search_preview"}],
            input=prompt,
        )

        raw = response.output_text.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        data = json.loads(raw)

        if isinstance(data, list):
            if not data:
                raise HTTPException(status_code=500, detail="OpenAI returned an empty list")
            data = data[0]

        if not isinstance(data, dict):
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected response format: {type(data)}"
            )

        # Clamp huge future targets like 2050 so /verify does not break.
        if isinstance(data.get("year_start"), int):
            data["year_start"] = max(2001, data["year_start"])

        if isinstance(data.get("year_end"), int):
            data["year_end"] = min(data["year_end"], GFW_TREE_COVER_LOSS_MAX_YEAR)

        coords = None
        primary_location = None

        if data.get("location"):
            raw_location = data["location"]
            primary_location, lat, lng = _extract_primary_location(raw_location)

            if primary_location and lat is not None and lng is not None:
                coords = {
                    "lat": lat,
                    "lon": lng,
                }

        result = {"company": company, **data, "coords": coords}
        if primary_location:
            result["primary_location"] = primary_location

        return result

    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse OpenAI response: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search claim failed: {str(e)}"
        )


@app.post("/verify")
async def verify(claim: Claim):
    bbox = geocode_location(claim.location)
    clamped_start, clamped_end = clamp_loss_years(claim.year_start, claim.year_end)
    loss_rows = await query_gfw_loss(bbox, clamped_start, clamped_end)
    result = compute_truth_score(loss_rows, clamped_start, claim.claimed_hectares)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="No satellite data found for this region/timeframe"
        )

    return {
        "company": claim.company,
        "location": claim.location,
        "claimed_hectares": claim.claimed_hectares,
        "year_start": clamped_start,
        "year_end": clamped_end,
        **result,
    }