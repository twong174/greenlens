from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
from geopy.geocoders import Nominatim
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
geolocator = Nominatim(user_agent="greenlens")

CURRENT_YEAR = datetime.now().year

BAD_LOCATIONS = {
    "global",
    "multi-country",
    "worldwide",
    "around the world",
    "multiple countries",
    "various countries",
    "international",
}


# -------------------------
# HELPERS
# -------------------------

def _safe_int(value: Any) -> Optional[int]:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except Exception:
        return None


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def _strip_code_fences(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_json(text: str) -> Dict[str, Any]:
    cleaned = _strip_code_fences(text)

    try:
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else {}
    except Exception:
        pass

    fenced = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        try:
            data = json.loads(fenced.group(1))
            return data if isinstance(data, dict) else {}
        except Exception:
            pass

    generic = re.search(r"(\{.*\})", cleaned, flags=re.DOTALL)
    if generic:
        try:
            data = json.loads(generic.group(1))
            return data if isinstance(data, dict) else {}
        except Exception:
            pass

    return {}


def _dedupe_sources(sources: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    cleaned: List[Dict[str, str]] = []

    for source in sources:
        url = (source.get("url") or "").strip()
        title = (source.get("title") or "Untitled").strip()
        source_type = (source.get("source_type") or "article").strip()

        if not url:
            continue

        normalized = url.split("#")[0].rstrip("/")
        if normalized in seen:
            continue

        seen.add(normalized)
        cleaned.append({
            "title": title,
            "url": normalized,
            "source_type": source_type,
        })

    return cleaned


def _company_aliases(company: str) -> List[str]:
    """
    Generate search aliases for a company. Includes manual aliases for known companies,
    but falls back to the company name itself for any company.
    """
    company = company.strip()
    aliases = {company}

    lowered = company.lower()

    # Manual aliases for companies with known alternative names
    manual_aliases = {
        "exxon mobil": ["Exxon Mobil", "ExxonMobil"],
        "exxonmobil": ["Exxon Mobil", "ExxonMobil"],
        "google": ["Google", "Alphabet"],
        "meta": ["Meta", "Facebook"],
        "facebook": ["Meta", "Facebook"],
        "dogbrew": ["DogBrew", "Dog Brew"],
        "microsoft": ["Microsoft"],
        "apple": ["Apple"],
        "amazon": ["Amazon", "AWS"],
    }

    if lowered in manual_aliases:
        aliases.update(manual_aliases[lowered])

    return list(aliases)


def _extract_primary_location(location: Optional[str]) -> Tuple[Optional[str], Optional[float], Optional[float]]:
    """
    Convert multi-location strings into the first geocodable primary location.

    Example:
    'Arkansas, Louisiana, and Texas, USA' -> tries 'Arkansas, USA' first, then 'Louisiana, USA', etc.
    Returns the first location that can be geocoded along with its coordinates.
    """
    if not location:
        return None, None, None

    normalized = location.strip()
    normalized = re.sub(r"\s+and\s+", ", ", normalized, flags=re.IGNORECASE)

    parts = [part.strip() for part in normalized.split(",") if part.strip()]
    if not parts:
        return None, None, None

    if len(parts) == 1:
        lat, lng = geocode_location(parts[0])
        return parts[0], lat, lng

    # If multiple parts, try combining each part (except the last) with the last part (country)
    country = parts[-1]
    
    for i in range(len(parts) - 1):
        location_candidate = f"{parts[i]}, {country}"
        lat, lng = geocode_location(location_candidate)
        if lat is not None and lng is not None:
            return location_candidate, lat, lng

    # Fallback: try just the country
    lat, lng = geocode_location(country)
    return country, lat, lng


# -------------------------
# GEO
# -------------------------

def geocode_location(location: str | None) -> Tuple[Optional[float], Optional[float]]:
    if not location:
        return None, None

    cleaned = location.strip().lower()
    if cleaned in BAD_LOCATIONS:
        return None, None

    try:
        loc = geolocator.geocode(location, timeout=10)
        if not loc:
            return None, None
        return loc.latitude, loc.longitude
    except Exception:
        return None, None


# -------------------------
# FETCH SOURCE TEXT
# -------------------------

async def fetch_source_text(url: str) -> str:
    try:
        async with httpx.AsyncClient(follow_redirects=True) as session:
            response = await session.get(
                url,
                timeout=25,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/122.0.0.0 Safari/537.36"
                    )
                },
            )
            response.raise_for_status()
            html = response.text

        html = re.sub(r"<script.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<noscript.*?</noscript>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<[^>]+>", " ", html)
        html = re.sub(r"\s+", " ", html).strip()

        return html[:50000]
    except Exception:
        return ""


# -------------------------
# SEARCH CANDIDATE SOURCES
# -------------------------

