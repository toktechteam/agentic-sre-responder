import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fetchDemoWorkloads, fetchIncidents, injectDemo, triggerDemoAttack } from "../api.js";
import Charts from "../components/Charts.jsx";

const demoPresets = [
  { incident_type: "crashloop", namespace: "ns-a", severity: "high", workload: "app-a" },
  { incident_type: "rollout_failure", namespace: "ns-b", severity: "critical", workload: "app-b" },
  { incident_type: "high_latency", namespace: "ns-a", severity: "medium", workload: "app-a" },
];

export default function Incidents() {
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [workloads, setWorkloads] = useState([]);
  const [workloadsLoading, setWorkloadsLoading] = useState(true);
  const [workloadsError, setWorkloadsError] = useState("");
  const [attackStatus, setAttackStatus] = useState("");

  useEffect(() => {
    let mounted = true;
    const loadIncidents = async () => {
      try {
        const data = await fetchIncidents();
        if (mounted) {
          setIncidents(data);
          setLoading(false);
        }
      } catch (err) {
        if (mounted) {
          setError(err.message);
          setLoading(false);
        }
      }
    };
    const loadWorkloads = async () => {
      try {
        setWorkloadsError("");
        const data = await fetchDemoWorkloads();
        if (mounted) {
          setWorkloads(data);
          setWorkloadsLoading(false);
        }
      } catch (err) {
        if (mounted) {
          setWorkloadsError(err.message);
          setWorkloadsLoading(false);
        }
      }
    };
    loadIncidents();
    loadWorkloads();
    return () => {
      mounted = false;
    };
  }, []);

  const active = useMemo(
    () => incidents.filter((item) => item.status !== "validated"),
    [incidents]
  );

  const onInject = async (payload) => {
    setLoading(true);
    try {
      await injectDemo(payload);
      const data = await fetchIncidents();
      setIncidents(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const onAttack = async (attackType) => {
    setAttackStatus(`Triggering ${attackType.replace("_", " ")}...`);
    setWorkloadsError("");
    try {
      await triggerDemoAttack({ attack_type: attackType });
      const data = await fetchDemoWorkloads();
      setWorkloads(data);
    } catch (err) {
      setWorkloadsError(err.message);
    } finally {
      setAttackStatus("");
    }
  };

  return (
    <div className="space-y-8">
      <section className="rounded-3xl border border-white/10 bg-white/5 p-8 shadow-glow">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="font-display text-3xl">Active incident response</h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-300">
              Live triage, investigation, and recommendations streamed into a single timeline.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {demoPresets.map((preset) => (
              <button
                key={preset.incident_type}
                onClick={() => onInject(preset)}
                className="rounded-full border border-white/20 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white/80 transition hover:border-amber-400/60 hover:text-white"
              >
                Inject {preset.incident_type.replace("_", " ")}
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="rounded-3xl border border-white/10 bg-white/5 p-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="font-display text-2xl">Demo workloads</h2>
            <p className="mt-2 max-w-2xl text-sm text-slate-300">
              Live health view for the demo namespaces. Attack actions are scoped only to these workloads.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {["crashloop", "rollout_failure", "high_latency"].map((attackType) => (
              <button
                key={attackType}
                onClick={() => onAttack(attackType)}
                className="rounded-full border border-white/20 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white/80 transition hover:border-rose-400/60 hover:text-white"
                disabled={Boolean(attackStatus)}
              >
                Attack {attackType.replace("_", " ")}
              </button>
            ))}
          </div>
        </div>
        {attackStatus && (
          <div className="mt-4 rounded-2xl border border-amber-400/40 bg-amber-500/10 p-4 text-xs text-amber-100">
            {attackStatus}
          </div>
        )}
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {workloadsLoading ? (
            <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-6 text-sm text-slate-200">
              Loading workloads...
            </div>
          ) : workloadsError ? (
            <div className="rounded-2xl border border-red-400/40 bg-red-500/10 p-6 text-sm text-red-200">
              {workloadsError}
            </div>
          ) : workloads.length === 0 ? (
            <div className="rounded-2xl border border-white/10 bg-slate-950/60 p-6 text-sm text-slate-200">
              Demo workloads not detected yet.
            </div>
          ) : (
            workloads.map((workload) => (
              <div
                key={`${workload.namespace}-${workload.workload}`}
                className="rounded-2xl border border-white/10 bg-slate-950/60 p-6"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs uppercase tracking-[0.2em] text-slate-400">
                      {workload.namespace}
                    </div>
                    <h3 className="mt-1 font-display text-lg">{workload.workload}</h3>
                  </div>
                  <div
                    className={`rounded-full px-3 py-1 text-xs uppercase tracking-[0.2em] ${
                      workload.status === "healthy"
                        ? "bg-emerald-500/20 text-emerald-200"
                        : "bg-rose-500/20 text-rose-200"
                    }`}
                  >
                    {workload.status}
                  </div>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-2 text-xs text-slate-300">
                  <div>Desired: {workload.desired_replicas}</div>
                  <div>Ready: {workload.ready_replicas}</div>
                  <div>Available: {workload.available_replicas}</div>
                  <div>Restarts: {workload.restarts}</div>
                </div>
                {workload.message && (
                  <div className="mt-3 rounded-xl border border-white/10 bg-slate-950/80 px-3 py-2 text-xs text-slate-300">
                    {workload.message}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </section>

      {loading ? (
        <div className="rounded-3xl border border-white/10 bg-white/5 p-8">Loading incidents...</div>
      ) : error ? (
        <div className="rounded-3xl border border-red-400/40 bg-red-500/10 p-8 text-red-200">{error}</div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-display text-xl">Active incidents</h2>
              <span className="text-xs uppercase tracking-[0.3em] text-slate-400">
                {active.length} open
              </span>
            </div>
            {active.length === 0 ? (
              <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-slate-200">
                All clear. Inject a demo to simulate a response.
              </div>
            ) : (
              active.map((incident) => (
                <Link
                  key={incident.incident_id}
                  to={`/incidents/${incident.incident_id}`}
                  className="group block rounded-2xl border border-white/10 bg-slate-950/60 p-6 transition hover:border-amber-400/60"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-xs uppercase tracking-[0.2em] text-amber-300">
                        {incident.incident_type}
                      </div>
                      <h3 className="mt-1 font-display text-lg">
                        {incident.summary}
                      </h3>
                      <p className="mt-2 text-xs text-slate-300">
                        Status: {incident.status}
                      </p>
                    </div>
                    <div className="text-right text-xs text-slate-400">
                      Severity: {incident.severity}
                    </div>
                  </div>
                </Link>
              ))
            )}
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
            <Charts incidents={incidents} />
          </div>
        </div>
      )}
    </div>
  );
}
