"""CLI text verification: python run.py 'one English claim'."""
import argparse
from core.pipeline import verify
from core.schemas import VerifyRequest

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VeriForward text verification")
    parser.add_argument("claim")
    parser.add_argument("--snapshot", help="Explicit opt-in path for saving evidence JSON")
    args = parser.parse_args()
    result = verify(VerifyRequest(content=args.claim, reviewed_claim=args.claim))
    output = result.model_dump_json(indent=2)
    print(output)
    if args.snapshot:
        from pathlib import Path
        Path(args.snapshot).write_text(output, encoding="utf-8")
