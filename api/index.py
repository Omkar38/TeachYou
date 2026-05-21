# Vercel Python serverless entrypoint.
# Vercel's FastAPI detection looks for an `app` object in api/index.py (among other locations).
from apps.api.main import app  # noqa: F401  – re-exported for Vercel
