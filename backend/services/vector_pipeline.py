from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import fitz  # PyMuPDF

# load model once
model = SentenceTransformer("all-MiniLM-L6-v2")

QUERY = "tree planting reforestation afforestation forest restoration mangrove agroforestry"


def extract_text(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text


def chunk_text(text, size=500):
    return [text[i:i+size] for i in range(0, len(text), size)]


def analyze_pdf(pdf_path):
    text = extract_text(pdf_path)
    chunks = chunk_text(text)

    chunk_embeddings = model.encode(chunks)
    query_embedding = model.encode([QUERY])[0]

    scores = cosine_similarity([query_embedding], chunk_embeddings)[0]

    results = []

    for i, score in enumerate(scores):
        if score > 0.4:
            results.append({
                "text": chunks[i],
                "score": float(score)
            })

    results.sort(key=lambda x: x["score"], reverse=True)

    return results[:5]