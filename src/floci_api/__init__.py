"""floci API — HTTP wrapper around the Moto-based AWS simulator.

Package layout:
  cache.py      — in-memory TTL cache
  errors.py     — structured JSON error responses
  middleware.py  — CORS, security headers, rate limiting
  routes.py     — FastAPI route handlers
  app.py        — FastAPI app assembly
"""
