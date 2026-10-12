# InvoiceIQ
![CI](https://github.com/narasimha4576/invoiceiq/actions/workflows/ci.yml/badge.svg)

**Live demo:** https://invoiceiq-b4hw9ocq9posxgujujmrga.streamlit.app/ (sample gallery and a playground for the safety net; no AI key is involved).

**Demo video (138 seconds):** <video controls src="../../Videos/Screen Recordings/demo-small.mp4" title="Title"></video>

AI-powered invoice extraction with a human-review safety net. Upload an invoice (PDF, PNG or JPG) and get structured JSON back, with a confidence score for every field and a clear flag when a person should double-check it. Invoices are processed in the background by a worker, so uploads never make the user wait.

![Review screen](docs/review-screen.png)

## What it does
- Reads invoices with a vision-capable AI model (Google Gemini) and returns clean JSON
- Returns `null` for anything missing or cut off, instead of guessing
- Checks the AI's answer with plain code (maths, GSTIN, tax rate, date, missing fields)
- Combines those checks with the AI's confidence scores to set `needs_review`
- Processes uploads as background jobs (Redis and Celery), with retries when the AI service is busy
- Lets a person correct flagged fields in a review screen, and stores both the AI's answer and the corrected version in PostgreSQL

## Architecture
```mermaid
flowchart LR
    U[Review screen - Streamlit] -->|upload invoice| A[FastAPI]
    A -->|create job| D[(PostgreSQL)]
    A -->|send task| R[(Redis queue)]
    R --> W[Celery worker]
    W -->|PDF or image| G[Gemini API]
    G -->|JSON and confidence| W
    W -->|checked result| D
    U -->|poll job status| A
```

How one invoice flows:
```mermaid
sequenceDiagram
    participant U as Review screen
    participant A as API
    participant R as Redis
    participant W as Worker
    participant G as Gemini
    participant D as PostgreSQL
    U->>A: POST /jobs (invoice file)
    A->>D: create job (queued)
    A->>R: send task
    A-->>U: 202 and job id
    W->>R: take task
    W->>G: read invoice
    G-->>W: JSON and confidence
    W->>D: store checked result (done)
    U->>A: GET /jobs/{id} every 2 seconds
    A-->>U: status, then the result
```

## Why the AI is not trusted blindly
The AI can misread an invoice or invent values for parts it cannot see. So every answer is checked:

| Check | What it catches |
|---|---|
| Line maths | quantity x unit price does not equal the line amount |
| Subtotal and total | line amounts do not add up to the subtotal, or subtotal + tax does not equal the total |
| GSTIN format | the GST number is not 15 characters in the right shape |
| Tax rate | the tax is not a standard GST percentage of the subtotal |
| Date | the date is incomplete, invalid or in the future |
| Missing fields | a required value is empty |
| AI confidence | the model itself says it is unsure (below 0.8) |

Rules and confidence catch different mistakes. A rule catches a half-visible date like `2023-1`, while low confidence catches a cut-off invoice number that looks valid.

## Measured accuracy
I measured the system on **66 generated invoices** in 7 conditions. Each invoice is drawn from known data, so the correct answer for every field is known exactly.

**Result: 526 of 528 field checks correct (99.6%).**

| Condition | Invoices | What makes it hard | Field checks correct |
|---|---|---|---|
| Clean PDF | 12 | baseline | 96/96 |
| Clean PNG | 8 | baseline | 64/64 |
| Degraded JPG | 8 | tilted, blurred, low resolution, compressed | 64/64 |
| Cut-off page | 8 | totals missing, so the right answer is "nothing" | 64/64 |
| Phone photo | 12 | dark table, tilt, keystone effect, shadow, noise, blur | 94/96 |
| Smudged page | 8 | amounts and totals covered, so the right answer is "nothing" | 64/64 |
| Second layout | 10 | different layout, HSN column, Indian digit grouping (`1,23,456.00`) | 80/80 |

The review safety net matters as much as accuracy:

| Question | Result |
|---|---|
| Incomplete invoices (cut-off or smudged) flagged for review | 16/16 |
| Invoices with a wrong field flagged for review | 2/2 |
| Correct invoices flagged by mistake | 0/48 |
| Values invented where the page shows nothing | 0/48 |
| Wrong answers that were **not** flagged (silent errors) | 0 |

**The two misses** were GSTINs on phone photos where the model read a digit `0` for a letter (`D` or `O`). The GSTIN format check caught both and sent them to human review.

**An experiment I rejected.** I added the GSTIN pattern to the prompt. Accuracy did not change, but one misread became a valid-looking wrong code (`D` read as `O`) that no check could catch. Silent errors went from 0 to 1, so I reverted it. Accuracy alone would have hidden that.

**How it was measured:** a generator creates the invoices and their answer sheets, a runner sends them through the same code the API uses, and a scorer compares each field. Text matches ignoring capitals and extra spaces, numbers match within 0.01, and line items are scored cell by cell. The full report is in [`benchmark/results/report.md`](benchmark/results/report.md).

**Limits:** the invoices are generated, with two layouts, and the PDFs are pictures of invoices. Real invoices (handwriting, stamps, multiple pages, other languages) are not measured yet, so real-world accuracy is likely lower. The numbers are for one model, set in `app/config.py`, measured in October 2026.

To reproduce:
```bash
python benchmark/generate.py
python -m benchmark.generate_hard
python -m benchmark.run        # about 66 AI calls
python -m benchmark.score
```

## Reliability
- **Retries:** a busy or rate-limited AI service is retried up to 3 times with growing waits. Permanent errors (such as a wrong API key) fail immediately.
- **No lost jobs:** tasks wait in Redis, so a job uploaded while the worker is down is processed when it returns.
- **Health checks:** `/health/ready` checks the database and Redis, and Docker uses it to mark the API healthy or unhealthy.
- **Tests:** 138 automated tests run with a fake AI, so they need no API key and no internet. They run automatically on every push with GitHub Actions.
- **Smoke test:** `smoke_test.py` checks a running system from end to end.

![Running containers](docs/compose-ps.png)

## API
| Endpoint | Purpose |
|---|---|
| `GET /health` | Is the service running? |
| `GET /health/ready` | Are the database and Redis reachable? |
| `POST /jobs` | Upload an invoice, get a job id (202) |
| `GET /jobs/{id}` | Job status, and the reviewed result when done |
| `GET /jobs` | Recent jobs (optional `status` and `limit`) |
| `POST /extract` | Upload and wait for the result in one call |
| `POST /invoices` | Save an original and a corrected invoice |
| `GET /invoices` | List saved invoices |

## Run with Docker (recommended)
You need your own free Google AI key (from Google AI Studio). It stays on your computer in the `.env` file and is never uploaded anywhere.
```bash
cp .env.example .env
# edit .env: add your Gemini API key and choose a database password
docker compose up --build
```
The API is at http://localhost:8000/docs. Start the review screen in a second terminal:
```bash
pip install -r requirements-ui.txt
streamlit run ui/review_app.py
```
## Published image
Every push to `main` that passes the tests is built and published by GitHub Actions to GitHub Container Registry:
```bash
docker pull ghcr.io/narasimha4576/invoiceiq:latest
```
Tags: `latest` (newest main), `sha-<commit>` (a specific commit) and `v<version>` (releases).

## Run without Docker
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```
This uses a local SQLite file and runs jobs inside the API, so Redis and the worker are not needed.

## Configuration
| Variable | Used by | Meaning |
|---|---|---|
| `GEMINI_API_KEY` | API, worker | Your Google AI key |
| `POSTGRES_PASSWORD` | database, compose | Local database password |
| `DATABASE_URL` | API, worker | Set by compose. Defaults to a local SQLite file |
| `REDIS_URL` | API, worker | Set by compose |
| `JOB_RUNNER` | API | `celery` (separate worker) or `background` (default) |
| `UPLOAD_DIR` | API, worker | Where uploads wait until processed |
| `API_URL` | review screen | Address of the API |

## Tests
```bash
pip install -r requirements-dev.txt
pytest
python smoke_test.py   # needs the system running; uses the real AI
```

## Project structure
```
app/        API, AI extraction, validators, review logic, jobs, worker, storage
ui/         Streamlit review screen
tests/      Unit and API tests
samples/    Fake invoices for testing
benchmark/  Generated test invoices, answer sheets, runner and scorer
docs/       Screenshots
```

## Status and roadmap
Measured, tested and published (see above). Next:
- Public deployment with a live demo link
- Real-world invoice samples in the benchmark

All sample invoices are fake.