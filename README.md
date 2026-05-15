# GCloud-Lab DevOps Infrastructure

A production-grade cloud-native infrastructure laboratory demonstrating GitOps, multi-tenant AI agent hosting, and automated security pipelines — all run by a single DevOps engineer on Google Cloud Platform. Trusted by builders who ship.

## Table of Contents

- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [DevOps Tools & Technologies](#devops-tools--technologies)
- [Monitoring](#monitoring)
- [Project Structure](#project-structure)
- [Infrastructure Components](#infrastructure-components)
- [Applications](#applications)
- [Getting Started](#getting-started)
- [Security](#security)
- [Cost Optimization](#cost-optimization)
- [License](#license)

---

## Project Overview

This repository is the single source of truth for a multi-application cloud platform running on GKE. Every deployment, database, and network policy flows through Git via Flux CD. What lives here:

1. **AgentForge** — Private multi-tenant AI agent workspace with dual-tier vLLM inference (L4 dispatcher + A100 deep thinker) and isolated CNPG databases per tenant.
2. **Multi-Profile AI Agent Team** — Six specialist AI profiles (backend-dev, frontend-dev, researcher, outreach, quant, sec-ops) orchestrated through a shared Kanban board with automated audit-to-fix pipelines.
3. **Waitlist API** — FastAPI landing page backend with idempotent signups, async PostgreSQL, and Telegram fire-and-forget notifications.
4. **Autonomous News Quant Pipeline** — 371 global feed scraper with DeepSeek-R1 analysis generating actionable futures trading signals.
5. **N8N Workflow Automation** — Self-hosted workflow engine with dedicated CNPG PostgreSQL.
6. **Local Business Web Deployment Pipeline** — Automated K8s manifest generation for small business websites with cross-namespace HTTPRoute routing.

---

## Architecture

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                          Google Cloud Platform                                │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                     GKE Cluster (devops-lab-cluster)                    │  │
│  │                                                                        │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │  │
│  │  │ Standard     │  │ L4 GPU Pool  │  │ A100 GPU Pool│                 │  │
│  │  │ Node Pool    │  │ (SPOT L4)    │  │ (SPOT A100)  │                 │  │
│  │  │ e2-std-2     │  │ 1 node (24/7)│  │ 0-1 nodes    │                 │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                 │  │
│  │                                                                        │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │              Cilium CNI + Hubble + NetworkPolicy                 │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                        │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │         Kubernetes Gateway API — external-http-gateway           │ │  │
│  │  │         HTTPRoute PathPrefix → AgentForge / Waitlist / Apps      │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                        │  │
│  │  ┌───────────────────────────────┐  ┌───────────────────────────────┐ │  │
│  │  │     customer1 namespace       │  │    agent-forge namespace      │ │  │
│  │  │  - AgentForge (PAaaS)         │  │  - Tenant-specific OpenClaw   │ │  │
│  │  │  - Dual-tier vLLM             │  │  - Isolated CNPG databases    │ │  │
│  │  │     L4 Dispatcher (24/7)      │  │  - Qwen 3.6 27B Abliterated   │ │  │
│  │  │     A100 Deep Thinker (KEDA)  │  │  - KEDA scale-to-zero         │ │  │
│  │  │  - Waitlist API (FastAPI)     │  │                               │ │  │
│  │  │  - News Bot Pipeline          │  │  ┌───────────────────────────┐ │ │  │
│  │  │  - Landing Page               │  │  │   sec-ops audit agent     │ │  │
│  │  │  - CNPG PostgreSQL Cluster    │  │  │  Automated vuln scanning  │ │  │
│  │  └───────────────────────────────┘  │  │  → backend-dev auto-fix   │ │  │
│  │                                      │  └───────────────────────────┘ │ │  │
│  │  ┌───────────────────────────────┐  └───────────────────────────────┘ │  │
│  │  │   local-business namespaces   │                                     │  │
│  │  │  - nginx + ConfigMap per biz  │  ┌───────────────────────────────┐ │  │
│  │  │  - Cross-ns HTTPRoute refs    │  │      monitoring namespace     │ │  │
│  │  └───────────────────────────────┘  │  - Prometheus + Grafana       │ │  │
│  │                                      │  - Tailscale-only access      │ │  │
│  │  ┌───────────────────────────────┐  │  - No public ingress           │ │  │
│  │  │       kanban namespace        │  └───────────────────────────────┘ │  │
│  │  │  - Hermes Agent Orchestrator  │                                     │  │
│  │  │  - 6 Specialist Profiles      │  ┌───────────────────────────────┐ │  │
│  │  │  - Isolated hermes-pgdb       │  │        n8n namespace           │ │  │
│  │  └───────────────────────────────┘  │  - Workflow automation         │ │  │
│  │                                      │  - Dedicated PostgreSQL        │ │  │
│  │                                      └───────────────────────────────┘ │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## DevOps Tools & Technologies

### Infrastructure as Code (IaC)

| Tool | Version | Purpose |
|------|---------|---------|
| **Terraform** | 1.7+ | Infrastructure provisioning for GCP resources |
| **Google Provider** | 7.14.1 | Terraform provider for GCP |
| **Helm Provider** | Latest | Terraform provider for Helm charts |
| **Flux Provider** | 1.7.6 | Terraform provider for Flux bootstrap |

### Container Orchestration & Networking

| Tool | Version | Purpose |
|------|---------|---------|
| **Google Kubernetes Engine (GKE)** | Latest | Managed Kubernetes cluster |
| **Cilium** | 1.18.5 | CNI plugin with eBPF-based networking |
| **Hubble** | 1.18.5 | Network observability and monitoring |
| **Kubernetes Gateway API** | v1 | Ingress routing and traffic management |

### GitOps & Configuration Management

| Tool | Version | Purpose |
|------|---------|---------|
| **Flux CD** | 1.7.6 | GitOps continuous delivery |
| **Kustomize** | v1beta1 | Kubernetes manifest customization |
| **Helm** | 3+ | Kubernetes package manager |
| **SOPS** | Latest | Secrets encryption in Git |
| **Age** | Latest | Modern encryption for SOPS |

### Database

| Tool | Version | Purpose |
|------|---------|---------|
| **CloudNative PG** | 0.26.1 | PostgreSQL Kubernetes operator |
| **PostgreSQL** | 15.2 | Relational database (multi-cluster fleet) |

### AI/ML Infrastructure

| Tool | Version | Purpose |
|------|---------|---------|
| **vLLM** | v0.9.1 | High-throughput LLM inference server |
| **Qwen 3.6 27B Abliterated** | Latest | Uncensored reasoning model (A100 deep thinker tier) |
| **Qwen 2.5 Coder 7B Abliterated** | Latest | Fast tool-calling dispatcher (L4 24/7 tier) |
| **NVIDIA L4 GPU** | - | 24/7 GPU for fast triage and dispatch |
| **NVIDIA A100 80GB** | - | SPOT GPU for deep reasoning and multi-file context |

### Development Environment

| Tool | Version | Purpose |
|------|---------|---------|
| **Mise** | Latest | Development tool version manager |
| **Dev Containers** | Latest | Consistent development environment |
| **k9s** | Latest | Kubernetes CLI dashboard |

### Monitoring & Observability

| Tool | Version | Purpose |
|------|---------|---------|
| **Prometheus** | Latest | Metrics collection via kube-prometheus-stack |
| **Grafana** | Latest | Dashboards & visualizations |
| **Tailscale** | Latest | Secure VPN access to internal services |

---

## Project Structure

```
gcloud-lab/
├── modules/                          # Terraform IaC modules
│   ├── providers.tf                  # Provider configurations
│   ├── gke.tf                        # GKE cluster definition
│   ├── vpc.tf                        # VPC and subnet configuration
│   ├── nodepool.tf                   # Standard node pool
│   ├── nodepool-gpu.tf               # GPU node pools (L4 + A100 SPOT)
│   ├── flux.tf                       # Flux GitOps bootstrap
│   ├── helm.tf                       # Helm chart deployments (Cilium)
│   └── variables.tf                  # Input variables
│
├── clusters/                         # Cluster configurations
│   └── devops-lab/
│       ├── flux-system/              # Flux CD components
│       │   ├── gotk-components.yaml  # Flux controllers
│       │   ├── gotk-sync.yaml        # Git repository sync
│       │   └── kustomization.yaml    # Flux kustomization
│       ├── customer1.yaml            # Customer1 Kustomization
│       ├── agent-forge.yaml          # AgentForge Kustomization
│       ├── infra-controllers.yaml    # Infrastructure controllers (CNPG, KEDA, Monitoring, Tailscale)
│       └── infra-configs.yaml        # Infrastructure configs
│
├── infrastructure/                   # Infrastructure components
│   ├── controllers/
│   │   ├── base/
│   │   │   ├── cnpg/                 # CloudNative PG operator
│   │   │   ├── keda/                 # KEDA autoscaling
│   │   │   ├── monitoring/           # Prometheus + Grafana (no public ingress)
│   │   │   └── tailscale/            # Tailscale Operator for secure VPN access
│   │   └── staging/
│   │       └── kustomization.yaml    # Aggregates all base components
│   └── configs/
│       └── staging/
│           └── kustomization.yaml
│
├── apps/                             # Application deployments
│   ├── base/
│   │   ├── customer1/
│   │   │   ├── namespace.yaml        # Namespace definition
│   │   │   ├── deployment.yaml       # N8N + vLLM deployments
│   │   │   ├── service.yaml          # ClusterIP services
│   │   │   ├── storage.yaml          # PersistentVolumeClaims
│   │   │   ├── configmap.yaml        # Application configuration
│   │   │   ├── pg-cluster-customer1.yaml  # PostgreSQL cluster
│   │   │   ├── apigateway.yaml       # GCP Gateway
│   │   │   ├── http-route.yaml       # HTTP routing
│   │   │   ├── healthcheck.yaml      # Health check policy
│   │   │   ├── waitlist-api/         # Waitlist API microservice
│   │   │   │   ├── deployment.yaml
│   │   │   │   ├── service.yaml
│   │   │   │   └── configmap.yaml
│   │   │   └── news_bot/             # News bot microservices
│   │   │       ├── scraper-cronjob.yaml
│   │   │       ├── analyst-cronjob.yaml
│   │   │       ├── telebot-cronjob.yaml
│   │   │       ├── scrapy-configmap.yaml
│   │   │       └── scrapy-urls-configmap.yaml
│   │   ├── agent-forge/
│   │   │   ├── namespace.yaml
│   │   │   ├── vllm-deep-thinker.yaml # A100 deployment with KEDA
│   │   │   ├── openclaw-tenant.yaml   # Per-tenant OpenClaw instance
│   │   │   └── pg-cluster-agentforge.yaml
│   │   ├── kanban/
│   │   │   ├── namespace.yaml
│   │   │   ├── hermes-deployment.yaml # AI agent orchestrator
│   │   │   └── pg-cluster-hermes.yaml
│   │   └── local-business/
│   │       └── template/
│   │           ├── namespace.yaml
│   │           ├── nginx-deployment.yaml
│   │           ├── configmap.yaml
│   │           └── http-route.yaml
│   └── staging/
│       ├── customer1/
│       │   └── kustomization.yaml
│       ├── agent-forge/
│       │   └── kustomization.yaml
│       └── kanban/
│           └── kustomization.yaml
│
├── scripts/
│   └── setup                         # Development setup script
│
├── .devcontainer.json                # Dev container configuration
├── mise.toml                         # Tool version management
├── age.agekey                        # SOPS encryption key
└── README.md                         # This file
```

---

## Infrastructure Components

### GKE Cluster

- **Name**: `devops-lab-cluster`
- **Region**: `us-central1-a`
- **Network**: Custom VPC with dual-stack IPv4/IPv6

### Node Pools

| Pool | Machine Type | Scaling | Purpose |
|------|-------------|---------|---------|
| Standard | e2-standard-2 | 1-16 nodes | General workloads, N8N, web servers |
| GPU L4 (SPOT) | g2-standard-8 + L4 | 0-5 nodes | vLLM dispatcher, 24/7 fast inference |
| GPU A100 (SPOT) | a2-highgpu-1g + A100 80GB | 0-1 nodes | Deep thinker tier, multi-file reasoning |

### Networking

- **VPC**: `devops-lab-network`
- **Primary CIDR**: `10.0.0.0/16`
- **Pod CIDR**: `192.168.32.0/20`
- **Service CIDR**: `192.168.16.0/24`
- **CNI**: Cilium with advanced datapath and NetworkPolicy enforcement
- **Ingress**: Kubernetes Gateway API via `external-http-gateway` with PathPrefix HTTPRoute routing
- **Internal Services**: Tailscale-only — no public ingress for monitoring, databases, or agent infrastructure

### CNPG Database Fleet

Multiple isolated PostgreSQL clusters, each with dedicated databases per application:

| Cluster | Namespace | Databases | Backup |
|---------|-----------|-----------|--------|
| `customer1-pgdb` | customer1 | `n8n`, `news_app`, `waitlist` | GCS, 7-day retention |
| `hermes-pgdb` | kanban | `hermes`, `memory_store` | GCS, 7-day retention |
| `openclaw-pgdb` | agent-forge | Per-tenant isolated DBs | GCS, 7-day retention |
| `siriusdevops-pgdb` | customer1 | `waitlist_prod` | GCS, 30-day retention |

### GitOps Flow

```
GitHub Repository (ghcr.io/sirius0xdev)
       │
       ▼
  Flux Source Controller (watches git, 1min interval)
       │
       ▼
  Flux Kustomize Controller (applies manifests)
       │
       ├── infrastructure/controllers → CNPG, KEDA, Monitoring, Tailscale
       ├── infrastructure/configs     → Cluster configs
       ├── apps/staging/customer1     → PAaaS, N8N, News Bot, Waitlist API
       ├── apps/staging/agent-forge   → Multi-tenant AI agent hosting
       ├── apps/staging/kanban        → AI Agent Team orchestrator
       └── apps/staging/local-business → Business websites
```

---

## Applications

### 1. AgentForge — Private AI Agent Workspace

A premium, uncensored, privacy-first AI agent hosting platform with dual-tier cognitive architecture:

- **Tier 1 (Dispatcher):** L4 GPU SPOT instance running 24/7. Hosts `Qwen2.5-Coder-7B-Instruct-heretic` via vLLM `v0.9.1` for lightning-fast, cheap triage and tool calling.
- **Tier 2 (Deep Thinker):** A100 80GB SPOT instance scaling from 0-1 via KEDA. Hosts `Qwen3.6-27B-heretic` with chunked prefill and FP8 KV cache for massive multi-file context and reasoning without OOMing.
- **Multi-Tenant Isolation:** Each tenant gets an isolated OpenClaw deployment with its own CNPG PostgreSQL database. No cross-tenant data leakage.
- **Landing Page:** Dockerized marketing site at siriusdevops.com, built via CI/CD from GitHub Actions and deployed to the staging kustomization overlay.
- **Container Registry:** All images pushed to `ghcr.io/sirius0xdev`.

### 2. Multi-Profile AI Agent Team

Six specialist AI agents orchestrated through a shared Kanban board, each with isolated memory, tools, and personality:

| Profile | Role | Key Capability |
|---------|------|---------------|
| **backend-dev** | Backend engineering | API design, database schema, K8s manifests |
| **frontend-dev** | Frontend engineering | UI/UX, landing pages, responsive design |
| **researcher** | Deep research | Market analysis, technical deep-dives |
| **outreach** | Communications | Content, social media, community building |
| **quant** | Quantitative analysis | Trading signals, market data pipelines |
| **sec-ops** | Security operations | Vulnerability scanning, audit pipelines |

**Automated Audit-to-Fix Pipeline:** The sec-ops agent continuously scans deployed infrastructure for vulnerabilities. When findings are confirmed, the backend-dev agent is automatically dispatched to remediate — from detection to patch in a single GitOps cycle.

### 3. Gateway API and HTTPRoute

Kubernetes Gateway API replaces legacy Ingress with a clean, declarative routing model:

- **Single Gateway:** `external-http-gateway` handles all external traffic.
- **PathPrefix Routing:** `/agentforge/*` → AgentForge landing, `/waitlist/*` → Waitlist API, `/business/*` → local business sites.
- **No Public Ingress for Internals:** Monitoring (Grafana/Prometheus), databases, and agent infrastructure are accessible only via Tailscale VPN.
- **Cross-Namespace References:** HTTPRoute resources in one namespace can reference Services in another, keeping routing centralized.

### 4. Waitlist API

FastAPI microservice powering the AgentForge waitlist at siriusdevops.com:

- **Database:** asyncpg connection pool to dedicated CNPG PostgreSQL.
- **Idempotent Signups:** `INSERT ... ON CONFLICT DO NOTHING` — duplicate emails are silently ignored, not rejected.
- **Notifications:** Fire-and-forget Telegram webhook on each new signup. No blocking I/O in the request path.
- **Security:** Rate limiting per IP, input sanitization, and CORS whitelist.

### 5. Autonomous News Quant Pipeline (`news_bot`)

An institutional-grade pipeline scraping 371 global feeds to generate actionable futures trading signals:

- **Scraper:** CronJob at `:50` pulling multi-lingual global financial data.
- **Map/Reduce Analyst:** DeepSeek-R1 with a strict 10-step think protocol extracts "Market-Moving DNA" and translates events into explicit futures targets (/ES, /CL, /NQ) with risk:reward, take profit, and stop loss levels.
- **Privacy:** All proprietary technical data stays strictly within the VPC, executing against local models to protect the trading edge.

### 6. Local Business Web Deployment Pipeline

Automated Kubernetes manifest generation for small business websites:

- **Stack:** nginx serving static content from ConfigMap, one namespace per business.
- **Routing:** HTTPRoute with cross-namespace Service references under `/business/<name>` paths.
- **Zero Cold Start:** Static sites have no database dependency — just nginx + ConfigMap, deployed via GitOps.

---

## Getting Started

### Prerequisites

- Google Cloud account with billing enabled
- GitHub account with repository access
- `gcloud` CLI authenticated
- Terraform 1.7+

### Local Development Setup

```bash
# Install tools via mise
./scripts/setup

# Or manually
mise trust && mise install
```

### Infrastructure Deployment

```bash
cd modules

# Initialize Terraform
terraform init

# Set required variables
export TF_VAR_github_token="your-token"
export TF_VAR_github_org="your-org"
export TF_VAR_github_repository="gcloud-lab"

# Plan and apply
terraform plan
terraform apply
```

### Accessing the Cluster

```bash
# Configure kubectl
gcloud container clusters get-credentials devops-lab-cluster \
  --zone us-central1-a \
  --project devops-lab-cluster

# Verify connection
kubectl get nodes

# Use k9s for interactive management
k9s
```

### Accessing Monitoring (Grafana / Prometheus)

Monitoring services are **not publicly exposed**. Access is via Tailscale VPN or port-forwarding:

```bash
# Option 1: Port-forward Grafana
kubectl port-forward svc/prometheus-community-kube-prometheus-stack-grafana \
  -n monitoring 3000:3000

# Option 2: Port-forward Prometheus
kubectl port-forward svc/prometheus-community-kube-prometheus-stack-prometheus \
  -n monitoring 9090:9090
```

⚠️ **Before deploying**, replace the Grafana admin password in
`infrastructure/controllers/base/monitoring/release.yaml` with a secure value,
or create a `monitoring-grafana-admin` Secret instead.

---

## Security

### Secrets Management

- **Encryption**: SOPS with Age encryption
- **Key Storage**: `age.agekey` (do not commit unencrypted)
- **Flux Integration**: Automatic decryption during deployment

### Pod Security

- Non-root containers (UID 1000)
- Filesystem group enforcement
- Privilege escalation disabled
- Resource limits enforced

### Network Security

- Cilium NetworkPolicy for pod-to-pod and namespace-to-namespace isolation
- Kubernetes Gateway API with TLS termination at the load balancer
- Internal services (monitoring, databases, agent infrastructure) accessible only via Tailscale VPN — zero public ingress
- Rate limiting on public-facing APIs (Waitlist, landing page)

### Database Security

- Managed roles with secret-based passwords per application
- Separate PostgreSQL clusters per domain (hermes-pgdb, openclaw-pgdb, siriusdevops-pgdb)
- GCS backups with configurable retention policies
- HA cluster with automatic failover

### Automated Security Auditing

- **sec-ops Agent:** Continuously scans deployed infrastructure for CVEs, misconfigurations, and policy violations
- **Auto-Remediation:** Confirmed findings automatically dispatch the backend-dev agent to patch and commit
- **Audit Trail:** Every finding, fix, and deployment is tracked in Git history — full provenance from detection to resolution

---

## Cost Optimization

- **SPOT GPU Instances**: 60-90% savings on L4 and A100 workloads
- **KEDA Scale-to-Zero**: A100 deep thinker pool scales to 0 when no requests are queued
- **Resource Limits**: CPU and memory caps on every container prevent runaway costs
- **Scheduled Workloads**: CronJobs only run when needed — no idle inference pods
- **Tailscale for Internal Access**: No need for expensive internal load balancers or Cloud NAT for monitoring

---

## Container Images

```
ghcr.io/sirius0xdev/agentforge-landing:latest
ghcr.io/sirius0xdev/waitlist-api:latest
ghcr.io/sirius0xdev/newsscraper:latest
ghcr.io/sirius0xdev/summarizer:latest
ghcr.io/sirius0xdev/news-messenger:latest
docker.n8n.io/n8nio/n8n:2.1.4
ghcr.io/cloudnative-pg/postgresql:15.2
```

---

## Tool Reference

### Terraform Providers

```hcl
google      = "~> 7.14"   # GCP resources
helm        = "~> 2.0"    # Helm chart management
flux        = "~> 1.7"    # GitOps bootstrap
```

### Helm Charts

```yaml
cilium:           1.18.5    # CNI and service mesh
cloudnative-pg:   0.26.1    # PostgreSQL operator
vllm:             0.9.1     # High-throughput LLM serving
```

---

## License

Private repository — All rights reserved.
