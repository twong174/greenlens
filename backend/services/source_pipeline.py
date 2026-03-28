# services/source_pipeline.py

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from geopy.geocoders import Nominatim
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
geolocator = Nominatim(user_agent="greenlens")


BAD_LOCATIONS = {
    "global",
    "multi-country",
    "worldwide",
    "around the world",
    "multiple countries",
    "various countries",
}


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except Exception:
        return None


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    fenced = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except Exception:
            pass

    generic = re.search(r"(\{.*\})", text, flags=re.DOTALL)
    if generic:
        try:
            return json.loads(generic.group(1))
        except Exception:
            pass

    return {}


def geocode_location(location: str | None) -> Tuple[Optional[float], Optional[float]]:
    if not location:
        return None, None

    cleaned = location.strip().lower()
    if cleaned in BAD_LOCATIONS:
        return None, None

    try:
        loc = geolocator.geocode(location)
        if not loc:
            return None, None
        return loc.latitude, loc.longitude
    except Exception:
        return None, None


def search_candidate_sources(company: str) -> List[Dict[str, str]]:
    """
    Find candidate sustainability / reforestation sources.
    """
    prompt = f"""
Find up to 8 high-quality sources about reforestation, afforestation, restoration,
forest regeneration, mangrove restoration, or tree-planting claims for the company "{company}".

Prioritize:
1. official sustainability report PDFs
2. official ESG / sustainability webpages
3. official project pages
4. reputable articles only if official sources are limited

Return ONLY valid JSON in this exact format:
{{
  "sources": [
    {{
      "title": "string",
      "url": "string",
      "source_type": "official_pdf | official_webpage | article"
    }}
  ]
}}
"""

    response = client.responses.create(
        model="gpt-4o-mini",
        tools=[{"type": "web_search_preview"}],
        input=prompt,
    )

    parsed = _extract_json(getattr(response, "output_text", "") or "")
    sources = parsed.get("sources", [])

    cleaned = []
    for source in sources:
        url = source.get("url")
        if not url:
            continue
        cleaned.append({
            "title": source.get("title", "Untitled"),
            "url": url,
            "source_type": source.get("source_type", "article"),
        })

    return cleaned[:8]


def build_fit_profile(company: str, source: Dict[str, str]) -> Dict[str, Any]:
    """
    Ask OpenAI to inspect one source and fill the score buckets.
    """
    prompt = f"""
You are evaluating whether a source is the best fit for verifying a corporate reforestation claim.

Company: {company}
Source title: {source.get("title", "")}
Source URL: {source.get("url", "")}
Source type: {source.get("source_type", "article")}

Determine whether this source contains:
- a direct reforestation/restoration/tree-planting claim
- a usable location
- usable years
- claimed hectares if stated
- a short supporting quote

Bucket rules:
- mentions_reforestation = true if the source clearly discusses reforestation, restoration,
  afforestation, forest regeneration, or mangrove restoration
- mentions_tree_planting = true if the source clearly discusses planting trees or saplings
- location_precision:
  - exact = named site, reserve, municipality, project site, or clearly mappable place
  - regional = state, province, region
  - broad = country only
  - none = no usable location
- is_vague = true if the wording is generic like "supports restoration" or "partnered with"
  without a concrete measurable project
- claimed_hectares should be numeric only if explicitly supported
- year_start and year_end only if explicitly supported
- source_quote should be short and relevant

Return ONLY valid JSON:
{{
  "mentions_reforestation": true,
  "mentions_tree_planting": false,
  "location_text": "Pará, Brazil",
  "location_precision": "regional",
  "year_start": 2019,
  "year_end": 2023,
  "claimed_hectares": 400000,
  "project_description": "forest restoration initiative",
  "source_quote": "short quote here",
  "is_vague": false
}}
"""

    response = client.responses.create(
        model="gpt-4o-mini",
        tools=[{"type": "web_search_preview"}],
        input=prompt,
    )

    parsed = _extract_json(getattr(response, "output_text", "") or "")

    return {
        "title": source.get("title"),
        "url": source.get("url"),
        "source_type": source.get("source_type"),
        "mentions_reforestation": bool(parsed.get("mentions_reforestation", False)),
        "mentions_tree_planting": bool(parsed.get("mentions_tree_planting", False)),
        "location_text": parsed.get("location_text"),
        "location_precision": parsed.get("location_precision", "none"),
        "year_start": _safe_int(parsed.get("year_start")),
        "year_end": _safe_int(parsed.get("year_end")),
        "claimed_hectares": _safe_float(parsed.get("claimed_hectares")),
        "project_description": parsed.get("project_description"),
        "source_quote": parsed.get("source_quote"),
        "is_vague": bool(parsed.get("is_vague", False)),
    }


