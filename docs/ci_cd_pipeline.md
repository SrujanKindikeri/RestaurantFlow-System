# CI/CD Pipeline

RestaurantFlow uses two GitHub Actions workflows: `ci.yml` for validation on every push and pull request, and `deploy.yml` for image building and server deployment.

---

## CI Pipeline (`.github/workflows/ci.yml`)

### Triggers

- `push` to `main` or `develop`
- `pull_request` targeting `main` or `develop`

### Stage diagram

```
backend-lint
     │
backend-tests ◄── postgres:15 service
     │         ◄── redis:7 service
     │
frontend-lint
     │
frontend-build
     │
docker-build  (push events only, not PRs)
     │
security-scan (non-blocking, push only)
```

### Stages

#### `backend-lint`
- Sets up Python 3.11 with pip cache.
- Installs `backend/requirements.txt`.
- Runs `flake8` if available (non-blocking — skips gracefully if not installed).
- Runs `python manage.py check` with `DEBUG=True` and a CI-safe test database.

#### `backend-tests`
- Spins up `postgres:15` and `redis:7` as GitHub Actions service containers.
- Runs `python manage.py migrate --noinput` then `python manage.py test --verbosity=2`.
- Uses isolated credentials (`DB_NAME=test_rf`, `SECRET_KEY=ci-test-key`).
- Pipeline fails if any test fails.
- Uses pip cache keyed on `backend/requirements.txt` hash.

#### `frontend-lint`
- Sets up Node 20 with npm cache (keyed on `frontend/package-lock.json`).
- Runs `npm ci` (uses lockfile exactly, no updates).
- Runs `npm run lint` — fails pipeline on any lint error.

#### `frontend-build`
- Runs `npm ci` + `npm run build` with placeholder production API URLs.
- Confirms the TypeScript compilation and Vite bundling succeed.

#### `docker-build`
- Uses `docker/setup-buildx-action@v3` for BuildKit.
- Builds both backend and frontend images to verify Dockerfiles are correct.
- Does **not** push images (push=false). Push happens in the CD workflow only.
- Runs only on push events, not pull requests.

#### `security-scan`
- Runs `pip-audit` against `backend/requirements.txt`.
- `continue-on-error: true` — a vulnerability warning does not fail the pipeline.
- Issues are surfaced as `::warning::` annotations in the Actions UI.

### Secrets used by CI

None. CI uses only ephemeral test credentials defined directly in the workflow YAML. No production secrets touch the CI pipeline.

---

## CD Pipeline (`.github/workflows/deploy.yml`)

### Triggers

- `push` to `main` → automatically deploys to **staging**.
- `workflow_dispatch` with `environment` input → manual deploy to `development`, `staging`, or `production`.
- `image_tag` input (optional) → deploy a specific previous tag for rollback.

### Stage diagram

```
prepare
  │
  ├── Determines environment (staging for push, manual choice for dispatch)
  └── Determines image tag (input or current SHA)
  │
build-and-push
  │
  ├── Logs in to GHCR with GHCR_TOKEN
  ├── Builds and pushes backend image → ghcr.io/<owner>/restaurantflow-backend:<sha>
  └── Builds and pushes frontend image → ghcr.io/<owner>/restaurantflow-frontend:<sha>
  │
deploy
  │
  ├── Targets GitHub environment: development / staging / production
  ├── Production environment requires manual approval (configure in repo settings)
  └── SSHs to server, runs deployment/scripts/deploy.sh <tag>
```

### GitHub environments

Create these environments in **Settings → Environments**:

| Environment | Protection rule |
|-------------|-----------------|
| `development` | None (auto-deploy) |
| `staging` | None (auto-deploy on main push) |
| `production` | Required reviewers (at least 1 approver) |

### Required secrets and variables

**Repository secrets** (Settings → Secrets → Actions):

| Secret | Description |
|--------|-------------|
| `GHCR_TOKEN` | GitHub personal access token with `write:packages` scope |
| `SSH_PRIVATE_KEY` | Private key for SSH access to the deployment server |
| `SSH_HOST` | Deployment server IP or hostname |
| `SSH_USER` | SSH username on the server |

**Repository variables** (Settings → Variables → Actions):

| Variable | Example |
|----------|---------|
| `VITE_API_URL` | `https://app.example.com/api` |
| `VITE_WS_URL` | `wss://app.example.com` |

### Image tagging strategy

| Tag | When updated |
|-----|-------------|
| `<git-sha>` | Every CD run |
| `latest` | Pushes to `main` only |

Always reference images by SHA tag in production. The `latest` tag is for convenience only.

---

## Adding a new environment

1. Create the environment in GitHub Settings.
2. Add environment-specific secrets if credentials differ per environment.
3. Add a `workflow_dispatch` input option or a new branch trigger in `deploy.yml`.

---

## Preventing accidental production deployments

- Feature branches never trigger the CD workflow.
- `main` push only deploys to `staging`.
- Production deployment requires `workflow_dispatch` + manual approval from a configured reviewer.
- Never push directly to `main` without a reviewed pull request.
