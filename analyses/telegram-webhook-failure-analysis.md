# Telegram Webhook Failure Analysis - Hermes Agent on GKE

**Date:** 2026-05-10
**Repo:** https://github.com/sirius0xdev/gcloud-lab
**Cluster:** devops-lab (GKE)
**Namespace:** customer1
**Webhook URL:** https://ws.siriusdevops.com/telegram/webhook/default

---

## Executive Summary

The Telegram webhook is failing because **there is no valid TLS certificate for `ws.siriusdevops.com`** at the Gateway layer. Telegram strictly requires HTTPS with a publicly-trusted certificate for webhook delivery. The Gateway listener declares `protocol: HTTPS` but has no `tls.certificateRefs` and relies on a GKE `CertMap` annotation referencing `gateway-cert-map` — a resource that **does not exist** in the repository. Cert-manager is configured but disconnected from the GatewayAPI setup (HTTP-01 solver points to a non-existent Traefik ingress class).

**TL;DR:** Telegram tries to POST to `https://ws.siriusdevops.com/...`, but the Gateway has no certificate to present during the TLS handshake. Connection fails before it ever reaches the hermes-agent pod.

---

## Root Cause #1: Missing TLS Certificate (CRITICAL)

### What's happening

**File:** `infrastructure/gatewayapi/apigateway.yaml`

```yaml
listeners:
- name: https
  protocol: HTTPS
  port: 443
  allowedRoutes:
    namespaces:
      from: All
```

The listener says HTTPS but has **no `tls:` block**. It relies entirely on this annotation:

```yaml
annotations:
  networking.gke.io/certmap: gateway-cert-map
```

### The problem

- **No `CertMap` or `CertMapEntry` resource** exists anywhere in the repository for `gateway-cert-map`
- Without it, GKE has no managed certificate to attach to the Gateway
- Telegram's webhook delivery gets a TLS handshake failure or no certificate

### Cert-manager is also broken

**File:** `infrastructure/controllers/base/certmanager/clusterissuer.yaml`

```yaml
solvers:
  - http01:
      ingress:
        class: traefik
```

- HTTP-01 solver references `class: traefik`, but **no Traefik ingress controller exists** in the cluster
- **No `Certificate` CRs** exist for `ws.siriusdevops.com` or any other domain
- Cert-manager is completely disconnected from the GatewayAPI setup

### How to fix (choose ONE approach)

**Option A: GKE Managed Certificates (recommended for GatewayAPI)**

Create a `ManagedCertificate` + `BackendConfig` or `CertMap`/`CertMapEntry`:

```yaml
apiVersion: networking.gke.io/v1
kind: ManagedCertificate
metadata:
  name: hermes-webhook-cert
  namespace: customer1
spec:
  domains:
    - ws.siriusdevops.com
    - brain.siriusdevops.com
    - paaas.siriusdevops.com
```

Then add `tls.certificateRefs` to the Gateway listener:

```yaml
listeners:
- name: https
  protocol: HTTPS
  port: 443
  tls:
    certificateRefs:
    - name: hermes-webhook-cert
      group: networking.gke.io
```

**Option B: Fix Cert-manager with DNS-01**

Switch ClusterIssuer from HTTP-01/Traefik to DNS-01 (e.g., Cloudflare, GCP DNS, or Route53), then create `Certificate` resources for each domain.

---

## Root Cause #2: No Readiness/Liveness Probes (HIGH)

**File:** `apps/base/customer1/hermes-agent/new-deployment.yaml`

No readiness or liveness probes are defined on any hermes-agent deployment.

### Impact
- Pods are marked "Ready" immediately after container start
- Gateway routes traffic to the webhook port (9118) before the process has bound to it
- During restarts, traffic hits pods that haven't initialized

### Fix
Add probes to the deployment:

```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 9118
  initialDelaySeconds: 5
  periodSeconds: 10
livenessProbe:
  httpGet:
    path: /health
    port: 9118
  initialDelaySeconds: 15
  periodSeconds: 30
```

---

## Root Cause #3: SOPS Encrypted Secrets (HIGH)

**Files:**
- `apps/base/customer1/hermes-agent/hermes-secret.yaml` (SOPS encrypted)
- `apps/base/customer1/hermes-agent/tele-webhook.yaml` (SOPS encrypted)

These contain `TELEGRAM_BOT_TOKEN` and `TELEGRAM_WEBHOOK_SECRET`.

