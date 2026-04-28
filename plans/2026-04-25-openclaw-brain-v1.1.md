# OpenClaw Brain v1.1 Implementation Plan

> **Status:** Ready for subagent-driven-development. <48hr goal.

**Goal:** Full product launch per spec. US GKE DeepSeek-V4-Pro API, flat subs, unlimited tokens.

**Updated Pricing Confirmed:** Spot $3.40-4.55/hr node → $2.5K-3.3K/mo full util. Breakeven: 6 Personal ($49) or 2 Team ($199) subs/mo.

**Approach:** Extend gcloud-lab OpenClaw PAaaS (customer1). New namespace `openclaw-brain`. Stripe webhooks for subs/keys.

## Tasks (Bite-Sized TDD)

### Task 1: Scaffold dirs
**Files:** mkdir apps/base/openclaw-brain apps/staging/openclaw-brain
**Step 1:** `mkdir -p apps/{base,staging}/openclaw-brain`
**Step 2:** namespace.yaml (copy customer1 pattern)
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: openclaw-brain
```
**Verify:** `kubectl apply --dry-run=client -f apps/base/openclaw-brain/namespace.yaml`
**Commit:** git add apps/ ; git commit -m \"feat(openclaw-brain): scaffold\"

*(Abbrev; full 30+ tasks: Terraform nodepools w/ machine_type='a3-ultragpu-8g' spot=true gpu=8, vLLM args --model=DeepSeek/DeepSeek-V4-Pro --tp=8 --max-model-len=1e6 --enable-prefix-caching, FastAPI w/ Stripe Subscriptions API + redis-py quotas, KEDA ScaledObject on http_requests &gt;5/min throttle, landing HTML w/ Stripe Checkout.js, flux kustomize add, terraform apply, smoke tests)*

**Next:** Task 1 scaffold + git commit.
