"""Conservative MVP heuristics; tune on development data, not the test set."""
import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ImportError:  # optional: environment variables may be set externally
    def load_dotenv(*_args, **_kwargs):
        return False

# Load .env before Settings reads the environment, so documented variables such
# as OFFICIAL_DOMAINS or TESSERACT_CMD actually work from the file.
load_dotenv()


@dataclass(frozen=True)
class Settings:
    relevance_threshold: float = float(os.getenv("RELEVANCE_THRESHOLD", "0.40"))
    nli_threshold: float = float(os.getenv("NLI_THRESHOLD", "0.85"))
    nli_margin: float = 0.30
    max_articles: int = 8
    max_passages: int = 12
    official_domains: tuple = tuple(filter(None, os.getenv("OFFICIAL_DOMAINS", "").split(",")))
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    nli_model: str = "cross-encoder/nli-MiniLM2-L6-H768"


settings = Settings()
