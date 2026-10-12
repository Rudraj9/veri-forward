from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app
from core.schemas import VerifyResponse

client = TestClient(app)


def test_health_and_schema():
    assert client.get("/health").status_code == 200
    with patch("core.pipeline.search_news", return_value=[]):
        response = client.post("/verify", json={"input_type": "text", "content": "A claim.", "reviewed_claim": "A claim."})
    assert response.status_code == 200
    assert VerifyResponse.model_validate(response.json()).verdict == "insufficient_evidence"
    assert "VerifyResponse" in client.get("/openapi.json").json()["components"]["schemas"]


def test_explicit_review_required():
    assert client.post("/verify", json={"content": "A claim."}).status_code == 422


def test_private_url_rejected():
    response = client.post("/verify", json={"input_type": "url", "content": "http://127.0.0.1", "reviewed_claim": "A claim."})
    assert response.status_code == 422


def test_upload_bounded():
    assert client.post("/prepare/image", content=b"x" * 5_000_001).status_code == 413
