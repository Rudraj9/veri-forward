"""Model-free checks of NLI input ordering and score interpretation."""
import sys
from unittest.mock import MagicMock, patch
import pytest
from core.schemas import Article, Evidence
from core.evidence_checker import assess


def test_premise_first_and_official_label_order():
    torch = MagicMock()
    torch.softmax.return_value.__getitem__.return_value.tolist.return_value = [0.95, 0.03, 0.02]
    tokenizer, model = MagicMock(), MagicMock()
    tokenizer.encode.return_value = [1, 2, 3]
    tensor = MagicMock()
    tensor.shape = (1, 30)
    tokenizer.return_value = {"input_ids": tensor}
    claim = "RBI raised the rate in Delhi."
    passage = "RBI did not raise the rate in Delhi."
    item = Evidence(article=Article(link="https://example.com"), excerpt=passage, relevance=0.95)
    with patch.dict(sys.modules, {"torch": torch}), patch("core.evidence_checker.get_nli", return_value=(tokenizer, model)):
        result = assess(claim, [item])[0]
    tokenizer.assert_called_once_with(passage, claim, return_tensors="pt")
    assert result.contradiction == 0.95
    assert result.support == 0.03
    assert result.eligible


def test_claim_is_never_silently_truncated():
    tokenizer = MagicMock()
    tokenizer.encode.return_value = list(range(181))
    with patch.dict(sys.modules, {"torch": MagicMock()}), patch("core.evidence_checker.get_nli", return_value=(tokenizer, MagicMock())):
        with pytest.raises(ValueError, match="token budget"):
            assess("long claim", [])
