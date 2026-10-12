"""Sentence-selection baseline. No paraphrasing or implicit date resolution."""
import re


def extract_claims(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text.strip()) if s.strip()][:30]


def query_variants(claim, domains=()):
    queries = [claim, claim + " fact check"]
    safe = [d.strip() for d in domains if re.fullmatch(r"[a-zA-Z0-9.-]+", d.strip())]
    if safe:
        queries.append(claim + " (" + " OR ".join("site:" + d for d in safe[:3]) + ")")
    return queries
