# Evaluation protocol (no measured results yet)

`claims.example.jsonl` demonstrates the format using synthetic claims. It is not
an evaluation dataset. Collect English single-claim examples, including negation,
changed dates/places/numbers, unsupported rumours and conflicting reports. Two
people should independently label each claim against saved reliable evidence;
record disagreements and resolve them before testing. Labels describe evidence
available at the annotation time, not an eternal truth value.

Fields: unique `id`, `split` (`dev` or `test`), literal `claim`, one of the four
`label` values, `rationale`, `reference_urls`, separate `event_date`, `annotated_at`.
Keep related events, paraphrases and syndicated articles in one split to reduce
leakage. Use development data for thresholds; freeze the rules before opening
the test set. Do not tune on the synthetic format examples.

Save snapshots explicitly with `python run.py "claim" --snapshot path.json` or
the UI download button. The output contains article text, passages, original
links, publisher links, query provenance, publication/retrieval dates, scores and
failures. Alongside it save dependency versions (`pip freeze`), model commit IDs,
configuration values, annotation records and warm/cold timings. Snapshots can
contain personal data: anonymize claims and do not commit private material.

Compare these systems on the same split and saved evidence:

1. **Future TF-IDF classifier baseline:** fit TF-IDF/logistic regression on
   training data only. Map labels explicitly. This experiment is deferred and
   must never override the app's retrieved evidence.
2. **Retrieval + similarity only:** report passage relevance and retrieval
   quality. Similarity does not provide a valid factual verdict. A safe factual
   comparator always abstains; any experimental threshold classifier must be
   clearly labelled an unsafe baseline, separate from the app.
3. **Retrieval + NLI + context checks:** current pipeline and frozen rules.
   Replay snapshots through the model/rules instead of fetching new evidence
   when comparing assessment methods. A snapshot replay runner is future work.

Predictions JSONL fields: `id`, `system`, `verdict`, `latency_seconds`,
`snapshot_path`. Measure latency with `time.perf_counter()` around the full
pipeline and document whether model loading is included. Keep all abstentions
and system failures, tagging failures separately; never discard hard examples.

Run `python evaluation/score.py claims.jsonl predictions.jsonl --split test`.
It calculates per-verdict precision/recall, false confirmations, abstention
rate, mean/median latency and missing-prediction counts. Undefined precision or
recall is `null`, not invented zero accuracy. Compare identical claim IDs; report
coverage and class counts alongside metrics. No performance figures have been
measured for this project.