### Risk
- If the deployment pipeline (Flux/Kustomize controller) is **not decrypting SOPS secrets**, pods receive literal `ENC[...]` strings
- The bot token would be invalid, so even if TLS worked, Telegram auth would fail
- The webhook secret would not match, causing Telegram to reject payloads

### Verify
Run `kubectl get secret hermes-secrets -n customer1 -o yaml` and check if values are base64-encoded real tokens or `ENC[...]` strings.

---

## Secondary Issues

### 3a. Service Name Mismatch (vLLM Integration)

**File:** `apps/base/customer1/hermes-agent/new-deployment.yaml`

```yaml
OPENAI_BASE_URL: "http://openclaw-brain-service.customer1.svc.cluster.local:8000/v1"
```

But the active vLLM deployment (`rtx6000-vllm.yaml`) creates a service named **`rtx6000-brain-service`**.

- `OPENAI_BASE_URL` points to `openclaw-brain-service` which may not exist
- If Hermes ever switches to the `openai` provider (instead of `xai`), local vLLM is unreachable
- The model provider defaults to `HERMES_MODEL_PROVIDER: xai` (Grok external API)

### 3b. Duplicate HTTPRoute Deployment

The webhook HTTPRoute (`hermes-webhook.yaml`) is included in **two** kustomization trees:

1. `infrastructure/gatewayapi/gateway-routes/kustomization.yaml` -> deployed via Flux
2. `apps/base/customer1/hermes-agent/kustomization.yaml` -> deployed via Flux

Same resource (`http-telegram-webhook` in `customer1`) from two sources. This may cause Flux reconciliation conflicts.

### 3c. Empty HF_TOKEN in vLLM Deployments

All vLLM deployments have:

```yaml
- name: HF_TOKEN
  value: ""
```

If the model `edp1096/Huihui-Qwen3.6-27B-abliterated-FP8` is a gated model on HuggingFace, it will fail to download.

### 3d. KEDA Scale-to-Zero

**File:** `infrastructure/gpus/base/keda-gpu-scaling/keda-vllm.yaml`

```yaml
minReplicaCount: 0
maxReplicaCount: 1
```

- vLLM scales to **zero** when idle
- First request after cold start incurs full model load time (30-60 seconds)
- For real-time Telegram responses, this causes visible latency

### 3e. PVC Name Collision

Both `rtx6000-vllm.yaml` and `a100-vllm.yaml` define a PVC named `vllm-model-qwen3.6-27b-uncensored` in namespace `customer1`. If both are ever active simultaneously, they conflict.

---

## Architecture Overview

```
                     Internet
                        |
                        v
              [GKE External LB]
                        |
          Gateway: external-http-gateway
         (port 443/HTTPS, NO TLS cert!)
                        |
            +-----------+-----------+
            |           |           |
     ws.siriusdevops.com   brain.siriusdevops.com   paaas.siriusdevops.com
            |           |           |
            v           v           v
    /telegram/webhook    /           /
            |           |           |
            v           v           v
   http-tele-webhook   rtx6000-   paaas-landing
       :9118            brain-       :8080
                       service:8000
            |
            v
   hermes-agent pod
   (ports: 8642, 8644, 9118)
            |
            v
   Model Provider: xai (Grok via external API)
   Fallback: OPENAI_BASE_URL -> openclaw-brain-service (MISMATCHED)
```

---

## vLLM Server Status

| Server | GPU | Model | Quantization | Status |
|--------|-----|-------|-------------|--------|
| RTX 6000 | 1x Pro 6000 (96GB) | edp1096/Huihui-Qwen3.6-27B-abliterated-FP8 | FP8 | **ACTIVE** |
| A100 | 1x A100 (80GB) | Youssofal/Qwen3.6-27B-Abliterated-Heretic-Uncensored-BF16 | BF16 | Commented out |
| L4 | 1x L4 (24GB) | p-e-w/Qwen3-8B-heretic | auto | Commented out |
| Gemma | 1x A100 (80GB) | coder3101/Qwen3.5-27B-heretic | BF16 | Not in kustomization |

**Note:** The architecture plan (`plans/AI_ARCHITECTURE.md`) describes a dual-tier L4 dispatcher + A100 deep thinker setup, but the active deployment only has RTX 6000.

---

## Action Plan (Priority Order)

