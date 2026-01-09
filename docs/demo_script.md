# Demo Script (CTO/VP Ready Walkthrough)

This script is designed for a 10–15 minute demo showing real Kubernetes incidents and evidence-driven recommendations.

## 1) Open the UI

- Confirm the dashboard loads and shows the Demo Workloads panel.
- Point out that the UI uses same-origin API calls via the NGINX proxy.

## 2) Show Baseline Health

- Demo workloads: `ns-a/app-a` and `ns-b/app-b` should be `healthy`.
- Click an incident detail (if any) to show the evidence list and timeline.

## 3) CrashLoopBackOff demo (app-a)

1. Click **Attack crashloop**.
2. Wait for the Demo Workloads panel to show `ns-a/app-a` degraded.
3. Click **Inject crashloop** to generate an incident report.
4. Open the incident detail view.
5. Highlight:
   - Evidence: pod restarts, waiting reason, log tail.
   - Hypotheses and recommended actions (read-only).
   - Timeline stages and stage duration bars.

## 4) Rollout failure demo (app-b)

1. Click **Attack rollout failure**.
2. Confirm `ns-b/app-b` shows degraded and the deployment has unavailable replicas.
3. Click **Inject rollout failure** and open the incident.
4. Point out deployment conditions and image pull errors in evidence.

## 5) High latency demo (app-a)

1. Click **Attack high latency** (toggles app-a latency flag).
2. Click **Inject high latency** and open the incident.
3. Highlight that the evidence includes pod status and logs; recommendations focus on safe validation steps.

## 6) Executive wrap-up

- The system is cloud-neutral and runs on any Kubernetes.
- Investigators are read-only; no auto-remediation.
- LLM recommendations are structured and safe by policy.
- The timeline and evidence give fast incident understanding.
