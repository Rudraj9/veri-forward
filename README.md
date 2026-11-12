---
title: VeriForward
emoji: 🔎
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---

# VeriForward

An English MCA-project MVP for investigating WhatsApp forwards and Facebook
posts using retrieved evidence. No paid APIs or large generative model. It
returns `supported`, `contradicted`, `mixed_or_misleading` or
`insufficient_evidence`, with excerpts, links, limitations and a copyable reply.
Absence of evidence never means false. There are no measured accuracy claims.

## Windows setup

Use Python 3.11 (recommended for the ML dependencies), PowerShell and a normal
internet-connected terminal. From the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python scripts/download_models.py
.\.venv\Scripts\python -m streamlit run app/streamlit_app.py
```

Using the full executable path avoids PowerShell activation-policy issues.
The explicit download step is optional; the first full-text check otherwise
loads/downloads models lazily. Downloads need internet and sufficient disk/RAM;
models run locally on CPU and are cached by Hugging Face. Set `HF_HOME` to change
the model cache. Model-loading failure produces an explicit abstention, never a
similarity-based fallback. After caching, `HF_HUB_OFFLINE=1` can prevent model
network access (live evidence retrieval still requires internet).

Install Tesseract separately for screenshot input:

```powershell
winget install UB-Mannheim.TesseractOCR
```

The app auto-detects the standard Windows install location
(`C:\Program Files\Tesseract-OCR\tesseract.exe`), so no environment variable is
needed. Set `TESSERACT_CMD` — in the shell environment or in `.env`, which is now
loaded at startup — only for a non-standard location:

```powershell
$env:TESSERACT_CMD = 'D:\tools\Tesseract-OCR\tesseract.exe'
& $env:TESSERACT_CMD --version
```

If unavailable, OCR explains the problem and the user can paste the screenshot
text. Screenshot bytes are processed in memory, not saved. Streamlit keeps
current inputs in session memory; there is no database or persistent upload
store. OCR supports PNG/JPEG/WebP, at most 5 MB, 5000 pixels per dimension and
12 million pixels total. OCR runs with a 30-second timeout.

## Local commands and input review

```powershell
# Text CLI, with optional explicit snapshot export
.\.venv\Scripts\python run.py 'RBI did not increase the repo rate.'
.\.venv\Scripts\python run.py 'Your single claim here.' --snapshot evidence.json

# Backend in a separate terminal; docs at http://127.0.0.1:8000/docs
.\.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In Streamlit choose text, URL or screenshot, press **Prepare for review**, correct
the extracted text, select one sentence, and edit the single claim before
verification. The sentence splitter is a documented baseline, not a trained
claim extractor. It retains wording, names, negation, dates and quantities;
abbreviations and compound sentences need manual correction. No ambiguous date
or location is resolved automatically. URL extraction is also useful for reading
the claim; that article alone is not enough for a one-sided verdict.

## API

`GET /health` reports process health without downloading models. It does not
guarantee model readiness. OpenAPI documents shared Pydantic contracts.

`POST /prepare`: JSON `{ "input_type": "url", "content": "https://publisher/article" }`
(or `input_type: "text"`). Returns `extracted_text` and `claim_candidates`.

