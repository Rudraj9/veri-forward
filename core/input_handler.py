"""Prepare input for explicit user review; preparation never verifies a claim."""
from core.claim_extractor import extract_claims
from core.scraper import extract_article
from core.ocr import extract_image_text


def prepare_input(kind, content):
    if kind == "url":
        article = extract_article(content)
        text = article["text"]
        if not text:
            raise ValueError("No publisher text extracted. Paste article text or a direct publisher URL.")
    elif kind == "image":
        text = extract_image_text(content)
    elif kind == "text":
        text = content
    else:
        raise ValueError("Unknown input type")
    return {"extracted_text": text, "claim_candidates": extract_claims(text)}
