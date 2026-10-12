"""Explicit optional CPU model download/warm-up."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.similarity import get_model
from core.evidence_checker import get_nli

if __name__ == "__main__":
    get_model()
    get_nli()
    print("Both CPU models loaded and cached successfully.")
