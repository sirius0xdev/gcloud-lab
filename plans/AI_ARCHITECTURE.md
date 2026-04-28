# Dual-Tier AI Architecture: L4 Dispatcher & A100 Deep Thinker

This document outlines the cost-optimized, dual-tier LLM architecture deployed in the cluster using OpenClaw, vLLM, and KEDA.

## Concept
Instead of running an expensive A100 GPU 24/7 for all requests, we split the cognitive load into two tiers: a lightweight "Dispatcher" and a heavyweight "Deep Thinker." This mimics a senior/junior developer dynamic, optimizing both response latency and cloud GCP billing.

## Tier 1: The Dispatcher (L4 GPU)
- **Hardware:** 1x NVIDIA L4 (24GB VRAM)
- **Model:** `Qwen2.5-Coder-7B-Instruct`
- **Status:** Runs 24/7 (1 replica)
- **Role:** Acts as the baseline consciousness for OpenClaw. Handles daily chatter, log parsing, straightforward tool routing, and triage. Lightning-fast token generation at a fraction of the cost.

## Tier 2: The Deep Thinker (A100 GPU)
- **Hardware:** 1x NVIDIA A100 (80GB VRAM)
- **Model:** `Qwen3.6-27B-heretic`
- **Status:** Scaled to zero by default.
- **Role:** Activated only for massive context tasks, deep research, and complex multi-file architectural reasoning.

## Scaling & Routing Mechanics (KEDA + OpenClaw)
1. **Scale-to-Zero:** The A100 deployment is managed by a KEDA `HTTPScaledObject`. It scales down to `0` replicas after 15 minutes of inactivity.
2. **Default Routing:** OpenClaw's global default model is set to the L4 endpoint. All standard messages hit the L4 immediately.
3. **Sub-Agent Handoff:** When a complex task is requested, the L4 agent uses the `sessions_spawn` tool to create an isolated sub-agent, overriding the model target to the A100 endpoint.
4. **Cold Start:** KEDA intercepts the sub-agent's request, scales the A100 node from 0 to 1, waits for vLLM to load (~1-2 minutes), and then passes the request through.
5. **Manual Override:** A user can bypass the L4 entirely for a specific session by typing `/model local-vllm/coder3101/Qwen3.5-27B-heretic` in the OpenClaw chat.
