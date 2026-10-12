"""Transparent rules. Article groups, never passage counts, determine strength."""
from utils.config import settings


def decide(evidence):
    def strong(item, label):
        score = getattr(item, label)
        other = item.contradiction if label == "support" else item.support
        return item.eligible and score >= settings.nli_threshold and score - max(other, item.neutral) >= settings.nli_margin
    supports = [e for e in evidence if strong(e, "support")]
    contradicts = [e for e in evidence if strong(e, "contradiction")]
    def groups(items):
        return {e.article.independence_group for e in items if e.article.independence_group}
    if supports and contradicts:
        return "mixed_or_misleading", "moderate", supports, contradicts
    if len(groups(supports)) >= 2:
        return "supported", "moderate", supports, contradicts
    if len(groups(contradicts)) >= 2:
        return "contradicted", "moderate", supports, contradicts
    return "insufficient_evidence", "limited", supports, contradicts


def explain(verdict):
    return {
        "supported": "At least two publisher groups contain relevant passages that support the reviewed claim under the configured rules. This is provisional evidence, not proof.",
        "contradicted": "At least two publisher groups contain relevant passages that contradict the reviewed claim under the configured rules. Review the quoted context before sharing.",
        "mixed_or_misleading": "Strong supporting and contradicting passages conflict. This indicates conflicting coverage; the system has not established that the claim is partly misleading.",
        "insufficient_evidence": "The retrieved material does not meet the conservative verification rules. Missing or incomplete evidence does not mean the claim is false.",
    }[verdict]
