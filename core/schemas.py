"""The same validated contracts are used by the CLI, UI and API."""
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field, model_validator, field_validator
from urllib.parse import urlsplit


def now():
    return datetime.now(timezone.utc).isoformat()


class VerifyRequest(BaseModel):
    input_type: Literal["text", "url"] = "text"
    content: str = Field(min_length=1, max_length=20000)
    reviewed_claim: str = Field(min_length=1, max_length=1500)

    @model_validator(mode="after")
    def nonblank(self):
        if not self.content.strip() or not self.reviewed_claim.strip():
            raise ValueError("Input and reviewed claim must not be blank")
        return self


class PrepareResponse(BaseModel):
    extracted_text: str
    claim_candidates: list[str]


class Article(BaseModel):
    title: str = ""
    link: str
    source: str = "Unknown source"
    source_url: str | None = None
    publisher_url: str | None = None
    published: str | None = None
    publisher_published: str | None = None
    retrieved_at: str = Field(default_factory=now)
    extraction_status: str = "not_attempted"
    text: str = ""
    provenance: list[str] = Field(default_factory=list)
    duplicate_urls: list[str] = Field(default_factory=list)
    independence_group: str = ""

    @field_validator("link", "publisher_url", "source_url")
    @classmethod
    def safe_link(cls, value):
        if value is not None:
            p = urlsplit(value)
            if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password:
                raise ValueError("Source links must be HTTP/HTTPS without credentials")
        return value


class Evidence(BaseModel):
    excerpt: str
    article: Article
    relevance: float
    support: float = 0
    contradiction: float = 0
    neutral: float = 1
    context_warnings: list[str] = Field(default_factory=list)
    eligible: bool = False


class VerifyResponse(BaseModel):
    status: Literal["completed", "limited", "system_error"] = "completed"
    original_input: str
    reviewed_claim: str
    verdict: Literal["supported", "contradicted", "mixed_or_misleading", "insufficient_evidence"]
    explanation: str
    evidence_strength: Literal["limited", "moderate", "strong"]
    supporting_evidence: list[Evidence] = Field(default_factory=list)
    contradicting_evidence: list[Evidence] = Field(default_factory=list)
    assessed_evidence: list[Evidence] = Field(default_factory=list)
    related_articles: list[Article] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    verification_timestamp: str = Field(default_factory=now)
    whatsapp_reply: str
