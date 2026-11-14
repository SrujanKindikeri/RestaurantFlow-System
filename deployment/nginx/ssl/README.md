# SSL Certificates

This directory is mounted into the Nginx container at `/etc/nginx/ssl/`. Place your TLS certificate files here.

> **Never commit real certificate files or private keys to version control.**

## Expected files

| File | Description |
|------|-------------|
| `fullchain.pem` | Full certificate chain (certificate + intermediates) |
| `privkey.pem`   | Private key |

---

## Obtaining certificates with Certbot / Let's Encrypt

Install Certbot on the host:

```bash
sudo apt install certbot
```

Obtain a certificate (standalone mode — stop Nginx first):

```bash
sudo systemctl stop nginx   # or: docker compose stop nginx
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com
sudo systemctl start nginx  # or: docker compose start nginx
```

Certbot stores files under `/etc/letsencrypt/live/yourdomain.com/`.  
Copy or symlink them into this directory:

```bash
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem deployment/nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem   deployment/nginx/ssl/
sudo chmod 600 deployment/nginx/ssl/privkey.pem
```

## Automatic renewal

Certbot's systemd timer renews certificates automatically. After renewal, restart Nginx:

```bash
certbot renew
docker compose restart nginx
```

To automate the restart, add a deploy hook:

```bash
# /etc/letsencrypt/renewal-hooks/deploy/restart-nginx.sh
#!/bin/bash
cd /home/deploy/restaurantflow
docker compose restart nginx
```

## Self-signed certificate (development / testing only)

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout deployment/nginx/ssl/privkey.pem \
  -out    deployment/nginx/ssl/fullchain.pem \
  -subj "/CN=localhost"
```

This generates an untrusted certificate that browsers will warn about. For local testing, add a browser exception or use `curl -k`.
