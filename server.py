"""floci API entry point for uvicorn.

Deploy:  uvicorn server:app --host 127.0.0.1 --port 8080
Proxy:   nginx → proxy_pass http://127.0.0.1:8080
TLS:     Cloudflare (orange cloud) → droplet IP, Free edge cert

This is the thin entry point. All logic lives in src/floci_api/.
"""

from floci_api.app import app  # noqa: F401
