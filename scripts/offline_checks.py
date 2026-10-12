"""Dependency-free checks that can run before pip installation."""
import ast
import json
import socket
import sys
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.http_client import validate_url, fetch, _cache
from core.claim_extractor import extract_claims, query_variants
from core.evidence_checker import context_checks
from core.verdict import decide
from core.scraper import publisher_link, extract_article


class OfflineChecks(unittest.TestCase):
    def test_denial_conflict_and_source_count(self):
        def item(group, support, contradiction):
            return SimpleNamespace(article=SimpleNamespace(independence_group=group), support=support, contradiction=contradiction, neutral=0.02, eligible=True)
        denial = item("one.org", 0.02, 0.96)
        self.assertEqual(decide([denial, item("two.org", 0.02, 0.96)])[0], "contradicted")
        self.assertEqual(decide([denial, denial])[0], "insufficient_evidence")
        self.assertEqual(decide([denial, item("two.org", 0.96, 0.02)])[0], "mixed_or_misleading")
        self.assertEqual(decide([])[0], "insufficient_evidence")
        denial.eligible = False
        self.assertEqual(decide([denial])[0], "insufficient_evidence")

    def test_google_wrapper_abstains(self):
        with patch("core.scraper.fetch", return_value=(b"Google News", "https://news.google.com/a", "text/html")):
            result = extract_article("https://news.google.com/a")
        self.assertEqual(result["text"], "")
        self.assertEqual(result["extraction_status"], "google_news_unresolved")
        html = b'<a href="https://publisher.example/story">Read</a>'
        self.assertEqual(publisher_link(html, "https://news.google.com/a", "https://publisher.example"), "https://publisher.example/story")

    def test_evaluation_scorer(self):
        from evaluation.score import score
        rows = [{"id": "one", "split": "test", "label": "contradicted"}]
        predictions = [{"id": "one", "system": "synthetic-test", "verdict": "supported", "latency_seconds": 1}]
        result = score(rows, predictions, "test")["synthetic-test"]
        self.assertEqual(result["false_confirmations"], 1)
        self.assertEqual(result["per_verdict"]["supported"]["precision"], 0)

    def test_syntax(self):
        root = Path(__file__).resolve().parents[1]
        for directory in ("core", "backend", "app", "utils", "tests", "scripts", "evaluation"):
            for path in (root / directory).rglob("*.py"):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def test_claim_preservation(self):
        claim = "RBI did not raise the rate to 6% in Delhi in 2025."
        self.assertEqual(extract_claims(claim), [claim])
        self.assertTrue(all(q.startswith(claim) for q in query_variants(claim)))

    def test_context_changes(self):
        fixture = json.loads((Path(__file__).resolve().parents[1] / "tests/fixtures/evidence.json").read_text())
        self.assertEqual(context_checks(fixture["claim"], fixture["support"]), [])
        for key in ("changed_date", "changed_location", "changed_quantity"):
            self.assertTrue(context_checks(fixture["claim"], fixture[key]))
        self.assertTrue(context_checks("Rate is 6%", "Rate is 16%"))

    def test_invalid_urls(self):
        for url in ("file:///etc/passwd", "ftp://example.com", "http://user:pass@example.com", "https://example.com:9000", "bad"):
            with self.assertRaises(ValueError):
                validate_url(url)

    def test_private_addresses(self):
        for ip in ("127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "fc00::1", "0.0.0.0", "224.0.0.1"):
            with patch("core.http_client.socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 80))]):
                with self.assertRaises(ValueError):
                    validate_url("http://example.com")

    def test_private_redirect(self):
        _cache.clear()
        response = MagicMock(status=302)
        response.getheader.return_value = "http://127.0.0.1/secret"
        connection = MagicMock()
        connection.getresponse.return_value = response
        def dns(host, *args, **kwargs):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1" if host == "127.0.0.1" else "8.8.8.8", 80))]
        with patch("core.http_client.socket.getaddrinfo", side_effect=dns), patch("core.http_client.socket.create_connection"), patch("core.http_client.http.client.HTTPConnection", return_value=connection):
            with self.assertRaises(ValueError):
                fetch("http://example.com")


if __name__ == "__main__":
    unittest.main(verbosity=2)
