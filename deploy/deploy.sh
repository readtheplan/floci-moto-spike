# floci API — deployment manifest
# Drop on a $6/mo Digital Ocean droplet (1 vCPU / 1 GB RAM / 25 GB SSD)
#
# Prerequisites:
#   - Ubuntu 24.04 LTS droplet
#   - Cloudflare DNS A record → droplet IP (proxied/orange cloud)
#   - DO_TOKEN set for doctl (optional — speeds up provisioning)
#
# ─────────────────────────────────────────────────────────────────────────

# ── System dependencies ─────────────────────────────────────────────────

sudo apt update && sudo apt install -y python3.11 python3.11-venv nginx git

# ── Clone & install ─────────────────────────────────────────────────────

sudo mkdir -p /opt/floci-api
sudo chown $USER:$USER /opt/floci-api
git clone https://github.com/readtheplan/floci-moto-spike.git /opt/floci-api

python3.11 -m venv /opt/floci-api/.venv
/opt/floci-api/.venv/bin/pip install --upgrade pip
/opt/floci-api/.venv/bin/pip install -e /opt/floci-api
/opt/floci-api/.venv/bin/pip install -r /opt/floci-api/requirements-api.txt

# ── Smoke test ──────────────────────────────────────────────────────────

/opt/floci-api/.venv/bin/python -m pytest /opt/floci-api/tests/ -q
curl -s http://127.0.0.1:8080/health || echo "API not started yet (expected)"

# ── systemd unit ────────────────────────────────────────────────────────

sudo tee /etc/systemd/system/floci-api.service << 'UNIT'
[Unit]
Description=floci API — AWS resource simulator
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/floci-api
ExecStart=/opt/floci-api/.venv/bin/uvicorn server:app --host 127.0.0.1 --port 8080
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now floci-api
sudo systemctl status floci-api

# ── nginx reverse proxy ─────────────────────────────────────────────────

sudo tee /etc/nginx/sites-available/floci-api << 'NGINX'
server {
    listen 80;
    server_name floci.readtheplan.dev;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
    }

    # Rate limit: 10 req/s per IP (Moto is in-process, single-threaded)
    limit_req zone=floci burst=5 nodelay;
    limit_req_status 429;
}
NGINX

# Rate limit zone
sudo mkdir -p /etc/nginx/conf.d
echo 'limit_req_zone $binary_remote_addr zone=floci:10m rate=10r/s;' \
  | sudo tee /etc/nginx/conf.d/floci-rate-limit.conf

sudo ln -sf /etc/nginx/sites-available/floci-api /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# ── Verify ──────────────────────────────────────────────────────────────

curl -s http://127.0.0.1:8080/health | python3 -m json.tool
curl -s http://127.0.0.1:8080/scenarios | python3 -m json.tool
curl -s -X POST 'http://127.0.0.1:8080/create?scenario=mixed' | python3 -m json.tool | head -5

echo ""
echo "=== Deployment complete ==="
echo "Health:  http://127.0.0.1:8080/health"
echo "API:     https://floci.readtheplan.dev (after Cloudflare DNS)"
echo "Logs:    sudo journalctl -u floci-api -f"
