# Repository Reorganization Plan

## Goal

Enforce the rule: **gcloud-lab = Kubernetes manifests only. No application code.**

Application code (source, Dockerfiles, CI/CD workflows, Helm charts, deployment scripts) belongs in `hermes-projects/`. gcloud-lab should contain only K8s manifests, Terraform infrastructure modules, cluster configs, and infra controller configs.

---

## Current State

### gcloud-lab/ — Full Directory Audit

```
gcloud-lab/
├── apps/
│   ├── base/
│   │   ├── customer1/          [KEEP] K8s manifests (deployments, services, configmaps, secrets)
│   │   ├── monitoring/         [KEEP] K8s manifests (dashboards)
│   │   └── osint-dashboard/    [KEEP] Helm chart (templates, values.yaml, Chart.yaml)
│   ├── staging/
│   │   ├── customer1/          [KEEP] K8s overlay (kustomization.yaml)
│   │   └── osint-dashboard/    [KEEP] K8s overlay (kustomization.yaml)
│   └── vwap-monitor/           [MOVE] App code (Dockerfile, app/, deploy/)
├── clusters/                   [KEEP] Cluster configs (devops-lab/*.yaml, flux-system/)
├── infrastructure/             [KEEP] Infra controllers, gatewayapi, gpus, tailnet
├── misc/                       [KEEP] Terraform snippets + K8s YAML
├── modules/                    [KEEP] Terraform modules (gke.tf, nodepool.tf, etc.)
├── scripts/                    [KEEP] Setup scripts
├── .github/workflows/
│   ├── osint-dashboard-infra.yml  [KEEP] Infra deployment workflow
│   └── trade-dashboard.yml        [MOVE] CI for trade-dashboard app → hermes-projects/
├── .devcontainer.json          [KEEP] Dev environment config
├── .sops.yaml                  [KEEP] SOPS encryption config
├── .terraform.lock.hcl         [KEEP] Terraform lock
├── .gitignore                  [KEEP] Git ignore rules
├── mise.toml                   [KEEP] Tool version management
├── README.md                   [KEEP] (will be updated)
├── infra-tailnet.yaml          [KEEP] Tailscale infra config
├── tailscale-0auth.yaml        [KEEP] Tailscale config
├── rays-new-deployment.yaml    [REVIEW] Orphan K8s deployment YAML — move to apps/base/
├── trade-dashboard/            [MOVE] Full FastAPI app → hermes-projects/trade-dashboard/
├── trading-platform/           [MOVE] Duplicate/deploy configs → hermes-projects/trading-platform/
├── trading-scripts/            [MOVE] Application code → hermes-projects/trading-scripts/
├── analyses/                   [REMOVE] Research artifacts (not code, not infra)
└── plans/                      [REMOVE] Planning docs (not code, not infra)
```

---

## Items to Move / Remove

### 1. `trade-dashboard/` → hermes-projects/trade-dashboard/

**What it is:** Full FastAPI application (not K8s manifests)
- `Dockerfile` — build config for the app
- `app/` — Python source code (main.py, models.py, schemas.py, database.py, requirements.txt, static/)
- `alembic/` — database migration scripts (env.py, versions/)
- `alembic.ini` — alembic config

**Also move:** `.github/workflows/trade-dashboard.yml` (CI workflow for this app)

**Already in gcloud-lab:** `apps/base/customer1/trade-dashboard/` — these are the K8s manifests for trade-dashboard (deployment.yaml, service.yaml, configmap.yaml, kustomization.yaml). **KEEP these** — they belong here.

### 2. `trading-platform/` → hermes-projects/trading-platform/

**What it is:** Duplicate/alternative deployment configs that overlap with hermes-projects/trading-platform/

Contents:
- `.github/workflows/` — 3 CI/CD workflows (build-push.yml, build-test.yml, deploy.yml)
- `README.md` — project readme
- `deploy/` — deployment configs:
  - `ci-cd/` — additional CI workflows
  - `docker-compose/` — docker-compose.dev.yml
  - `dockerfiles/` — Dockerfiles (api-gateway, dashboard, data-service, execute-service, news-service)
  - `helm/` — Helm charts (api-gateway, dashboard, data-service, execute-service, news-service)
  - `k8s/` — raw K8s manifests (deployments, services, hpa, cert-manager, ingress)
  - `mtls/` — mTLS README
  - `scripts/` — deploy.sh, generate-mtls-certs.sh
- `dockerfiles/` — Dockerfiles (dashboard, data-service, execute-service, news-service)
- `helm/` — Helm chart with templates (trading-platform chart, values.yaml, secrets)

**Already in gcloud-lab:** `apps/base/customer1/trading-platform/` — these are the K8s manifests. **KEEP these** — they belong here.

**Already in hermes-projects:** `hermes-projects/trading-platform/` — source code exists here (dashboard, data-service, execute-service, news-service, data_infrastructure). The gcloud-lab trading-platform/ deploy/dockerfiles/helm content should be MERGED into hermes-projects/trading-platform/.

**Decision needed:** The `trading-platform/` in gcloud-lab has BOTH deploy configs (dockerfiles, helm, k8s manifests) AND CI workflows. The K8s manifests in `deploy/k8s/base/` are similar but NOT identical to what's in `apps/base/customer1/trading-platform/`. Need to decide which is authoritative.

### 3. `trading-scripts/` → hermes-projects/trading-scripts/

