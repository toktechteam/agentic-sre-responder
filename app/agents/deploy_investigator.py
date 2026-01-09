from __future__ import annotations

from app.models import Evidence, IncidentReport, InvestigationResult


async def deploy_investigation(report: IncidentReport) -> InvestigationResult:
    evidence: list[Evidence] = []
    links: list[str] = []

    workload = (
        report.raw_alert.get("annotations", {}).get("workload")
        if report.raw_alert
        else None
    )
    namespace = (
        report.raw_alert.get("labels", {}).get("namespace", "default")
        if report.raw_alert
        else "default"
    )

    if workload:
        evidence.append(
            Evidence(
                source="deployment",
                detail=f"Workload hint from alert annotations: {workload}",
                severity="info",
            )
        )
        links.extend(
            [
                f"kubectl describe deployment {workload} -n {namespace}",
                f"kubectl rollout status deployment/{workload} -n {namespace}",
            ]
        )
    else:
        evidence.append(
            Evidence(
                source="deployment",
                detail="No workload hint in alert; check recent deployments",
                severity="info",
            )
        )

    return InvestigationResult(evidence=evidence, links=links)

