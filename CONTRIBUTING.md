# Contributing

Thanks for your interest in contributing to GenAI Whiteboard Explainer MVP.

Quick guidelines to get started locally:

1. Recommended local run (Docker)

```bash
cd infra
docker compose up --build
# Frontend: http://localhost:5173
# API: http://localhost:8000
```

2. Local dev token

- Default token for local development: `dev-token`
- Set `DEV_TOKEN` in your local `.env` for API and worker

3. Environment

- Copy `.env.example` → `.env` and fill required keys (`OPENAI_API_KEY` is required for best quality)
- Keep `.env` private — do not commit secrets.

4. Coding style & checks

- This repo has a GitHub Actions workflow that builds the frontend and a lightweight Python syntax check.
- Before opening a PR, run the frontend build:

```bash
cd frontend
npm ci
npm run build
```

5. Pull requests

- Fork or branch from `main` and open a PR. Describe the change and any testing steps.
- Small, focused PRs are easier to review.

6. Tests

- There are no automated Python tests in the repo yet. If you add tests, ensure CI runs them or document how to run locally.

If you'd like, I can add a basic test scaffold and a more comprehensive Python CI later.
