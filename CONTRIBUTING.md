# Contributing

- Setup: `./setup.sh --no-start`, then `./backend/run.sh api` and, in a second terminal, `./backend/run.sh worker`. App: http://localhost:8787
- Backend tests: `docker compose up -d db`, then `cd backend && .venv/bin/pip install -r requirements-dev.txt && .venv/bin/python -m pytest -q`. They create their own throwaway database (`careers_test`) and never touch yours.
- Web tests: `cd frontend && npx vitest run`, and with the app running `npx playwright test`.
- Adding a job system (ATS): write an adapter in `backend/app/crawler/discovery.py` returning `list[dict(title, location, url, description, posted_at)]` or `None`, register it in `ADAPTERS` and `ATS_PATTERNS`, and add a test with a fixture.
- Database changes: add an Alembic migration in `backend/migrations/versions/`.
- Keep crawling polite: honour robots.txt, keep the rate limits, never work around a block. Job-board search is optional, off by default and meant for personal use.