def score_source(profile: Dict[str, Any]) -> Dict[str, Any]:
    bucket_score = 0
    weighted_score = 0.0
    reasons: List[str] = []

    source_type = profile.get("source_type")
    if source_type == "official_pdf":
        weighted_score += 3.0
        reasons.append("Official PDF")
    elif source_type == "official_webpage":
        weighted_score += 2.0
        reasons.append("Official company webpage")
    elif source_type == "article":
        weighted_score += 1.0
        reasons.append("Third-party article")

    if profile.get("mentions_reforestation"):
        bucket_score += 1
        weighted_score += 3.0
        reasons.append("Direct reforestation/restoration mention")

    if profile.get("mentions_tree_planting"):
        bucket_score += 1
        weighted_score += 2.0
        reasons.append("Direct tree-planting mention")

    if profile.get("location_text"):
        bucket_score += 1
        reasons.append(f"Location found: {profile['location_text']}")

    loc_precision = profile.get("location_precision")
    if loc_precision == "exact":
        bucket_score += 1
        weighted_score += 4.0
        reasons.append("Exact location")
    elif loc_precision == "regional":
        bucket_score += 1
        weighted_score += 3.0
        reasons.append("Regional location")
    elif loc_precision == "broad":
        weighted_score += 1.0
        reasons.append("Broad country-level location")
    else:
        weighted_score -= 2.0
        reasons.append("Penalty: no usable location")

    if profile.get("year_start") is not None:
        bucket_score += 1
        weighted_score += 2.0
        reasons.append(f"Start year: {profile['year_start']}")

    if profile.get("year_end") is not None:
        bucket_score += 1
        weighted_score += 1.0
        reasons.append(f"End year: {profile['year_end']}")

    if profile.get("claimed_hectares") is not None:
        bucket_score += 1
        weighted_score += 2.0
        reasons.append(f"Claimed hectares: {profile['claimed_hectares']}")

    if profile.get("source_quote"):
        bucket_score += 1
        weighted_score += 1.5
        reasons.append("Supporting quote found")

    year_start = profile.get("year_start")
    if year_start is not None:
        project_age = 2026 - year_start
        if project_age >= 3:
            weighted_score += 2.0
            reasons.append("Good before/after time window")
        elif project_age >= 1:
            weighted_score += 0.5
            reasons.append("Limited time window")

    if profile.get("is_vague"):
        weighted_score -= 3.0
        reasons.append("Penalty: vague wording")

    profile["bucket_score"] = bucket_score
    profile["weighted_score"] = round(weighted_score, 2)
    profile["reasons"] = reasons
    return profile


def select_best_source(company: str) -> Dict[str, Any]:
    candidates = search_candidate_sources(company)

    ranked_sources = []
    for candidate in candidates:
        profile = build_fit_profile(company, candidate)
        ranked_sources.append(score_source(profile))

    ranked_sources.sort(
        key=lambda x: (x["weighted_score"], x["bucket_score"]),
        reverse=True
    )

    selected = ranked_sources[0] if ranked_sources else None

    return {
        "company": company,
        "ranked_sources": ranked_sources,
        "selected_source": selected,
    }


def parse_best_source_to_json(company: str, selected_source: Dict[str, Any]) -> Dict[str, Any]:
    """
    Since the fit profile already extracted the main fields,
    we mostly normalize and geocode them here.
    """
    location = selected_source.get("location_text")
    lat, lng = geocode_location(location)

    return {
        "company": company,
        "location": location,
        "claimed_hectares": selected_source.get("claimed_hectares"),
        "year_start": selected_source.get("year_start"),
        "year_end": selected_source.get("year_end"),
        "lat": lat,
        "lng": lng,
        "source_title": selected_source.get("title"),
        "source_url": selected_source.get("url"),
        "source_type": selected_source.get("source_type"),
        "project_description": selected_source.get("project_description"),
        "source_quote": selected_source.get("source_quote"),
        "bucket_score": selected_source.get("bucket_score"),
        "weighted_score": selected_source.get("weighted_score"),
        "location_precision": selected_source.get("location_precision"),
        "ready_for_map": lat is not None and lng is not None,
        "ready_for_verification": (
            lat is not None
            and lng is not None
            and selected_source.get("claimed_hectares") is not None
            and selected_source.get("year_start") is not None
            and selected_source.get("year_end") is not None
        ),
    }


def analyze_company(company: str) -> Dict[str, Any]:
    ranked = select_best_source(company)
    selected = ranked.get("selected_source")

    if not selected:
        return {
            "company": company,
            "location": None,
            "claimed_hectares": None,
            "year_start": None,
            "year_end": None,
            "lat": None,
            "lng": None,
            "source_title": None,
            "source_url": None,
            "source_type": None,
            "project_description": None,
            "source_quote": None,
            "bucket_score": 0,
            "weighted_score": 0,
            "location_precision": "none",
            "ready_for_map": False,
            "ready_for_verification": False,
            "ranked_sources": [],
        }

    parsed = parse_best_source_to_json(company, selected)
    parsed["ranked_sources"] = ranked.get("ranked_sources", [])
    return parsed