from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from geopy.geocoders import Nominatim

app = FastAPI()

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


# Mock satellite data for demo companies — keyed by company name (lowercase)
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
    # Build a bounding box ~1 degree around the point
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
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json={"sql": sql, "geometry": geometry})
        resp.raise_for_status()
        return resp.json().get("data", [])


def compute_truth_score(loss_rows: list, year_start: int, claimed_hectares: float):
    if not loss_rows:
        return None

    midpoint = year_start + (loss_rows[-1]["umd_tree_cover_loss__year"] - year_start) // 2
    before = [r for r in loss_rows if r["umd_tree_cover_loss__year"] <= midpoint]
    after  = [r for r in loss_rows if r["umd_tree_cover_loss__year"] >  midpoint]

    avg_before = sum(r["loss_ha"] for r in before) / len(before) if before else 0
    avg_after  = sum(r["loss_ha"] for r in after)  / len(after)  if after  else 0

    reduction = avg_before - avg_after  # positive = deforestation slowed
    score = min(max(reduction / claimed_hectares * 100, 0), 100)

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
