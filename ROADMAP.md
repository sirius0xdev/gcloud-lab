# GKE AI Inference Platform - Project Roadmap

This roadmap tracks the tasks required to transition our dual-tier vLLM architecture (L4 Dispatcher + A100 Thinker) into a secure, multi-tenant SaaS offering for a limited group of premium users.

## Phase 1: Security & API Gateway
- [ ] **Choose API Gateway:** Select an ingress/gateway solution capable of API key auth and rate limiting (e.g., Kong, Traefik, or GCP API Gateway).
- [ ] **Implement API Key Auth:** Require a valid token/key to hit the vLLM endpoints.
- [ ] **Configure Rate Limiting:** Prevent a single user from spamming requests and hogging the L4 queue or unnecessarily waking the A100.
- [ ] **Network Isolation:** Ensure vLLM services are not publicly exposed directly; all traffic must flow through the gateway.

## Phase 2: User Access & Quotas
- [ ] **User Tiering:** Define what "access" means. 
    - *Example:* X number of L4 fast-tokens per month, Y number of A100 deep-thinking hours per month.
- [ ] **Usage Tracking:** Implement a lightweight logging/metrics system (Prometheus/Grafana or a custom DB) to track token usage per API key.
- [ ] **Onboarding Process:** Create a secure way to generate and distribute API keys to the limited user cohort.

## Phase 3: Infrastructure Tuning & Observability
- [ ] **A100 Sleep Tuning:** Monitor KEDA scale-down metrics. If users trigger the A100 too frequently, adjust the 15-minute timeout or implement a queuing system for heavy tasks.
- [ ] **Alerting:** Set up Slack/Telegram alerts for GPU OOM (Out of Memory) errors, KEDA scaling failures, and gateway 429 (Rate Limit Exceeded) spikes.
- [ ] **Cost Monitoring:** Set up strict GCP billing alerts to ensure the A100 node doesn't accidentally run 24/7 due to a stuck scale-to-zero metric.

## Phase 4: Billing (Optional)
- [ ] **Stripe Integration:** Hook API key generation to Stripe subscriptions.
- [ ] **Usage-based Billing:** Bill users automatically based on the tokens generated at the Gateway level.
