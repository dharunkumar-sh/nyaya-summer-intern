import { useState } from 'react';
import { Menu, X } from 'lucide-react';
import { useReasoner } from '../../context/ReasonerContext';

export default function Header({
  sidebarOpen,
  setSidebarOpen,
  activeCorpus = null,
}) {
  const reasoner = useReasoner();
  const {
    corpus,
    systemStatus,
    isLoadingSystemStatus,
    systemStatusError,
    refetchSystemStatus,
    isBackendOnline,
    isNeo4jOnline,
    isSystemDegraded,
  } = reasoner || {};
  const currentCorpus = corpus || activeCorpus;

  const [showStatusMenu, setShowStatusMenu] = useState(false);

  // Status badge styling
  const statusColor = !isBackendOnline || systemStatusError
    ? "bg-rose-500"
    : isSystemDegraded
    ? "bg-amber-400"
    : "bg-emerald-400";

  const statusLabel = isLoadingSystemStatus
    ? "Checking..."
    : !isBackendOnline || systemStatusError
    ? "Backend Offline"
    : isSystemDegraded
    ? (isNeo4jOnline ? "Degraded" : "Neo4j Offline")
    : "All Systems Operational";

  return (
    <header className="sticky top-0 z-40 w-full bg-[#0a1020] border-b border-slate-800/90 text-white shadow-md select-none">
      <div className="flex items-center justify-between h-16 px-3 sm:px-5 lg:px-6">
        {/* Left: Mobile Toggle + Lotus Logo + Title & Subtitle */}
        <div className="flex items-center gap-2.5 sm:gap-3.5 min-w-0">
          <button
            type="button"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="lg:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors focus:outline-none"
            aria-label="Toggle Navigation"
          >
            {sidebarOpen ? (
              <X className="w-5 h-5" />
            ) : (
              <Menu className="w-5 h-5" />
            )}
          </button>

          {/* Application Logo */}
          <div className="flex items-center gap-3 min-w-0">
            <div className="p-1 rounded-xl bg-slate-900/90 border border-purple-500/30 shadow-inner flex items-center justify-center shrink-0">
              <img
                src="/logo.png"
                alt="Application Logo"
                className="w-7 h-7 sm:w-8 sm:h-8 object-contain drop-shadow-[0_1px_4px_rgba(168,85,247,0.4)]"
              />
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h1 className="text-sm sm:text-base md:text-lg font-bold text-slate-100 tracking-tight leading-tight">
                  Tol<span className="text-purple-400">Nyāya</span>
                </h1>
                <span className="hidden xs:inline-block px-1.5 py-0.5 rounded text-[10px] font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                  v2.6
                </span>
              </div>
              <p className="text-[10px] sm:text-[11px] text-slate-400 font-medium tracking-wide truncate">
                Neuro-Symbolic Reasoner for Classical Tamil Knowledge
              </p>
            </div>
          </div>
        </div>

        {/* Right: Real-Time System Health Pill & Corpus Status */}
        <div className="flex items-center gap-2 sm:gap-3 shrink-0 relative">
          {/* Dynamic Unified System Status Pill with Dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowStatusMenu(!showStatusMenu)}
              className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-slate-900/90 hover:bg-slate-850 border border-slate-800 text-xs text-slate-300 transition-colors cursor-pointer"
              title="Click to view real-time service connectivity diagnostics"
            >
              <span className={`w-2 h-2 rounded-full ${statusColor} ${isLoadingSystemStatus ? 'animate-pulse' : (isBackendOnline ? 'animate-pulse' : '')}`} />
              <span className="hidden sm:inline font-medium text-[11px] text-slate-300">
                {statusLabel}
              </span>
            </button>

            {/* Dropdown Diagnostics Card */}
            {showStatusMenu && (
              <div
                className="absolute right-0 mt-2 w-72 rounded-xl bg-slate-900 border border-slate-800 shadow-2xl p-3 z-50 text-xs animate-in fade-in slide-in-from-top-2 duration-150"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                  <span className="font-semibold text-slate-200">System Diagnostics</span>
                  <button
                    type="button"
                    onClick={() => {
                      if (refetchSystemStatus) refetchSystemStatus();
                    }}
                    disabled={isLoadingSystemStatus}
                    className="text-[10px] text-purple-400 hover:text-purple-300 transition-colors font-mono cursor-pointer"
                  >
                    {isLoadingSystemStatus ? "Pinging..." : "↻ Re-ping"}
                  </button>
                </div>

                <div className="mt-2.5 space-y-2">
                  {/* Service 1: Flask Application */}
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-slate-400">Flask Core App:</span>
                    <span className="font-mono flex items-center gap-1.5">
                      <span className={`w-1.5 h-1.5 rounded-full ${isBackendOnline ? 'bg-emerald-400' : 'bg-rose-500'}`} />
                      <span className={isBackendOnline ? 'text-emerald-400' : 'text-rose-400'}>
                        {isBackendOnline ? `${systemStatus?.services?.application?.latency_ms ?? 0}ms` : 'Offline'}
                      </span>
                    </span>
                  </div>

                  {/* Service 2: Neo4j Aura */}
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-slate-400">Neo4j Aura Graph:</span>
                    <span className="font-mono flex items-center gap-1.5">
                      <span className={`w-1.5 h-1.5 rounded-full ${isNeo4jOnline ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                      <span className={isNeo4jOnline ? 'text-emerald-400' : 'text-amber-400'}>
                        {isNeo4jOnline
                          ? `${systemStatus?.services?.database?.latency_ms ?? 0}ms`
                          : 'Disconnected'}
                      </span>
                    </span>
                  </div>

                  {/* Service 3: Hybrid RAG Engine */}
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-slate-400">RAG Index (FAISS):</span>
                    <span className="font-mono flex items-center gap-1.5">
                      <span className={`w-1.5 h-1.5 rounded-full ${systemStatus?.services?.retrieval?.healthy ? 'bg-emerald-400' : 'bg-slate-500'}`} />
                      <span className="text-slate-300">
                        {systemStatus?.services?.retrieval?.faiss_indexed_chunks ?? 0} Chunks
                      </span>
                    </span>
                  </div>

                  {/* Service 4: Hierarchical Knowledge Graph */}
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-slate-400">Knowledge Graph:</span>
                    <span className="font-mono flex items-center gap-1.5">
                      <span className={`w-1.5 h-1.5 rounded-full ${systemStatus?.services?.knowledge_graph?.healthy ? 'bg-emerald-400' : 'bg-slate-500'}`} />
                      <span className="text-slate-300">
                        {systemStatus?.services?.knowledge_graph?.total_nodes ?? 0} Nodes
                      </span>
                    </span>
                  </div>
                </div>

                <div className="mt-2.5 pt-2 border-t border-slate-800 text-[10px] text-slate-500 flex justify-between">
                  <span>Zero Credential Exposure</span>
                  <span className="text-purple-400/80 font-mono">Status: {systemStatus?.status || 'Unknown'}</span>
                </div>
              </div>
            )}
          </div>

          {currentCorpus && (
            <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 text-xs text-slate-300">
              <span className="text-slate-400">Corpus:</span>
              <span className="font-semibold text-purple-300 truncate max-w-32.5 sm:max-w-none">
                {currentCorpus.name}
              </span>
              <span className="text-slate-600">•</span>
              <span className="font-mono text-slate-400 text-[11px]">
                {currentCorpus.formattedCount}
              </span>
            </div>
          )}

        </div>
      </div>
    </header>
  );
}
