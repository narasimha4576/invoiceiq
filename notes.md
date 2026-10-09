## Interview stories

1. Problem: small businesses type invoice data by hand. I built a tool that reads an invoice, returns structured data, and asks a human to check only the doubtful ones.
2. Surprise: on a cut-off invoice the AI calculated tax and total values that were not visible. A stricter prompt reduced it, but the real fix was checking the AI with plain code.
3. Decision: I use both rules and the AI's confidence. Rules caught the incomplete date; low confidence caught a cut-off invoice number that looked valid.
4. Things that broke: Google retired the model I used (I moved the name to one config line), the service was overloaded at times (I added retries), and tests failed without an API key (I made the AI client load only when needed).
5. Next: a job queue, PostgreSQL, an accuracy benchmark, automated CI and a public deployment.

## Week 3 notes

- Moved from SQLite to PostgreSQL with SQLAlchemy. The same code runs on SQLite in tests and Postgres in Docker.
- Slow AI work moved out of the API into a Celery worker with a Redis queue. Uploads answer instantly with a job id and the screen polls for the result.
- Retries: a busy AI service is retried with growing waits, but a wrong API key fails right away, because retrying a permanent error only wastes time.
- A job uploaded while the worker was stopped was processed after the worker restarted, because tasks wait in the queue.
- Health checks: /health only says the program is alive, /health/ready checks the database and Redis.
- Tests use a fake AI and temporary databases, so they need no key and no internet (about 60 tests).
- invoiceiq-app image size: 373MB