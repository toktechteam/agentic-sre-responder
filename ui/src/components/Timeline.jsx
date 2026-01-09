import React from "react";

function formatDuration(ms) {
  if (!ms) return "-";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export default function Timeline({ timeline, stageTimings }) {
  const durations = stageTimings.map((stage) => stage.duration_ms || 0);
  const maxDuration = Math.max(1, ...durations);

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-6">
      <h3 className="font-display text-lg">Incident timeline</h3>
      <div className="mt-4 grid gap-3">
        {timeline.map((event, idx) => (
          <div
            key={`${event.stage}-${idx}`}
            className="flex items-center justify-between rounded-xl border border-white/10 bg-slate-950/60 px-4 py-3"
          >
            <div>
              <div className="text-xs uppercase tracking-[0.3em] text-amber-300">
                {event.stage}
              </div>
              <div className="text-sm text-slate-200">{event.status}</div>
            </div>
            <div className="text-xs text-slate-400">
              {new Date(event.timestamp).toLocaleTimeString()}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-6 space-y-3 text-xs text-slate-300">
        {stageTimings.map((stage) => {
          const duration = stage.duration_ms || 0;
          const width = Math.max(4, Math.round((duration / maxDuration) * 100));
          return (
            <div key={stage.stage} className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="uppercase tracking-[0.2em]">{stage.stage}</span>
                <span className="text-slate-200">{formatDuration(stage.duration_ms)}</span>
              </div>
              <div className="h-2 rounded-full bg-white/10">
                <div
                  className="h-2 rounded-full bg-amber-400/80"
                  style={{ width: `${width}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
