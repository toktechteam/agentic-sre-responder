# agentic-sre-responder

## Project Overview

agentic-sre-responder is a Kubernetes incident response system that uses read-only AI agents to investigate real workloads and produce evidence-driven recommendations. It targets the gap between alerting and action by automating the tedious, multi-source investigation steps that slow down incident response.

Traditional monitoring and on-call workflows break down when teams face alert storms, complex dependencies, and fragmented sources of truth. Engineers spend most of their time collecting evidence rather than resolving the incident. AI agents are needed here not as chatbots, but as workflow automation that can assemble context, reason about failures, and deliver structured next steps.

## Problem Statement

- Alert fatigue overwhelms teams with noisy signals and repeated escalations.
- Slow MTTR results from manual investigation across pods, deployments, events, and logs.
- Siloed data across metrics, logs, events, and configs blocks fast correlation.
- Human-heavy triage loops delay root cause discovery and amplify risk.

## Solution Architecture

agentic-sre-responder orchestrates multiple read-only agents that perform staged investigation:

- Alert -> Triage -> Investigate -> Recommend -> Validate
- Agents collect evidence from Kubernetes and deployment metadata.
- Orchestration stages provide a measurable, auditable timeline and MTTR proxies.

![arch. diagram](agentic-sre-responder.png)

Agents are strictly read-only to ensure safe operation in regulated environments and to avoid automated changes in production systems.

## Key Capabilities

- Real Kubernetes incident investigation (pods, deployments, events, logs)
- Evidence-driven recommendations with structured outputs
- Structured incident timelines with stage timing metrics
- MTTR proxy metrics for triage, investigation, and recommendation stages
- Slack integration for incident notifications
- Cloud-neutral, platform-agnostic design

## Demo Scenarios

- CrashLoopBackOff: breaks a required env var for a demo app to force restarts
- Rollout failure: sets a bad image tag to trigger ImagePullBackOff
- High latency: toggles a latency flag to slow request handling

The dashboard shows workload health, evidence grouped by source, incident timelines, and LLM-generated hypotheses and recommended actions.

## Architecture Components

- API service (FastAPI): incident ingestion, storage, demo endpoints
- Agent orchestrator: async, staged workflows for triage/investigation/recommendation
- Investigators: Kubernetes and deployment evidence collection
- LLM provider abstraction: OpenAI, Bedrock, or mock
- Redis + SQLite: state and incident persistence
- Dashboard UI: same-origin calls via NGINX proxy
- Demo workloads: two lightweight apps in separate namespaces

## Security & Governance

- Read-only Kubernetes RBAC for investigators
- Scoped demo attacker permissions limited to demo namespaces only
- No auto-remediation in the agent workflow
- Safe LLM prompting and structured responses
- Suitable for regulated environments with strict change controls

## Deployment Model

- Runs on KIND for local demo
- Runs on any Kubernetes (on-prem, EKS, AKS, GKE)
- No cloud lock-in
- Optional LLM providers (OpenAI or Bedrock)

## Value to the Organization

- Reduced MTTR through automated evidence collection
- Faster incident understanding for responders and leadership
- Lower cognitive load on SREs and on-call engineers
- Better postmortems with structured timelines and evidence
- Executive visibility into operational health and response efficacy

## What Makes This Different

- Not another monitoring dashboard
- Not a chatbot
- Not auto-remediation
- Agentic, evidence-first, infrastructure-aware design

## Who This Is For

- SRE teams
- Platform engineering teams
- Cloud operations teams
- CTO / VP Engineering leadership

## Demo & Getting Started

- Setup instructions: `setup.md`
- Demo setup addendum: `docs/demo_setup.md`
- Demo walkthrough: `docs/demo_script.md`

Run the demo end-to-end on KIND using the setup docs and then follow the demo script to trigger real incidents and review the evidence-driven response.
