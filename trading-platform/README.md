# Trading Platform — Kubernetes Deployment

Kubernetes deployment infrastructure for the trading platform microservices running on GKE (customer1 namespace).

## Directory Structure

```
trading-platform/
├── dockerfiles/           # Multi-stage Dockerfiles for each service
│   ├── dashboard/         # Next.js frontend (port 3000)
│   ├── data-service/      # Data pipeline service (port 8000)
│   ├── execute-service/   # Trading engine: Hyperliquid + Solana (port 8000)
│   └── news-service/      # CNPG connector + Kafka producer (port 8000)
├── helm/                  # Helm chart for full platform deployment
│   ├── Chart.yaml         # Chart metadata
│   ├── values.yaml        # Default values (images, replicas, resources, infra)
│   ├── .sops.yaml         # SOPS configuration for secret encryption
│   ├── trading-secrets.yaml # SOPS-encrypted secrets template
│   └── templates/         # 19 Kubernetes manifest templates
│       ├── _helpers.tpl           # Template helpers
│       ├── namespace.yaml         # Namespace resource
│       ├── configmap.yaml         # Shared ConfigMap
│       ├── secrets.yaml           # Secrets (SOPS-encrypted via trading-secrets.yaml)
│       ├── ingress.yaml           # GCE Ingress for all services
│       ├── NOTES.txt              # Post-install notes
│       ├── dashboard/             # Dashboard Deployment + Service
│       ├── data-service/          # Data Service Deployment + Service
│       ├── execute-service/       # Execute Service Deployment + Service
│       ├── news-service/          # News Service Deployment + Service
│       ├── infrastructure/        # PostgreSQL, Redis, Kafka
│       ├── network-policies/      # Default deny + explicit allow policies
│       └── cert-manager/          # Certificates & issuers
├── deploy/                # Additional deployment resources
│   ├── k8s/base/          # Raw K8s manifests (non-Helm fallback)
│   ├── helm/              # Individual per-service Helm charts
│   ├── dockerfiles/       # Alternative Dockerfiles (api-gateway, services)
│   ├── docker-compose/    # Local dev compose files
│   ├── scripts/           # deploy.sh, generate-mtls-certs.sh
│   └── mtls/              # mTLS documentation
└── .github/workflows/     # CI/CD pipelines
    ├── build-test.yml     # Build + unit tests on PR
    ├── build-push.yml     # Build + push to GAR on merge
    └── deploy.yml         # Helm deploy to GKE on push to master
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Dashboard | 3000 | Next.js trading dashboard |
| Data Service | 8000 | Data pipeline, Postgres + Redis + Kafka consumers |
| Execute Service | 8000 | Trading engine with Hyperliquid + Solana integration |
| News Service | 8000 | CryptoPanic/GNews connector, Kafka producer |

## Infrastructure Components

- **PostgreSQL 17** — Primary database for trades, orders, user data
- **Redis 7** — Caching layer with 3-node cluster
- **Kafka 3.9** (KRaft mode) — Event streaming (trades, orders, news topics)
- **GCE Ingress** — External traffic routing with TLS termination
- **Cert-Manager** — Automatic TLS certificates (Let's Encrypt + internal CA)
- **Network Policies** — Default deny ingress/egress with explicit allow rules

## Deploying

### Prerequisites

- GKE cluster: `customer1-gke` (us-central1)
- Helm 3 installed locally or in CI
- SOPS configured with Age key (`trading-secrets.yaml` must be encrypted)
- Access to `us-central1-docker.pkg.dev/customer1-gke/trading` registry

### Quick Deploy

```bash
# 1. Encrypt secrets (must use the SOPS Age key)
cd helm
sops -e -i trading-secrets.yaml

# 2. Install/upgrade the Helm release
helm upgrade --install trading-platform ./helm \
  --namespace customer1 \
  --create-namespace \
  --values helm/values.yaml \
  --set global.environment=production
```

### CI/CD

- **PR opened** → `build-test.yml` runs unit tests
- **Merged to master** → `build-push.yml` builds images and pushes to GAR
- **Push to master** → `deploy.yml` runs `helm upgrade` on GKE

## Secrets

Secrets are managed via [SOPS](https://github.com/getsops/sops) with Age encryption.
The `.sops.yaml` file configures which keys to use for each path.

```bash
# Encrypt the secrets file
sops -e -i helm/trading-secrets.yaml

# Decrypt (for debugging)
sops -d helm/trading-secrets.yaml
```

**Never commit unencrypted secrets to git.**

## Namespace

The platform deploys into the `customer1` namespace on the GKE cluster.
Update `global.namespace` in `helm/values.yaml` or override via `--set` during install.