**What it is:** Application code (Python trading scripts)
- `market_data.py` — market data script
- `orb-monitor/` — monitoring tool (monitor.py, config.yaml)
- `README.md`, `ROADMAP.md` — documentation

### 4. `apps/vwap-monitor/` → hermes-projects/vwap-monitor/

**What it is:** Application code with a Dockerfile
- `Dockerfile` — build config
- `app/` — source code (scanner.py, requirements.txt)
- `deploy/` — deployment config (deployment.yaml, kustomization.yaml, secret.yaml, config.env)

**Note:** The `deploy/` subdirectory contains K8s manifests. These should be moved BACK into gcloud-lab as `apps/base/customer1/vwap-monitor/`. The app code (Dockerfile + app/) goes to hermes-projects.

### 5. `analyses/` → REMOVE from gcloud-lab

**What it is:** Research/analysis markdown documents
- `telegram-webhook-container-analysis.md`
- `telegram-webhook-failure-analysis.md`

These are one-time research artifacts, not infrastructure config. Remove from gcloud-lab entirely.

### 6. `plans/` → REMOVE from gcloud-lab

**What it is:** Planning/strategy markdown documents
- `2026-04-25-openclaw-brain-v1.1.md`
- `AI_ARCHITECTURE.md`
- `models-to-try.md`

These are planning docs, not infrastructure config. Remove from gcloud-lab entirely.

### 7. `rays-new-deployment.yaml` → REVIEW

**What it is:** A standalone K8s deployment YAML at repo root.

**Action:** Move to `apps/base/customer1/hermes-agent/` (appears related to hermes-agent/rays deployment based on filename). Already similar files exist in that directory.

---

## Proposed Migration Plan (Ordered by PR)

### PR 1: This Plan (docs only)
- Add `MIGRATION_PLAN.md` (this file)
- Update `README.md` to document the new structure

### PR 2: Remove planning/research docs
- Delete `analyses/` directory
- Delete `plans/` directory
- Low risk, no dependencies

### PR 3: Move trade-dashboard app to hermes-projects
- Move `trade-dashboard/` → hermes-projects/trade-dashboard/
- Move `.github/workflows/trade-dashboard.yml` → hermes-projects/.github/workflows/
- K8s manifests in `apps/base/customer1/trade-dashboard/` stay in place
- Verify image references in K8s manifests still point to correct registry

### PR 4: Move trading-platform deploy configs to hermes-projects
- Move `trading-platform/` → merge with hermes-projects/trading-platform/
- CI workflows → hermes-projects/trading-platform/.github/workflows/
- Dockerfiles → hermes-projects/trading-platform/dockerfiles/
- Helm charts → hermes-projects/trading-platform/helm/
- K8s manifests from `trading-platform/deploy/k8s/` → reconcile with `apps/base/customer1/trading-platform/`
- **Decision needed:** Which K8s manifests are authoritative? The ones in gcloud-lab/apps/ or trading-platform/deploy/k8s/?

### PR 5: Move trading-scripts to hermes-projects
- Move `trading-scripts/` → hermes-projects/trading-scripts/
- Simple move, no K8s manifest reconciliation needed

### PR 6: Split vwap-monitor (app → hermes-projects, K8s → gcloud-lab)
- Move `apps/vwap-monitor/app/` + `apps/vwap-monitor/Dockerfile` → hermes-projects/vwap-monitor/
- Move `apps/vwap-monitor/deploy/` K8s manifests → `apps/base/customer1/vwap-monitor/`
- Update image references in K8s manifests

---

## Items That Stay in gcloud-lab (No Changes)

| Path | Reason |
|------|--------|
| `apps/base/customer1/` | K8s manifests (kustomize structure) |
| `apps/base/monitoring/` | K8s manifests (dashboards) |
| `apps/base/osint-dashboard/` | Helm chart for infra |
| `apps/staging/` | K8s overlays |
| `clusters/` | Cluster configs, flux-system |
| `infrastructure/` | Controllers, gatewayapi, gpus, tailnet |
| `misc/` | Terraform snippets + K8s YAML |
| `modules/` | Terraform modules |
| `scripts/` | Setup scripts |
| Root config files | .sops.yaml, .devcontainer.json, mise.toml, .gitignore, .terraform.lock.hcl |
| `infra-tailnet.yaml` | Tailscale infra config |
| `tailscale-0auth.yaml` | Tailscale config |

---

## K8s Manifest Reference Check

After moves, verify these image references still resolve:

| K8s Manifest | Image Reference |
|--------------|----------------|
| `apps/base/customer1/trade-dashboard/deployment.yaml` | Check image tag matches hermes-projects build |
| `apps/base/customer1/trading-platform/*/deployment.yaml` | Check image tags match hermes-projects build |
| `apps/base/customer1/hermes-agent/deployment.yaml` | N/A (already correct) |
| `apps/base/customer1/siriusdevops-site/deployment.yaml` | N/A (already correct) |

---

## Decisions Needed Before Proceeding

1. **trading-platform K8s manifest authority:** `trading-platform/deploy/k8s/base/` vs `apps/base/customer1/trading-platform/` — which is the source of truth?
2. **analyses/ and plans/:** Delete entirely, or archive somewhere else?
3. **rays-new-deployment.yaml:** Move to `apps/base/customer1/hermes-agent/` or delete?
