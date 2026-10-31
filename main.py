# Entrypoint for Vercel (and `uvicorn main:app` locally).
from backend.app.main import app  # noqa: F401
