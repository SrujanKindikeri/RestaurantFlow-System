# RestaurantFlow — Deployment

Deployment configurations will be added in **Phase 15**.

## Planned Contents

```
deployment/
├── nginx/
│   └── nginx.conf           ← Reverse proxy configuration
├── docker/
│   ├── Dockerfile.backend   ← Production Django image
│   └── Dockerfile.frontend  ← Production React build
├── aws/
│   ├── ec2/                 ← EC2 / ECS task definitions
│   └── rds/                 ← RDS parameter groups
└── github-actions/
    └── deploy.yml           ← CI/CD pipeline
```

## Target Infrastructure (Phase 15)

```
CloudFront (CDN)
      │
   Route 53 (DNS)
      │
Application Load Balancer
      │
    Nginx
      │
  ┌───┴────┐
  │        │
Gunicorn  Daphne
(REST)   (WebSocket)
  │
Django
  │
  ├── RDS PostgreSQL
  └── ElastiCache Redis
```

## Development Infrastructure (Current)

Managed by `docker-compose.yml` at the project root:

```bash
docker compose up -d    # start PostgreSQL + Redis
docker compose down     # stop services
docker compose down -v  # stop + remove volumes
```
