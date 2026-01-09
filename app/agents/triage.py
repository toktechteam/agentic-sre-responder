from __future__ import annotations

from app.models import Evidence, IncidentReport
from app.results import TriageResult


async def triage_alert(report: IncidentReport) -> TriageResult:
    evidence: list[Evidence] = []
    severity = report.severity or "unknown"
    evidence.append(Evidence(source="triage", detail=f"Incident severity: {severity}"))
    evidence.append(Evidence(source="triage", detail=f"Incident type: {report.incident_type}"))
    return TriageResult(evidence=evidence)

