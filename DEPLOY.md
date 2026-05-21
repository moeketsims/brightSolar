# Deploying Bright Solar Ops to a server

This walks through putting the app onto a VPS so your team can use it from anywhere
(not just your laptop). The app stays in Docker — nothing special needed on the host
besides Docker and a domain name.

## Prerequisites

- A Linux VPS (any provider — Hetzner, DigitalOcean, AWS Lightsail work fine; 2 vCPU /
  2 GB RAM is plenty for a team of <10)
- A domain you control (e.g. `ops.brightsolarpower.co.za`)
- DNS A-record pointing the domain at the VPS IP
- Docker + Docker Compose installed on the VPS

## One-time server setup

```bash
# On the VPS
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin ufw
sudo ufw allow OpenSSH && sudo ufw allow 80 && sudo ufw allow 443 && sudo ufw enable

# Clone the app
git clone https://github.com/YOUR/brightSolar.git
cd brightSolar

# Create the prod env file
cp .env.prod.example .env.prod
nano .env.prod   # fill in POSTGRES_PASSWORD, JWT_SECRET, PUBLIC_URL, CORS_ORIGINS

# Build & run
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Seed the first owner user (then delete the dev accounts via /settings)
docker compose exec backend python -m app.seed
```

## TLS (HTTPS)

You need a reverse proxy in front of the stack. The simplest option is **Caddy**
(auto-TLS out of the box). Install it on the VPS:

```bash
sudo apt install -y caddy
sudo nano /etc/caddy/Caddyfile
```

Paste (replacing the hostname):

```caddyfile
ops.brightsolarpower.co.za {
    # Frontend
    reverse_proxy /api/* localhost:8000
    reverse_proxy /auth/* localhost:8000
    reverse_proxy /projects/* localhost:8000
    reverse_proxy /invoices/* localhost:8000
    reverse_proxy /clients/* localhost:8000
    reverse_proxy /technicians/* localhost:8000
    reverse_proxy /vehicles/* localhost:8000
    reverse_proxy /templates/* localhost:8000
    reverse_proxy /expenses/* localhost:8000
    reverse_proxy /settings* localhost:8000
    reverse_proxy /activities/* localhost:8000
    reverse_proxy /today* localhost:8000
    reverse_proxy /trips* localhost:8000
    reverse_proxy /uploads/* localhost:8000
    reverse_proxy /health localhost:8000
    reverse_proxy /docs localhost:8000
    reverse_proxy /openapi.json localhost:8000
    reverse_proxy * localhost:3000
}
```

```bash
sudo systemctl reload caddy
```

Caddy automatically provisions a Let's Encrypt cert. Visit
`https://ops.brightsolarpower.co.za` and you're live.

## Backups

`docker-compose.prod.yml` includes a `backup` service that runs nightly `pg_dump` at
02:00 to `./backups/YYYY-MM-DD.sql.gz` and keeps the last 30 days.

**Restore from a backup:**

```bash
gunzip -c backups/2026-04-22.sql.gz | docker compose exec -T db psql -U brightsolar -d brightsolar
```

**Copy backups off the server** — set up a daily cron to `scp` or `rsync` the
`backups/` directory to a separate server or S3 bucket. Local backups alone don't
survive disk failure.

## Upgrading

```bash
git pull
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

No migrations framework yet — the app uses `Base.metadata.create_all` so new columns
need a DB wipe *or* a manual `ALTER TABLE`. When you introduce your first destructive
schema change, add Alembic.

## What's still on you

- Domain + DNS
- VPS + SSH hardening (`~/.ssh/authorized_keys` only, disable root, change SSH port)
- Off-server backup copy (scp/rsync/S3 — don't trust one disk)
- First owner user created: change the default password immediately
- `.env.prod` values: use long random strings for `POSTGRES_PASSWORD` and `JWT_SECRET`
