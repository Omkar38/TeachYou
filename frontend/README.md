# GenAI Explainer Frontend (Next.js 14)

## Run

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open http://localhost:5173

## Login

- By default the UI expects an API token stored in a cookie (`genai_token`).
- Go to `/login`, paste the token you set for the backend (`API_AUTH_TOKEN`), and save.

If you want to bypass UI login while iterating locally:

```bash
# in frontend/.env
NEXT_PUBLIC_AUTH_DISABLED=1
```
