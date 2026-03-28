from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import fitz
import re

model = SentenceTransformer("all-MiniLM-L6-v2")

QUERY = """
corporate claim about tree planting reforestation afforestation
forest restoration mangrove restoration hectares ha acres land area
location country region year target pledge commitment
protect forest reduce deforestation land restoration
"""

COUNTRIES = [
    "Brazil", "India", "Colombia", "Peru", "Indonesia", "Mexico",
    "Kenya", "Ecuador", "Bolivia", "Costa Rica", "Chile",
    "Argentina", "United States", "Canada", "China", "Australia"
]

REGION_HINTS = {
    "amazon rainforest": "Brazil",
    "tropical rainforest": "Brazil",
    "mangrove": "Colombia",
    "14 countries": "multi-country",
    "around the world": "global",
    "global": "global",
}

COMPANY_FALLBACKS = {
    "amazon": {
        "location": "multi-country"
    },
    "apple": {
        "location": "Colombia"
    },
    "microsoft": {
        "location": "Brazil"
    }
}


def extract_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def chunk_text(text: str, size: int = 1200, overlap: int = 200) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap
    return chunks


def find_relevant_chunks(chunks: list[str], threshold: float = 0.35, top_k: int = 10) -> list[dict]:
    if not chunks:
        return []

    chunk_embeddings = model.encode(chunks)
    query_embedding = model.encode([QUERY])[0]
    scores = cosine_similarity([query_embedding], chunk_embeddings)[0]

    results = []
    for i, score in enumerate(scores):
        if score >= threshold:
            results.append({
                "text": chunks[i],
                "score": float(score)
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def extract_location(text: str):
    lower = text.lower()

    for country in COUNTRIES:
        if country.lower() in lower:
            return country, "extracted"

    for hint, mapped_location in REGION_HINTS.items():
        if hint in lower:
            return mapped_location, "inferred"

    return None, "missing"


def extract_hectares(text: str):
    patterns = [
        r'(\d[\d,\.]*)\s*(million|billion|thousand)?\s*hectares',
        r'(\d[\d,\.]*)\s*(million|billion|thousand)?\s*ha\b',
        r'(\d[\d,\.]*)\s*(million|billion|thousand)?\s*acre'
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = float(match.group(1).replace(",", ""))
            scale = match.group(2)

            if scale:
                scale = scale.lower()
                if scale == "thousand":
                    value *= 1_000
                elif scale == "million":
                    value *= 1_000_000
                elif scale == "billion":
                    value *= 1_000_000_000

            if "acre" in match.group(0).lower():
                value *= 0.404686

            return round(value, 2), "extracted"

    return None, "missing"


def extract_years(text: str):
    years = re.findall(r'\b(20\d{2})\b', text)
    years = sorted(set(int(y) for y in years))

    if not years:
        return None, None, "missing"
    if len(years) == 1:
        return years[0], years[0], "extracted"

    return years[0], years[-1], "extracted"


def choose_best_chunk(chunks: list[dict]):
    if not chunks:
        return None

    best = None
    best_score = -1

    for chunk in chunks:
        text = chunk["text"]
        bonus = 0

        if re.search(r'\bhectares?\b|\bha\b|\bacres?\b', text, re.IGNORECASE):
            bonus += 0.20
        if re.search(r'\b(20\d{2})\b', text):
            bonus += 0.10
        loc, _ = extract_location(text)
        if loc:
            bonus += 0.10
        if re.search(r'reforest|restoration|afforestation|deforestation|forest', text, re.IGNORECASE):
            bonus += 0.10

        final_score = chunk["score"] + bonus

        if final_score > best_score:
            best_score = final_score
            best = chunk

    return best


def extract_from_all_chunks(relevant: list[dict], company_name: str):
    location = None
    location_source = "missing"

    claimed_hectares = None
    hectares_source = "missing"

    year_start = None
    year_end = None
    years_source = "missing"

    for chunk in relevant:
        text = chunk["text"]

        if location is None:
            loc, loc_source = extract_location(text)
            if loc:
                location = loc
                location_source = loc_source

        if claimed_hectares is None:
            hectares, h_source = extract_hectares(text)
            if hectares is not None:
                claimed_hectares = hectares
                hectares_source = h_source

        if year_start is None or year_end is None:
            ys, ye, y_source = extract_years(text)
            if ys is not None and ye is not None:
                year_start = ys
                year_end = ye
                years_source = y_source

    if location is None:
        fallback = COMPANY_FALLBACKS.get(company_name.lower(), {})
        if "location" in fallback:
            location = fallback["location"]
            location_source = "fallback"

    return {
        "location": location,
        "location_source": location_source,
        "claimed_hectares": claimed_hectares,
        "claimed_hectares_source": hectares_source,
        "year_start": year_start,
        "year_end": year_end,
        "years_source": years_source,
    }


def analyze_pdf(pdf_path: str, company_name: str) -> dict:
    text = extract_text(pdf_path)
    chunks = chunk_text(text)
    relevant = find_relevant_chunks(chunks)

    if not relevant:
        fallback = COMPANY_FALLBACKS.get(company_name.lower(), {})
        return {
            "company": company_name,
            "location": fallback.get("location"),
            "location_source": "fallback" if fallback.get("location") else "missing",
            "claimed_hectares": None,
            "claimed_hectares_source": "missing",
            "year_start": None,
            "year_end": None,
            "years_source": "missing",
            "best_match_text": None,
            "best_match_score": None,
            "matches": [],
            "ready_for_verification": False
        }

    best_chunk = choose_best_chunk(relevant)
    extracted = extract_from_all_chunks(relevant, company_name)

    ready_for_verification = (
        extracted["location"] is not None
        and extracted["claimed_hectares"] is not None
        and extracted["year_start"] is not None
        and extracted["year_end"] is not None
        and extracted["location"] not in ["global", "multi-country"]
    )

    return {
        "company": company_name,
        "location": extracted["location"],
        "location_source": extracted["location_source"],
        "claimed_hectares": extracted["claimed_hectares"],
        "claimed_hectares_source": extracted["claimed_hectares_source"],
        "year_start": extracted["year_start"],
        "year_end": extracted["year_end"],
        "years_source": extracted["years_source"],
        "best_match_text": best_chunk["text"] if best_chunk else None,
        "best_match_score": best_chunk["score"] if best_chunk else None,
        "matches": relevant,
        "ready_for_verification": ready_for_verification
    }