### P0 - Fix TLS (will unblock Telegram webhooks)

1. **Create a `CertMap`/`CertMapEntry`** or **`ManagedCertificate`** resource for `ws.siriusdevops.com`
2. **Add `tls.certificateRefs`** to the Gateway listener in `apigateway.yaml`
3. Verify with: `curl -vI https://ws.siriusdevops.com/telegram/webhook/default`
4. If cert is valid, Telegram should start delivering webhooks

### P1 - Verify Secrets

5. Check if SOPS secrets are actually decrypted in the cluster
6. Run: `kubectl get secret hermes-secrets -n customer1 -o jsonpath='{.data.TELEGRAM_BOT_TOKEN}' | base64 -d`

### P2 - Add Probes

7. Add readiness/liveness probes to hermes-agent deployment
8. Redeploy

### P3 - Clean Up GatewayAPI

9. Remove duplicate `hermes-webhook.yaml` reference from one kustomization
10. Fix or remove Traefik-referencing ClusterIssuers

### P4 - Fix vLLM Integration

11. Fix `OPENAI_BASE_URL` service name or update kustomization to create `openclaw-brain-service`
12. Set real `HF_TOKEN` in vLLM deployments
13. Consider setting `minReplicaCount: 1` in KEDA for consistent response times

---

## Files Referenced

### GatewayAPI & TLS
- `infrastructure/gatewayapi/apigateway.yaml` - Gateway definition (missing TLS)
- `infrastructure/gatewayapi/gateway-routes/hermes-webhook.yaml` - Webhook HTTPRoute
- `infrastructure/gatewayapi/gateway-routes/route.yaml` - General route
- `infrastructure/controllers/base/certmanager/clusterissuer.yaml` - Cert-manager (Traefik mismatch)

### Hermes Agent Deployment
- `apps/base/customer1/hermes-agent/new-deployment.yaml` - Active deployment + webhook service
- `apps/base/customer1/hermes-agent/deployment.yaml` - Old deployment (no webhook config)
- `apps/base/customer1/hermes-agent/configmap.yaml` - Hermes config
- `apps/base/customer1/hermes-agent/hermes-secret.yaml` - SOPS encrypted secrets
- `apps/base/customer1/hermes-agent/tele-webhook.yaml` - SOPS encrypted webhook secret
- `apps/base/customer1/hermes-agent/kustomization.yaml` - Kustomize composition

### vLLM Infrastructure
- `infrastructure/gpus/base/vllm-servers/rtx6000-vllm.yaml` - Active vLLM server
- `infrastructure/gpus/base/keda-gpu-scaling/keda-vllm.yaml` - KEDA scaling
- `infrastructure/gpus/base/keda-gpu-scaling/vllm-route.yaml` - vLLM external route

### Architecture Plans
- `plans/AI_ARCHITECTURE.md` - AI architecture plan
- `plans/models-to-try.md` - Models being considered

---

## Quick Diagnostic Commands

Run these on the cluster to confirm findings:

```bash
# 1. Check if TLS cert exists for the webhook domain
curl -vI https://ws.siriusdevops.com/telegram/webhook/default 2>&1 | grep -E 'SSL|certificate|subject|issuer'

# 2. Check Gateway status
kubectl get gateway external-http-gateway -n customer1 -o yaml

# 3. Check HTTPRoute status (attached/programmed)
kubectl get httproute http-telegram-webhook -n customer1 -o yaml

# 4. Verify secrets are decrypted
kubectl get secret hermes-secrets -n customer1 -o jsonpath='{.data.TELEGRAM_BOT_TOKEN}' | base64 -d && echo

# 5. Check if pods are actually ready
kubectl get pods -n customer1 -l app=hermes-agent -o wide

# 6. Check CertMap exists
kubectl get certmap gateway-cert-map -A 2>/dev/null || echo "CertMap NOT FOUND"

# 7. Check managed certificates
kubectl get managedcertificate -A 2>/dev/null || echo "No ManagedCertificates"

# 8. Check cert-manager certificates
kubectl get certificate -A 2>/dev/null || echo "No Certificates"

# 9. Check vLLM pod status
kubectl get pods -n customer1 -l app=rtx6000-brain-vllm -o wide

# 10. Test internal webhook endpoint
kubectl exec -n customer1 deploy/hermes-agent -- curl -s http://localhost:9118/health || echo "Health check failed"
```
