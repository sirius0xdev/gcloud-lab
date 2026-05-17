#!/bin/bash
# =============================================================================
# Deploy Trading Platform to Kubernetes
# =============================================================================
#
# Usage:
#   ./deploy/scripts/deploy.sh [staging|production] [tag]
#
# Examples:
#   ./deploy/scripts/deploy.sh staging latest
#   ./deploy/scripts/deploy.sh production v1.2.3
#
# Prerequisites:
#   - kubectl configured with cluster access
#   - Helm 3.x installed
#   - Docker images pushed to registry
#   - cert-manager installed in cluster (for TLS)
# =============================================================================

set -euo pipefail

ENVIRONMENT="${1:-staging}"
IMAGE_TAG="${2:-latest}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(staging|production)$ ]]; then
  echo "ERROR: Environment must be 'staging' or 'production', got '$ENVIRONMENT'"
  exit 1
fi

# Set namespace and values file based on environment
if [[ "$ENVIRONMENT" == "staging" ]]; then
  NAMESPACE="customer1-staging"
  VALUES_FILE="$PROJECT_ROOT/deploy/k8s/overlays/staging/kustomization.yaml"
else
  NAMESPACE="customer1"
  VALUES_FILE="$PROJECT_ROOT/deploy/k8s/overlays/production/kustomization.yaml"
fi

echo "========================================================"
echo "  Deploying Trading Platform to $ENVIRONMENT"
echo "  Image tag: $IMAGE_TAG"
echo "  Namespace: $NAMESPACE"
echo "========================================================"

# Confirm cluster context
CURRENT_CONTEXT=$(kubectl config current-context 2>/dev/null || echo "unknown")
echo "Current kubectl context: $CURRENT_CONTEXT"
read -r -p "Continue? (y/N) " -n 1
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Deployment cancelled."
  exit 1
fi

# Install dependencies (optional)
echo ""
echo "Step 1/5: Checking prerequisites..."

# Check for Helm
if ! command -v helm &>/dev/null; then
  echo "ERROR: helm is not installed"
  exit 1
fi

# Check for kubectl
if ! command -v kubectl &>/dev/null; then
  echo "ERROR: kubectl is not installed"
  exit 1
fi

# Check cluster connectivity
if ! kubectl cluster-info &>/dev/null; then
  echo "ERROR: Cannot connect to Kubernetes cluster"
  exit 1
fi
echo "  ✓ Kubernetes cluster is accessible"

# Create namespace if it doesn't exist
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
echo "  ✓ Namespace $NAMESPACE exists"

# Step 2: Deploy infrastructure (PostgreSQL, Redis, Kafka)
echo ""
echo "Step 2/5: Deploying infrastructure..."
kubectl apply -f "$PROJECT_ROOT/deploy/k8s/base/namespace.yaml"
kubectl apply -f "$PROJECT_ROOT/deploy/k8s/base/configmap.yaml"
echo "  ✓ ConfigMap applied"

# Step 3: Deploy services
echo ""
echo "Step 3/5: Deploying microservices..."

SERVICES=("execute-service" "data-service" "news-service" "api-gateway" "dashboard")

for service in "${SERVICES[@]}"; do
  echo "  Deploying $service..."
  kubectl apply -f "$PROJECT_ROOT/deploy/k8s/base/${service}-deployment.yaml"
  kubectl apply -f "$PROJECT_ROOT/deploy/k8s/base/${service}-service.yaml"
done

echo "  ✓ All services deployed"

# Step 4: Deploy ingress and networking
echo ""
echo "Step 4/5: Configuring ingress and networking..."
kubectl apply -f "$PROJECT_ROOT/deploy/k8s/base/ingress.yaml"
echo "  ✓ Ingress configured"

# Apply NetworkPolicies from security review
if [[ -d "$PROJECT_ROOT/trading-platform/security/network-policies" ]]; then
  kubectl apply -f "$PROJECT_ROOT/trading-platform/security/network-policies/"
  echo "  ✓ NetworkPolicies applied"
fi

# Step 5: Wait for rollouts
echo ""
echo "Step 5/5: Waiting for deployments to stabilize..."

for service in "${SERVICES[@]}"; do
  echo "  Waiting for $service..."
  if ! kubectl rollout status "deployment/${service}" -n "$NAMESPACE" --timeout=5m; then
    echo "WARNING: $service rollout timed out"
    echo "  Check pods: kubectl get pods -n $NAMESPACE -l app=$service"
    echo "  Check logs: kubectl logs -n $NAMESPACE -l app=$service --tail=100"
    exit 1
  fi
done

echo ""
echo "========================================================"
echo "  Deployment complete! All services running."
echo "========================================================"
echo ""
echo "Useful commands:"
echo "  kubectl get pods -n $NAMESPACE"
echo "  kubectl get svc -n $NAMESPACE"
echo "  kubectl get ingress -n $NAMESPACE"
echo "  kubectl logs -n $NAMESPACE -l app=$service -f"
