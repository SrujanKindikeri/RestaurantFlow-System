# Production Deployment Guide

This document walks through deploying RestaurantFlow to a production server for the first time and updating it on subsequent releases.

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Docker | 24+ |
| Docker Compose (plugin) | v2.20+ (`docker compose`, not `docker-compose`) |
| SSH access to the server | With a non-root deploy user |
| A domain name | With DNS A records pointing at the server |
| TLS certificates | Let's Encrypt via Certbot (see `deployment/nginx/ssl/README.md`) |

---

## First-time setup

### 1. Clone the repository

```bash
git clone https://github.com/your-org/restaurantflow.git ~/restaurantflow
cd ~/restaurantflow
```

### 2. Create the production env file

```bash
cp deployment/environment/.env.prod.example deployment/environment/.env.prod
nano deployment/environment/.env.prod   # or your preferred editor
```

Fill in every placeholder value.  To generate a secure `SECRET_KEY`:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

> **Never commit `.env.prod` to version control.**

### 3. Place TLS certificates

Follow `deployment/nginx/ssl/README.md` to obtain and place:

```
deployment/nginx/ssl/fullchain.pem
deployment/nginx/ssl/privkey.pem
```

### 4. Build images

```bash
bash deployment/scripts/build.sh
```

Or, if pulling from GHCR after a CD pipeline run, skip the build step and go to step 6.

### 5. Validate environment

```bash
source deployment/environment/.env.prod
bash deployment/scripts/validate-environment.sh
```

### 6. Back up the database (skip on first deploy — there is nothing to back up)

```bash
bash deployment/scripts/backup-before-deploy.sh
```

### 7. Run the deployment

```bash
bash deployment/scripts/deploy.sh <image-tag>
```

`deploy.sh` will:
1. Validate the environment
2. Back up the database
3. Pull images
4. Run `python manage.py migrate --noinput`
5. Restart all services
6. Poll `/health/ready/` for up to 120 s

### 8. Verify health

```bash
bash deployment/scripts/health-check.sh
# Or manually:
curl -f https://yourdomain.com/health/ready/
```

---

## Subsequent deployments

```bash
bash deployment/scripts/deploy.sh <new-image-tag>
```

The script handles everything: backup → migrate → restart → verify.

---

## Running migrations standalone

If you need to run migrations without a full deploy:

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  run --rm backend python manage.py migrate --noinput
```

---

## Scaling Celery workers

You can run additional worker processes to handle higher task volume:

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  up -d --scale celery_worker=3
```

> **Never scale `celery_beat`.** Only one instance of the beat scheduler may run at a time.  Running multiple instances causes duplicate task execution.

---

## Accessing logs

```bash
# All services
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# Backend only
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f backend

# Nginx access and error logs
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f nginx
```

---

## Updating SSL certificates

After Certbot renews the certificates, restart Nginx to pick them up:

```bash
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem deployment/nginx/ssl/
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem   deployment/nginx/ssl/
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart nginx
```

---

## Rolling back

See [`deployment_rollback.md`](deployment_rollback.md).
