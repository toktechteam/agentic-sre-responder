import React from "react";
import { Link, Route, Routes } from "react-router-dom";
import Incidents from "./pages/Incidents.jsx";
import IncidentDetail from "./pages/IncidentDetail.jsx";

export default function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 text-white">
      <div className="relative overflow-hidden">
        <div className="absolute -top-16 -right-20 h-64 w-64 rounded-full bg-amber-400/20 blur-3xl" />
        <div className="absolute -bottom-24 -left-10 h-72 w-72 rounded-full bg-teal-400/20 blur-3xl" />
        <header className="relative z-10 border-b border-white/10">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
            <Link to="/" className="font-display text-2xl tracking-tight">
              agentic-sre-responder
            </Link>
            <div className="text-sm text-slate-300">MTTR Reduction Console</div>
          </div>
        </header>
        <main className="relative z-10 mx-auto max-w-6xl px-6 py-8">
          <Routes>
            <Route path="/" element={<Incidents />} />
            <Route path="/incidents/:incidentId" element={<IncidentDetail />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
