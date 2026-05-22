# Telegram Webhook Failure Analysis - Deep Dive (Container-Level)

**Date:** 2026-05-10
**Repo:** https://github.com/sirius0xdev/gcloud-lab
**Cluster:** devops-lab (GKE), Namespace: customer1
**Webhook URL:** https://ws.siriusdevops.com/telegram/webhook/default

---

## Status Update

**TLS certificates ARE provisioned** in GCP admin console. The Gateway certmap annotation is working.

The real issues are in the **container configuration** and **missing probes**.

---

## Root Cause #1: NO Liveness/Readiness Probes (CONFIRMED CRITICAL)

**The hermes-agent deployment has ZERO probes defined.**

This means:
- Kubernetes marks pods "Ready" immediately after container start
- The Gateway routes webhook traffic before the process has bound to port 9118
- During restarts, there is no graceful drain
- **A crashed or hung pod stays in the endpoint list forever**

### The /health endpoint problem

The Telegram webhook server runs on **port 9118** via python-telegram-bot's `start_webhook()`. This internally starts an aiohttp server that **ONLY registers the webhook path** (`/telegram/webhook/default`). It does NOT expose a `/health` endpoint.

So a probe like this would FAIL:
```yaml
# THIS WON'T WORK - port 9118 has no /health
readinessProbe:
  httpGet:
    path: /health
    port: 9118
```

### What DOES have a health endpoint?

The **generic webhook adapter** on **port 8644** IS a Hermes-managed server. From the source code, it exposes `/health`. This IS enabled via `WEBHOOK_ENABLED: "true"`.

### The Fix

Add probes targeting port 8644 (the generic webhook server that IS healthy when the gateway is running):

```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8644
  initialDelaySeconds: 10
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
livenessProbe:
  httpGet:
    path: /health
    port: 8644
  initialDelaySeconds: 30
  periodSeconds: 30
  timeoutSeconds: 5
  failureThreshold: 3
```

Alternatively, enable the API server on port 8642 and probe there (it also has `/health`).

---

## Root Cause #2: NO Resource Limits (HIGH)

The **new deployment dropped all resource limits** that existed in the old deployment.

**Old deployment (`deployment.yaml`):**
```yaml
resources:
  requests:
    memory: 2Gi
    cpu: "1"
  limits:
    memory: 3Gi
    cpu: "2"
```

**New deployment (`new-deployment.yaml`):**
```yaml
# NO resources block for the hermes-agent container
```

Only the `hermes-webui` sidecar has limits (500Mi-1Gi memory, 100m-500m CPU).

### Impact
- The hermes-agent container can consume unbounded memory
- With `agent.max_turns: 90` and `gateway_timeout: 1800` (30 min), a single agent run can eat massive memory
- Pod may be OOMKilled by the node, but K8s won't restart it gracefully without probes
- **This is a likely cause of intermittent failures**

### Fix
Add resource limits back:
```yaml
resources:
  requests:
    memory: 2Gi
    cpu: "1"
  limits:
    memory: 4Gi
    cpu: "2"
```

---

## Root Cause #3: Path Handling Concern (MEDIUM)

**Source code** (`/opt/hermes/gateway/platforms/telegram.py:1213`):
```python
webhook_path = urlparse(webhook_url).path or "/telegram"
```

For `TELEGRAM_WEBHOOK_URL=https://ws.siriusdevops.com/telegram/webhook/default`:
- `webhook_path` = `/telegram/webhook/default`
- PTB's aiohttp server registers a handler at exactly `/telegram/webhook/default` on port 9118

**HTTPRoute** (`hermes-webhook.yaml`):
```yaml
rules:
- matches:
  - path:
      type: PathPrefix
      value: /telegram/webhook
  backendRefs:
  - name: http-tele-webhook
    port: 9118
```

**The question:** Does the GKE Gateway strip the `/telegram/webhook` prefix before forwarding?

- If it does NOT strip: Pod receives `/telegram/webhook/default` -> **OK**
- If it DOES strip to `/default`: Pod receives `/default` -> **404**
- If it strips to `/`: Pod receives `/` -> **404**

Most GatewayAPI implementations pass the full original path by default, but some ingress controllers strip the matched prefix. **Verify this on the running cluster.**

---

## Root Cause #4: API Server Not Enabled (MEDIUM)

The old deployment had:
```yaml
- name: API_SERVER_ENABLED
  value: "true"
- name: API_SERVER_HOST
  value: "0.0.0.0"
- name: API_SERVER_PORT
  value: "8642"
- name: API_SERVER_KEY
  valueFrom: {secretKeyRef: ...}
- name: API_SERVER_MODEL_NAME
  value: "hermes-agent"
```

**These are ALL absent from `new-deployment.yaml`.** Port 8642 is declared as a containerPort but nothing listens on it because `API_SERVER_ENABLED` is not set.

The API server exposes `/health` and `/health/detailed` endpoints. Without it, you lose a convenient health check and the API server interface.

---

## Other Findings

### 5. TELEGRAM_WEBHOOK_ENABLED is Ignored (INFO)

The code only checks if `TELEGRAM_WEBHOOK_URL` is set (non-empty). It does NOT read `TELEGRAM_WEBHOOK_ENABLED`. The env var in the deployment is a dead config — set but ignored.

