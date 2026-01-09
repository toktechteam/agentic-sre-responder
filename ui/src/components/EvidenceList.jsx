import React from "react";

export default function EvidenceList({ evidence }) {
  const items = evidence || [];
  const grouped = items.reduce((acc, item) => {
    const key = item.source || "unknown";
    if (!acc[key]) acc[key] = [];
    acc[key].push(item);
    return acc;
  }, {});
  const sources = Object.keys(grouped);

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
      <h3 className="font-display text-lg">Evidence stream</h3>
      {sources.length === 0 ? (
        <div className="mt-4 text-sm text-slate-300">No evidence collected yet.</div>
      ) : (
        <div className="mt-4 space-y-6">
          {sources.map((source) => (
            <div key={source} className="space-y-3">
              <div className="text-xs uppercase tracking-[0.3em] text-amber-300">{source}</div>
              {grouped[source].map((item, idx) => (
                <div
                  key={`${source}-${idx}`}
                  className="rounded-xl border border-white/10 bg-slate-950/60 px-4 py-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400">{item.severity}</span>
                  </div>
                  <p className="mt-2 text-sm text-slate-200">{item.detail}</p>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
