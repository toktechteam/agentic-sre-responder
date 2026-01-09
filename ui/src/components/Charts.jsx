import React, { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
} from "recharts";

const palette = ["#f59e0b", "#14b8a6", "#38bdf8", "#f97316", "#e11d48"];

function getNamespace(incident) {
  const raw = incident.raw_alert || {};
  return raw.labels?.namespace || "default";
}

function avgDuration(incidents, field) {
  if (!incidents.length) return 0;
  const values = incidents.map((item) => item[field]).filter((v) => v != null);
  if (!values.length) return 0;
  const total = values.reduce((sum, val) => sum + val, 0);
  return Math.round(total / values.length);
}

export default function Charts({ incidents }) {
  const typeData = useMemo(() => {
    const counts = incidents.reduce((acc, item) => {
      acc[item.incident_type] = (acc[item.incident_type] || 0) + 1;
      return acc;
    }, {});
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  }, [incidents]);

  const durationData = useMemo(() => {
    return [
      { name: "triage", value: avgDuration(incidents, "time_to_triage_ms") },
      { name: "investigate", value: avgDuration(incidents, "time_to_investigate_ms") },
      { name: "recommend", value: avgDuration(incidents, "time_to_recommend_ms") },
    ];
  }, [incidents]);

  const namespaceData = useMemo(() => {
    const counts = incidents.reduce((acc, item) => {
      const ns = getNamespace(item);
      acc[ns] = (acc[ns] || 0) + 1;
      return acc;
    }, {});
    return Object.entries(counts)
      .map(([name, value]) => ({ name, value }))
      .slice(0, 5);
  }, [incidents]);

  return (
    <div className="space-y-6">
      <div>
        <h3 className="font-display text-lg">Incident types</h3>
        <div className="mt-4 h-40">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={typeData} dataKey="value" nameKey="name" innerRadius={35} outerRadius={60}>
                {typeData.map((entry, index) => (
                  <Cell key={`cell-${entry.name}`} fill={palette[index % palette.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div>
        <h3 className="font-display text-lg">Avg stage duration (ms)</h3>
        <div className="mt-4 h-40">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={durationData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="name" stroke="#94a3b8" fontSize={10} />
              <YAxis stroke="#94a3b8" fontSize={10} />
              <Tooltip />
              <Bar dataKey="value" fill="#38bdf8" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div>
        <h3 className="font-display text-lg">Top namespaces</h3>
        <div className="mt-4 space-y-2 text-xs text-slate-300">
          {namespaceData.map((item, idx) => (
            <div key={item.name} className="flex items-center justify-between">
              <span>{item.name}</span>
              <span className="text-slate-200">{item.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