### 6. vLLM Service Name Mismatch (INFO)

```yaml
OPENAI_BASE_URL: "http://openclaw-brain-service.customer1.svc.cluster.local:8000/v1"
```

But the active vLLM deployment (`rtx6000-vllm.yaml`) creates a service named `rtx6000-brain-service`. If Hermes ever switches from xAI to the openai provider, local vLLM is unreachable.

### 7. SOPS Secrets (VERIFY)

Both `hermes-secret.yaml` and `tele-webhook.yaml` are SOPS-encrypted. Verify they are decrypted in the cluster:
```bash
kubectl get secret hermes-secrets -n customer1 -o jsonpath='{.data.TELEGRAM_BOT_TOKEN}' | base64 -d
kubectl get secret telegram-webhook -n customer1 -o jsonpath='{.data.TELEGRAM_WEBHOOK_SECRET}' | base64 -d
```

### 8. Container Env Vars Summary

| Variable | Value | Notes |
|----------|-------|-------|
| TELEGRAM_WEBHOOK_URL | https://ws.siriusdevops.com/telegram/webhook/default | OK |
| TELEGRAM_WEBHOOK_PORT | 9118 | OK |
| TELEGRAM_WEBHOOK_SECRET | From SOPS secret | Verify decrypted |
| TELEGRAM_WEBHOOK_ENABLED | "true" | **Ignored by code** |
| TELEGRAM_BOT_TOKEN | From SOPS secret | Verify decrypted |
| TELEGRAM_ALLOWED_USERS | 7528130947 | OK |
| WEBHOOK_ENABLED | "true" | OK (enables port 8644 /health) |
| WEBHOOK_PORT | 8644 | OK |
| API_SERVER_ENABLED | **NOT SET** | Port 8642 has no listener |
| HERMES_MODEL_PROVIDER | xai | OK (uses Grok) |
| HERMES_MODEL | grok-4.20-0309-reasoning | OK |

---

## Recommended Fix (Priority Order)

### P0 - Add Probes (will detect and restart hung/crashed pods)

Add to `new-deployment.yaml` under the hermes-agent container spec:

```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8644
  initialDelaySeconds: 10
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
livenessProbe:
  httpGet:
    path: /health
    port: 8644
  initialDelaySeconds: 30
  periodSeconds: 30
  timeoutSeconds: 5
  failureThreshold: 3
```

### P1 - Add Resource Limits (prevents OOM kills)

```yaml
resources:
  requests:
    memory: 2Gi
    cpu: "1"
  limits:
    memory: 4Gi
    cpu: "2"
```

### P2 - Verify Path Handling

Test if the Gateway passes the full path:
```bash
# From inside the pod, check what the webhook server receives
kubectl exec -n customer1 deploy/hermes-agent -- curl -s http://localhost:9118/telegram/webhook/default -X POST -H "Content-Type: application/json" -d '{}'
```

### P3 - Enable API Server (optional, gives /health on 8642)

Add back the API_SERVER_ENABLED env var if you want the API server health endpoint.

---

## Diagnostic Commands

Run these on the cluster RIGHT NOW to confirm the current state:

```bash
# 1. Check pod status and restart count
kubectl get pods -n customer1 -l app=hermes-agent -o wide

# 2. Check events for OOMKilled or probe failures
kubectl describe pod -n customer1 -l app=hermes-agent | grep -A5 -i 'oom\|probe\|restart'

# 3. Check if the webhook port is actually listening
kubectl exec -n customer1 deploy/hermes-agent -- ss -tlnp | grep 9118

# 4. Check if port 8644 health endpoint works
kubectl exec -n customer1 deploy/hermes-agent -- curl -s http://localhost:8644/health

# 5. Check logs for webhook startup messages
kubectl logs -n customer1 deploy/hermes-agent --tail=50 | grep -i 'webhook\|listening\|9118'

# 6. Verify SOPS secrets are decrypted
kubectl get secret hermes-secrets -n customer1 -o jsonpath='{.data.TELEGRAM_BOT_TOKEN}' | base64 -d && echo
kubectl get secret telegram-webhook -n customer1 -o jsonpath='{.data.TELEGRAM_WEBHOOK_SECRET}' | base64 -d && echo

# 7. Check if the webhook is registered with Telegram (using the pod's bot token)
BOT_TOKEN=$(kubectl get secret hermes-secrets -n customer1 -o jsonpath='{.data.TELEGRAM_BOT_TOKEN}' | base64 -d)
curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo" | python3 -m json.tool

# 8. Test the full path through the Gateway
curl -v https://ws.siriusdevops.com/telegram/webhook/default -X POST -H "Content-Type: application/json" -d '{}' 2>&1

# 9. Check container memory usage
kubectl top pod -n customer1 -l app=hermes-agent 2>/dev/null || echo "metrics-server not available"

# 10. Check resource limits on the container
kubectl get pod -n customer1 -l app=hermes-agent -o jsonpath='{.items[0].spec.containers[0].resources}'
```

---

## Files to Modify

1. `apps/base/customer1/hermes-agent/new-deployment.yaml` - Add probes + resource limits
2. Optionally: Re-enable API server env vars in `new-deployment.yaml`
