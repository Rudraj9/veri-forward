"""NLI premise=evidence, hypothesis=claim; context checks are incomplete heuristics."""
import re
import threading
from functools import lru_cache
from utils.config import settings


_load_lock = threading.Lock()


@lru_cache(maxsize=1)
def _load_nli():
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    tokenizer = AutoTokenizer.from_pretrained(settings.nli_model)
    model = AutoModelForSequenceClassification.from_pretrained(settings.nli_model).to("cpu").eval()
    expected = {0: "contradiction", 1: "entailment", 2: "neutral"}
    if model.config.num_labels != 3 or {int(k): v.lower() for k, v in model.config.id2label.items()} != expected:
        raise ValueError("Unexpected NLI label mapping; refusing assessment")
    return tokenizer, model


def get_nli():
    with _load_lock:
        return _load_nli()


def context_checks(claim, passage):
    warnings = []
    lower = passage.casefold()
    numbers = re.findall(r"\b\d+(?:[.,]\d+)*(?:%|\b)", claim)
    passage_numbers = set(re.findall(r"\b\d+(?:[.,]\d+)*(?:%|\b)", passage))
    if any(n not in passage_numbers for n in numbers):
        warnings.append("Claim date or quantity is absent or differs in the passage")
    months = re.findall(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\b", claim, re.I)
    if any(m.casefold() not in lower for m in months):
        warnings.append("Claim month is absent or differs in the passage")
    entities = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b|\b[A-Z]{2,}\b", claim)
    ignored = {"the", "a", "an", "this", "there", "on", "in", "at", "it"}
    if any(e.casefold() not in lower for e in entities if e.casefold() not in ignored):
        warnings.append("A named entity or location is missing from the passage")
    return warnings


def assess(claim, evidence):
    import torch
    tokenizer, model = get_nli()
    if len(tokenizer.encode(claim, add_special_tokens=False)) > 180:
        raise ValueError("Reviewed claim exceeds safe NLI token budget")
    for item in evidence:
        item.context_warnings = context_checks(claim, item.excerpt)
        inputs = tokenizer(item.excerpt, claim, return_tensors="pt")
        if inputs["input_ids"].shape[1] > 512:
            item.context_warnings.append("Passage/claim exceeds NLI input budget")
            continue
        with torch.inference_mode():
            scores = torch.softmax(model(**inputs).logits, dim=-1)[0].tolist()
        # Official model card mapping: 0 contradiction, 1 entailment, 2 neutral.
        item.contradiction, item.support, item.neutral = scores
        item.eligible = item.relevance >= settings.relevance_threshold and not item.context_warnings
    return evidence
