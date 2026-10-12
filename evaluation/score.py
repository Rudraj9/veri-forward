"""Score saved predictions, without retrieval or model downloads.

Predictions JSONL: id, system, verdict, latency_seconds, snapshot_path.
No metrics are claimed until real labelled data and predictions are supplied.
"""
import argparse
import json
from collections import defaultdict
from statistics import mean, median

LABELS = ("supported", "contradicted", "mixed_or_misleading", "insufficient_evidence")


def read_jsonl(path):
    with open(path, encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def score(claims, predictions, split):
    truth = {row["id"]: row["label"] for row in claims if row["split"] == split}
    if len({r["id"] for r in claims}) != len(claims):
        raise ValueError("Claim IDs must be unique across splits")
    if any(label not in LABELS for label in truth.values()):
        raise ValueError("Unknown ground-truth label")
    grouped = defaultdict(list)
    seen = set()
    for row in predictions:
        if row["id"] not in truth:
            continue
        if row["verdict"] not in LABELS or row["latency_seconds"] < 0:
            raise ValueError("Invalid prediction")
        key = (row["system"], row["id"])
        if key in seen:
            raise ValueError("Duplicate system/claim prediction")
        seen.add(key)
        grouped[row["system"]].append(row)
    results = {}
    for system, rows in grouped.items():
        metrics = {}
        for label in LABELS:
            tp = sum(truth[r["id"]] == label and r["verdict"] == label for r in rows)
            fp = sum(truth[r["id"]] != label and r["verdict"] == label for r in rows)
            fn = sum(truth[r["id"]] == label and r["verdict"] != label for r in rows)
            metrics[label] = {"precision": tp / (tp + fp) if tp + fp else None,
                              "recall": tp / (tp + fn) if tp + fn else None,
                              "tp": tp, "fp": fp, "fn": fn}
        confirmations = sum(r["verdict"] == "supported" for r in rows)
        false_confirmations = sum(r["verdict"] == "supported" and truth[r["id"]] != "supported" for r in rows)
        results[system] = {"evaluated": len(rows), "missing_predictions": len(truth) - len(rows),
            "per_verdict": metrics, "false_confirmations": false_confirmations,
            "false_confirmation_rate_among_confirmations": false_confirmations / confirmations if confirmations else None,
            "abstention_rate": sum(r["verdict"] == "insufficient_evidence" for r in rows) / len(rows),
            "mean_latency_seconds": mean(r["latency_seconds"] for r in rows),
            "median_latency_seconds": median(r["latency_seconds"] for r in rows)}
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("claims")
    parser.add_argument("predictions")
    parser.add_argument("--split", choices=["dev", "test"], default="test")
    args = parser.parse_args()
    print(json.dumps(score(read_jsonl(args.claims), read_jsonl(args.predictions), args.split), indent=2))
