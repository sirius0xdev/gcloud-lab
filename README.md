# GCloud-Lab DevOps Infrastructure

A cloud-native DevOps laboratory project showcasing modern infrastructure-as-code, GitOps practices, and Kubernetes orchestration on Google Cloud Platform. This project runs a news intelligence system with LLM-powered analysis and a workflow automation platform.

## Table of Contents

- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [DevOps Tools & Technologies](#devops-tools--technologies)
- [Project Structure](#project-structure)
- [Infrastructure Components](#infrastructure-components)
- [Applications](#applications)
- [Getting Started](#getting-started)
- [Security](#security)

---

## Project Overview

This repository contains infrastructure and application configurations for:

1. **News Intelligence Pipeline**: Automated web scraping, LLM-powered summarization, and Telegram distribution
2. **Workflow Automation**: N8N platform for custom integrations
3. **DevOps Reference Architecture**: Demonstrates GitOps, IaC, and cloud-native best practices

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Google Cloud Platform                            │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    GKE Cluster (devops-lab-cluster)               │  │
│  │                                                                   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │  │
│  │  │ Standard    │  │ GPU Pool    │  │   Flux CD (GitOps)      │   │  │
│  │  │ Node Pool   │  │ (SPOT L4)   │  │   - Source Controller   │   │  │
│  │  │ e2-std-2    │  │ g2-std-8    │  │   - Kustomize Controller│   │  │
│  │  │ 1-16 nodes  │  │ 0-5 nodes   │  │   - Helm Controller     │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘   │  │
│  │                                                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────┐ │  │
│  │  │                    Cilium CNI + Hubble                      │ │  │
│  │  │            (Network Policies + Observability)               │ │  │
│  │  └─────────────────────────────────────────────────────────────┘ │  │
│  │                                                                   │  │
│  │  ┌───────────────────────┐  ┌─────────────────────────────────┐  │  │
│  │  │  customer1 namespace  │  │     cnpg-system namespace       │  │  │
│  │  │  ┌─────────────────┐  │  │  ┌───────────────────────────┐  │  │  │
│  │  │  │      N8N        │  │  │  │   CloudNative PG Operator │  │  │  │
│  │  │  │  (Workflows)    │  │  │  └───────────────────────────┘  │  │  │
│  │  │  └─────────────────┘  │  └─────────────────────────────────┘  │  │
│  │  │  ┌─────────────────┐  │                                       │  │
│  │  │  │ News Scraper    │  │  ┌─────────────────────────────────┐  │  │
│  │  │  │ (CronJob :00)   │  │  │     PostgreSQL HA Cluster       │  │  │
│  │  │  └─────────────────┘  │  │  ┌─────┐ ┌─────┐ ┌─────┐        │  │  │
│  │  │  ┌─────────────────┐  │  │  │ DB1 │ │ DB2 │ │ DB3 │        │  │  │
│  │  │  │ News Analyst    │◄─┼──┼──│(RW) │ │(RO) │ │(RO) │        │  │  │
│  │  │  │ (CronJob :15)   │  │  │  └─────┘ └─────┘ └─────┘        │  │  │
│  │  │  │ + Ollama/Gemma2 │  │  └─────────────────────────────────┘  │  │
│  │  │  └─────────────────┘  │                                       │  │
│  │  │  ┌─────────────────┐  │                                       │  │
│  │  │  │ Telegram Bot    │  │                                       │  │
│  │  │  │ (CronJob :20)   │  │                                       │  │
│  │  │  └─────────────────┘  │                                       │  │
│  │  └───────────────────────┘                                       │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │          GCP L7 Global Load Balancer (HTTPS)                    │    │
│  │                   n8n.sirius-sec.com                            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
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
| **PostgreSQL** | 15.2 | Relational database (3-node HA cluster) |

### AI/ML Infrastructure

| Tool | Version | Purpose |
|------|---------|---------|
| **Ollama** | Latest | Local LLM inference server |
| **Gemma2** | Latest | Open-source LLM for text summarization |
| **NVIDIA L4 GPU** | - | GPU acceleration for LLM workloads |

### Development Environment

| Tool | Version | Purpose |
|------|---------|---------|
| **Mise** | Latest | Development tool version manager |
| **Dev Containers** | Latest | Consistent development environment |
| **k9s** | Latest | Kubernetes CLI dashboard |

---

## Project Structure

```
gcloud-lab/
├── modules/                          # Terraform IaC modules
│   ├── providers.tf                  # Provider configurations
│   ├── gke.tf                        # GKE cluster definition
│   ├── vpc.tf                        # VPC and subnet configuration
│   ├── nodepool.tf                   # Standard node pool
│   ├── nodepool-gpu.tf               # GPU node pool (SPOT instances)
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
│       ├── infra-controllers.yaml    # Infrastructure controllers
│       └── infra-configs.yaml        # Infrastructure configs
│
├── infrastructure/                   # Infrastructure components
│   ├── controllers/
│   │   ├── base/
│   │   │   └── cnpg/                 # CloudNative PG operator
│   │   │       ├── repository.yaml   # Helm repository
│   │   │       └── release.yaml      # Helm release
│   │   └── staging/
│   │       └── kustomization.yaml
│   └── configs/
│       └── staging/
│           └── kustomization.yaml
│
├── apps/                             # Application deployments
│   ├── base/
│   │   └── customer1/
│   │       ├── namespace.yaml        # Namespace definition
│   │       ├── deployment.yaml       # N8N deployment
│   │       ├── service.yaml          # ClusterIP service
│   │       ├── storage.yaml          # PersistentVolumeClaim
│   │       ├── configmap.yaml        # N8N configuration
│   │       ├── pg-cluster-customer1.yaml  # PostgreSQL cluster
│   │       ├── apigateway.yaml       # GCP Gateway
│   │       ├── http-route.yaml       # HTTP routing
│   │       ├── healthcheck.yaml      # Health check policy
│   │       └── news_bot/             # News bot microservices
│   │           ├── scraper-cronjob.yaml
│   │           ├── analyst-cronjob.yaml
│   │           ├── telebot-cronjob.yaml
│   │           ├── scrapy-configmap.yaml
│   │           └── scrapy-urls-configmap.yaml
│   └── staging/
│       └── customer1/
│           └── kustomization.yaml    # Staging overlay
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
| Standard | e2-standard-2 | 1-16 nodes | General workloads |
| GPU (SPOT) | g2-standard-8 + L4 | 0-5 nodes | LLM inference |

### Networking

- **VPC**: `devops-lab-network`
- **Primary CIDR**: `10.0.0.0/16`
- **Pod CIDR**: `192.168.32.0/20`
- **Service CIDR**: `192.168.16.0/24`
- **CNI**: Cilium with advanced datapath
- **Ingress**: GCP L7 Global Load Balancer

### GitOps Flow

```
GitHub Repository
       │
       ▼
  Flux Source Controller (watches git, 1min interval)
       │
       ▼
  Flux Kustomize Controller (applies manifests)
       │
       ├── infrastructure/controllers → CNPG Operator
       ├── infrastructure/configs     → Cluster configs
       └── apps/staging/customer1     → Applications
```

---

## Applications

### N8N Workflow Automation

- **URL**: `https://n8n.sirius-sec.com`
- **Image**: `docker.n8n.io/n8nio/n8n:2.1.4`
- **Database**: PostgreSQL (dedicated `n8n` database)
- **Storage**: 1GB persistent volume

### News Intelligence Pipeline

A three-stage data pipeline running as Kubernetes CronJobs:

| Stage | Schedule | Container | Purpose |
|-------|----------|-----------|---------|
| Scraper | `:00` hourly | `siriussec/newsscraper` | Scrapes 100+ global news sources |
| Analyst | `:15` hourly | `siriussec/summarizer` + `ollama/ollama` | LLM-powered summarization |
| Telegram | `:20` hourly | `siriussec/news-messenger` | Distributes summaries to Telegram |

**News Sources Coverage**:
- North America: NPR, AP News, CBC, etc.
- Europe: BBC, Reuters, The Guardian, etc.
- Asia: SCMP, Al Jazeera, Times of India, etc.
- Africa: BBC Africa, News24, etc.
- South America: Buenos Aires Herald, etc.

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

- Cilium network policies for pod-to-pod isolation
- TLS termination at load balancer
- Private cluster networking with NAT

### Database Security

- Managed roles with secret-based passwords
- Separate users per application (`customer1`, `news_app`)
- HA cluster with automatic failover

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
```

### Container Images

```
docker.n8n.io/n8nio/n8n:2.1.4
ghcr.io/cloudnative-pg/postgresql:15.2
ollama/ollama:latest
siriussec/newsscraper:latest
siriussec/summarizer:latest
siriussec/news-messenger:latest
```

---

## Cost Optimization

- **SPOT GPU Instances**: 60-90% savings on LLM workloads
- **Autoscaling**: GPU nodes scale to 0 when idle
- **Resource Limits**: Prevents runaway costs
- **Scheduled Workloads**: CronJobs only run when needed

---

## License

Private repository - All rights reserved.