`POST /prepare/image`: raw image bytes with `Content-Type: image/png` (or JPEG/WebP),
**not multipart**. Returns the same preparation contract. Correct the extracted
text and choose a single claim. Upload example:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/prepare/image -ContentType image/png -InFile screenshot.png
```

`POST /verify` always requires the explicitly reviewed claim:

```powershell
$body = @{
  input_type = 'text'
  content = 'The original forward text.'
  reviewed_claim = 'The single claim selected and edited by the user.'
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/verify -ContentType application/json -Body $body
```

For URLs use `input_type: "url"` and the original URL as `content`. For an OCR
result use `input_type: "text"` and corrected extracted text as `content`.
The API cannot enforce human review; callers must implement that step.

The response includes original input, reviewed claim, verdict, explanation,
evidence strength, supporting/contradicting/assessed passages, related articles,
publication dates, retrieval dates, provenance, duplicate URLs, extraction
status, warnings, failures, UTC verification timestamp and WhatsApp reply.
`status` separates `completed`, `limited` and `system_error`: no results can be a
completed evidence-based abstention; failed model assessment is a system error
with an abstaining verdict. Invalid inputs use HTTP 422; oversized uploads use
413; unexpected uncaught application errors use 500. JSON bodies are capped at
100 KB before parsing, image bodies at 5 MB.

## How the pipeline works (viva guide)

1. `input_handler` prepares text and `claim_extractor` proposes literal sentences.
2. `news_search` retains the original Google News RSS search function and output
   fields. Requests now use bounded fetching. Two queries preserve the entire
   claim (original and `fact check` suffix); a third optional query restricts
   configured domains. Queries are provenance, not new claims.
3. `scraper` follows validated HTTP redirects and extracts publisher text with
   Trafilatura. A Google News page is never treated as publisher evidence. An
   unambiguous outgoing article link on the RSS-reported publisher host may be
   followed; otherwise `google_news_unresolved` is recorded. Many modern Google
   links may remain unresolved: this can make text-only checks abstain. Use a
   direct publisher URL when possible. No undocumented Google RPC decoder is
   assumed to work.
4. Deduplication merges identical URLs/titles and near-identical bodies, retaining
   query provenance and duplicate links. Registered domains from a bundled
   public-suffix list approximate publisher groups. Shared ownership and rewritten
   syndication are not reliably detectable, and this uncertainty is shown.
5. `similarity` keeps the existing title-ranking interface and adds overlapping
   token passages (up to 220 embedding tokens, 40-token overlap, first 4000 tokens
   per article). It ranks relevance with `all-MiniLM-L6-v2`; no vector database.
   Candidate extraction is capped at eight articles; only twelve passages are
   assessed. Later article context may be omitted, a deliberate MVP limit.
6. `evidence_checker` uses English CPU NLI, evidence as **premise**, claim as
   **hypothesis**. Scores are internal relation scores, never truth likelihoods.
   Missing names, month names or exact numeric tokens block that passage from a
   verdict. These incomplete heuristics can over-abstain and do not handle every
   location alias, relative date or spelled-out quantity. Joint NLI inputs over
   512 tokens and hypotheses over 180 NLI tokens are rejected without silently
   dropping the claim. Successful model loads are cached under locks.
7. `verdict` requires relevance >= 0.40, NLI relation score >= 0.85 and a margin
   >= 0.30 over both other labels. A one-sided verdict requires two distinct
   publisher groups. Strong conflicting passages produce `mixed_or_misleading`
   even without two-sided corroboration; its explanation says conflicting
   coverage, not proven partial deception. All other cases abstain. Several
   passages from one article count once. Source reputation has no voting weight.
   Strength is conservatively limited/moderate; strong is reserved until stronger
   independence/calibration work exists. Thresholds are unvalidated heuristics.
8. `pipeline` generates evidence-backed templates shared by CLI, Streamlit and
   FastAPI. The optional classifier placeholder is not called.

`published` is the RSS publication date. `publisher_published` is an explicitly
declared `article:published_time` metadata value if present; unknown dates stay
null. Neither is an event date and metadata can be wrong. Retrieval timestamps
record this check's collection time; HTTP responses may come from the five-minute
in-memory cache.

Configuration via environment variables (no secrets required):

```powershell
$env:OFFICIAL_DOMAINS = 'rbi.org.in,pib.gov.in'
$env:RELEVANCE_THRESHOLD = '0.40'
$env:NLI_THRESHOLD = '0.85'
```

Choose official domains relevant to the topic; being official does not itself
verify a claim. `.env` is ignored by Git and is not loaded automatically.

## Security and retrieval bounds

Only HTTP/HTTPS with standard ports and no credentials are allowed. Every
destination and redirect is DNS-checked; any non-public, multicast or reserved
address is blocked. Connections pin the validated IP, with original-host TLS
certificate checks/SNI to avoid DNS rebinding. Environment proxies are not used.
Requests have ten-second socket timeouts, a thirty-second body-read budget, at
most two attempts per hop, at most three redirects, a two-MB response cap,
half-second request spacing and a bounded 64-entry/five-minute memory cache.
DNS resolution still depends on OS resolver timeout. No full input/image logging.

## Checks and evaluation

```powershell
.\.venv\Scripts\python -m pytest -q
# Dependency-free security/context/rule smoke checks
python scripts/offline_checks.py
# Optional real network/model checks, excluded from normal tests
.\.venv\Scripts\python scripts/integration_check.py --retrieval
.\.venv\Scripts\python scripts/integration_check.py --models
.\.venv\Scripts\python scripts/integration_check.py --url 'https://a-real-public-publisher/article'
```

Normal pytest tests use synthetic saved fixtures and mocked retrieval/model
scores: denial versus similarity, no results, failed search/extraction, unavailable
models, duplicates, conflicting evidence, context changes, private/invalid URLs,
redirect blocking, extraction and API contracts. They do not download models.
Mock scores test rules, not model accuracy. See [evaluation/README.md](evaluation/README.md)
for separated development/test sets, labelled claim format, opt-in snapshots,
baseline comparisons and a scoring script. The TF-IDF baseline is future work;
similarity-only retrieval is not factual verification.

Implementation-environment checks: nine dependency-free checks passed and all
Python sources parsed/compiled. The full pytest suite could not run because
dependencies were missing; pip had `PIP_NO_INDEX=1`, and isolated pip failed through
the configured proxy. Live RSS, publisher extraction, model inference, OCR, UI/API
runtime and Docker build were not validated in this environment. Run the commands
above on an internet-connected development machine before relying on the app.

## Docker / Hugging Face Spaces (configuration only)

```powershell
docker build -t veriforward .
docker run --rm -p 7860:7860 veriforward
```

The image installs English Tesseract and serves Streamlit on `0.0.0.0:7860`, as
configured by this README's Docker Spaces front matter. It runs as UID 1000 with
a writable user-owned model cache, following the [official Docker Spaces
guide](https://huggingface.co/docs/hub/spaces-sdks-docker). Models download on
first full-text use; restarting an ephemeral Space may require downloads again.
The default container exposes the UI; to expose the API instead, override:

```powershell
docker run --rm -p 7860:7860 veriforward python -m uvicorn backend.main:app --host 0.0.0.0 --port 7860
```

UI and API are separate processes locally. A shared public port/proxy for both
is deferred. No deployment or publication was performed.

## Model documentation checked

On 2026-10-05, official documentation identified both models as Apache-2.0:
[embedding model](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
and [NLI model](https://huggingface.co/cross-encoder/nli-MiniLM2-L6-H768).
The NLI card documents premise/hypothesis ordering and label order; the
[model configuration](https://huggingface.co/cross-encoder/nli-MiniLM2-L6-H768/blob/main/config.json)
maps 0=contradiction, 1=entailment, 2=neutral. The loader validates that mapping
and refuses unexpected configurations. Record actual downloaded commit IDs for
reproducible experiments; dependencies are version-bounded, not a tested lockfile.

## Deferred features

Regional-language verification, learned confidence calibration, LIME/SHAP
classifier explanations, internet-wide reverse-image search, automatic image
origin/date verification, and the TF-IDF classifier experiment remain future
work. `imagehash` can compare against an existing reference-image collection;
it cannot independently discover an image's original context. The image input
currently checks OCR text only, not image authenticity or when/where it was taken.
