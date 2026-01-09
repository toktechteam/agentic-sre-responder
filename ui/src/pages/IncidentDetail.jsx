import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchIncident } from "../api.js";
import Timeline from "../components/Timeline.jsx";
import EvidenceList from "../components/EvidenceList.jsx";
import Recommendations from "../components/Recommendations.jsx";

export default function IncidentDetail() {
  const { incidentId } = useParams();
  const [incident, setIncident] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    fetchIncident(incidentId)
      .then((data) => {
        if (mounted) {
          setIncident(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (mounted) {
          setError(err.message);
          setLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, [incidentId]);

  if (loading) {
    return <div className="rounded-2xl border border-white/10 bg-white/5 p-8">Loading incident...</div>;
  }

  if (error || !incident) {
    return (
      <div className="rounded-2xl border border-red-400/40 bg-red-500/10 p-8 text-red-200">
        {error || "Incident not found"}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <Link to="/" className="text-xs uppercase tracking-[0.3em] text-slate-400">
        Back to incidents
      </Link>
      <section className="rounded-3xl border border-white/10 bg-white/5 p-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="text-xs uppercase tracking-[0.3em] text-amber-300">
              {incident.incident_type}
            </div>
            <h1 className="mt-2 font-display text-3xl">{incident.summary}</h1>
            <p className="mt-2 text-sm text-slate-300">Severity: {incident.severity}</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 text-xs text-slate-300">
            Status: {incident.status}
          </div>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Timeline timeline={incident.timeline} stageTimings={incident.stage_timings} />
          <EvidenceList evidence={incident.evidence} />
        </div>
        <div className="space-y-6">
          <Recommendations
            hypotheses={incident.root_cause_hypotheses}
            actions={incident.recommended_actions}
          />
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
            <h3 className="font-display text-lg">Command links</h3>
            <ul className="mt-3 space-y-2 text-xs text-slate-300">
              {incident.links.map((link, idx) => (
                <li key={idx} className="rounded-lg bg-slate-950/60 p-2 font-mono">
                  {link}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