def _search_sources_for_alias(alias: str) -> List[Dict[str, str]]:
    prompt = f"""
Find up to 6 high-quality sources about reforestation, afforestation, restoration,
forest regeneration, mangrove restoration, tree-planting, nature restoration,
or forest carbon removal claims for the company "{alias}".

Prioritize:
1. official sustainability report PDFs
2. official ESG / sustainability webpages
3. official project pages
4. reputable articles only if official sources are limited

Look for projects that mention:
- a specific location
- a specific project or initiative
- a year or timeframe
- hectares, acres, trees planted, restoration area, or carbon removal project area

Return ONLY valid JSON:
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

    try:
        parsed = _extract_json(getattr(response, "output_text", "") or "")
        sources = parsed.get("sources", [])
        if not isinstance(sources, list):
            print(f"DEBUG: _search_sources_for_alias('{alias}') - sources not a list: {type(sources)}")
            return []

        cleaned: List[Dict[str, str]] = []
        for source in sources:
            if not isinstance(source, dict):
                continue

            url = source.get("url")
            if not url:
                continue

            cleaned.append({
                "title": source.get("title", "Untitled"),
                "url": str(url).strip(),
                "source_type": source.get("source_type", "article"),
            })

        print(f"DEBUG: _search_sources_for_alias('{alias}') - found {len(cleaned)} valid sources")
        return cleaned
    except Exception as e:
        print(f"DEBUG: _search_sources_for_alias('{alias}') - error: {e}")
        return []


def search_candidate_sources(company: str) -> List[Dict[str, str]]:
    all_sources: List[Dict[str, str]] = []

    for alias in _company_aliases(company):
        all_sources.extend(_search_sources_for_alias(alias))

    return _dedupe_sources(all_sources)[:12]


# -------------------------
# BUILD FIT PROFILE
# -------------------------

def build_fit_profile(company: str, source: Dict[str, str], source_text: str) -> Dict[str, Any]:
    prompt = f"""
You are evaluating whether a source is the best fit for verifying a corporate reforestation claim.

Company: {company}
Source title: {source.get("title", "")}
Source URL: {source.get("url", "")}
Source type: {source.get("source_type", "article")}

Use ONLY the source text below.

Determine whether this source contains:
- a direct reforestation/restoration/tree-planting/nature restoration/forest carbon removal claim
- a usable location
- usable years
- claimed hectares if stated
- a short supporting quote

Rules:
- mentions_reforestation = true if the source clearly discusses reforestation, restoration,
  afforestation, forest regeneration, mangrove restoration, forest protection with measurable restoration,
  or forest carbon removal tied to land restoration
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
- do not guess
- if missing, use null

Return ONLY valid JSON:
{{
  "mentions_reforestation": false,
  "mentions_tree_planting": false,
  "location_text": null,
  "location_precision": "none",
  "year_start": null,
  "year_end": null,
  "claimed_hectares": null,
  "project_description": null,
  "source_quote": null,
  "is_vague": false
}}

SOURCE TEXT:
{source_text}
"""

    response = client.responses.create(
        model="gpt-4o-mini",
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
        project_age = CURRENT_YEAR - year_start
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


async def select_best_source(company: str) -> Dict[str, Any]:
    candidates = search_candidate_sources(company)

    ranked_sources: List[Dict[str, Any]] = []

    async def process_candidate(candidate: Dict[str, str]) -> Dict[str, Any]:
        source_text = await fetch_source_text(candidate["url"])
        profile = build_fit_profile(company, candidate, source_text)
        return score_source(profile)

    if candidates:
        ranked_sources = await asyncio.gather(*[process_candidate(c) for c in candidates])

    ranked_sources.sort(
        key=lambda x: (x["weighted_score"], x["bucket_score"]),
        reverse=True,
    )

    selected = ranked_sources[0] if ranked_sources else None

    return {
        "company": company,
        "ranked_sources": ranked_sources,
        "selected_source": selected,
    }


# -------------------------
# NORMALIZE BEST SOURCE
# -------------------------

def parse_best_source_to_json(company: str, selected_source: Dict[str, Any]) -> Dict[str, Any]:
    raw_location = selected_source.get("location_text")
    primary_location, lat, lng = _extract_primary_location(raw_location)

    return {
        "company": company,
        "raw_location": raw_location,
        "location": primary_location,
        "coords": {
            "lat": lat,
            "lon": lng,
        },
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
        "selection_reasons": selected_source.get("reasons", []),
        "ready_for_map": lat is not None and lng is not None,
        "ready_for_verification": (
            lat is not None
            and lng is not None
            and selected_source.get("claimed_hectares") is not None
            and selected_source.get("year_start") is not None
            and selected_source.get("year_end") is not None
        ),
    }


# -------------------------
# MAIN PIPELINE
# -------------------------

async def analyze_company(company: str) -> Dict[str, Any]:
    ranked = await select_best_source(company)
    selected = ranked.get("selected_source")

    if not selected:
        return {
            "company": company,
            "selected_source": None,
            "ranked_sources": [],
            "raw_location": None,
            "location": None,
            "coords": {
                "lat": None,
                "lon": None,
            },
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
            "selection_reasons": [],
            "ready_for_map": False,
            "ready_for_verification": False,
        }

    parsed = parse_best_source_to_json(company, selected)
    parsed["selected_source"] = selected
    parsed["ranked_sources"] = ranked.get("ranked_sources", [])
    return parsed


async def run_pipeline(company: str) -> Dict[str, Any]:
    return await analyze_company(company)