import React from "react";

export default function Recommendations({ hypotheses, actions }) {
  const safeHypotheses = hypotheses || [];
  const safeActions = actions || [];
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
      <h3 className="font-display text-lg">Recommendations</h3>
      <div className="mt-4 space-y-4">
        <div>
          <div className="text-xs uppercase tracking-[0.3em] text-slate-400">Root cause hypotheses</div>
          <ul className="mt-2 space-y-2 text-sm text-slate-200">
            {safeHypotheses.length === 0 ? (
              <li>No hypotheses generated.</li>
            ) : (
              safeHypotheses.map((item, idx) => (
                <li key={idx} className="rounded-lg bg-slate-950/60 px-3 py-2">
                  {item.hypothesis} ({Math.round(item.confidence * 100)}%)
                </li>
              ))
            )}
          </ul>
        </div>
        <div>
          <div className="text-xs uppercase tracking-[0.3em] text-slate-400">Recommended actions</div>
          <ul className="mt-2 space-y-2 text-sm text-slate-200">
            {safeActions.length === 0 ? (
              <li>No recommendations yet.</li>
            ) : (
              safeActions.map((item, idx) => (
                <li key={idx} className="rounded-lg border border-white/10 bg-slate-950/60 px-3 py-2">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span>Risk: {item.risk}</span>
                    <span>Confidence: {Math.round(item.confidence * 100)}%</span>
                  </div>
                  <p className="mt-1 text-sm text-slate-200">{item.action}</p>
                </li>
              ))
            )}
          </ul>
        </div>
      </div>
    </div>
  );
}
