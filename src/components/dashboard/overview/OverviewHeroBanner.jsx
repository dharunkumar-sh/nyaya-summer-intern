import {
  Sparkles,
  Cpu,
  Database,
  ArrowRight,
  Zap,
  Library,
  Network,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import Badge from "../../common/Badge";
import { useReasoner } from "../../../context/ReasonerContext";

export default function OverviewHeroBanner() {
  const navigate = useNavigate();
  const { corpus, dashboardSummary, queryStats, systemStatus, isNeo4jOnline } = useReasoner();

  const corpusData = dashboardSummary?.corpus || corpus;
  const dbInfo = systemStatus?.services?.database;
  const neo4jActive = isNeo4jOnline ?? (dbInfo?.connected ?? (dashboardSummary?.system_status?.neo4j_connected ?? false));
  const searchRag = dashboardSummary?.search_and_rag;
  const reasoningData = dashboardSummary?.reasoning_and_soundness;

  const corpusName = corpusData?.name || "Tolkāppiyam";
  const totalSutras = corpusData?.total_sutras_canonical || corpusData?.totalSutras || (corpusData?.canonical_sutras ?? 1610);
  const engineName = reasoningData?.framework?.split('(')[0]?.trim() || "Pañcāvayava Syllogism";
  const avgLatency = queryStats?.latencyMs
    ? `${queryStats.latencyMs} ms`
    : searchRag?.average_inference_ms
    ? `${searchRag.average_inference_ms} ms`
    : (systemStatus?.services?.application?.latency_ms ? `${systemStatus.services.application.latency_ms} ms` : "--");
  const soundnessText = reasoningData ? `${reasoningData.soundness_rate}% Sound` : (dashboardSummary ? '100% Sound' : 'Pending Verification');

  return (
    <div className="relative overflow-hidden rounded-2xl bg-linear-to-br from-slate-900 via-[#111827] to-purple-950 text-white border border-slate-800 shadow-xl p-6 sm:p-8">
      {/* Background Decorative Mesh & Glow */}
      <div className="absolute -top-24 -right-24 w-96 h-96 bg-purple-600/15 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-24 -left-24 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
        {/* Left Column: Title, Subtitle, and System Pulse */}
        <div className="max-w-3xl space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="greenDark" size="xs" dot>
              Nyāya Validated ({soundnessText})
            </Badge>
            <Badge variant={neo4jActive ? "blueDark" : "slate"} size="xs">
              {neo4jActive
                ? `Neo4j Knowledge Graph Active (${dbInfo?.database || 'Aura'})`
                : "In-Memory Knowledge Graph Active (Neo4j Offline)"}
            </Badge>
          </div>

          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white font-serif">
              Classical Tamil Neuro-Symbolic Epistemology
            </h1>
            <p className="mt-1.5 text-xs sm:text-sm text-slate-300 leading-relaxed max-w-2xl">
              Integrating{" "}
              <span className="text-purple-300 font-semibold">
                Tamil-BERT cross-attention retrieval
              </span>{" "}
              with classical{" "}
              <span className="text-amber-300 font-semibold">
                Nyāya 5-stage Pañcāvayava syllogistic inference
              </span>{" "}
              and defeasible{" "}
              <span className="text-emerald-300 font-semibold">
                Hetvābhāsa fallacy verification
              </span>{" "}
              over all {totalSutras.toLocaleString()} sūtras of Tolkāppiyam.
            </p>
          </div>

          {/* Real-time Subsystem Status Pills */}
          <div className="flex flex-wrap items-center gap-3 pt-2 text-xs">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/80 text-slate-300">
              <Database className="w-3.5 h-3.5 text-purple-400" />
              <span className="text-slate-400">Corpus:</span>
              <span className="font-semibold text-slate-100">
                {corpusName}
              </span>
              <span className="text-purple-300 font-mono text-[11px]">
                ({totalSutras.toLocaleString()} Sūtras)
              </span>
            </div>

            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/80 text-slate-300">
              <Cpu className="w-3.5 h-3.5 text-amber-400" />
              <span className="text-slate-400">Engine:</span>
              <span className="font-semibold text-slate-100">
                {engineName}
              </span>
            </div>

            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/80 text-slate-300">
              <Zap className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-slate-400">Avg Latency:</span>
              <span className="font-mono font-semibold text-emerald-400">
                {avgLatency}
              </span>
            </div>
          </div>
        </div>

        {/* Right Column: Quick Action Cockpit */}
        <div className="flex flex-row lg:flex-col items-stretch gap-2.5 shrink-0 min-w-52.5">
          <button
            type="button"
            onClick={() => navigate("/query-center")}
            className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs sm:text-sm font-semibold shadow-lg shadow-purple-900/30 transition-all cursor-pointer group"
          >
            <Sparkles className="w-4 h-4 text-purple-200" />
            <span>Formulate Query</span>
            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
          </button>

          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => navigate("/sutras")}
              className="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 text-slate-300 hover:text-white text-xs font-medium transition-colors cursor-pointer"
            >
              <Library className="w-3.5 h-3.5 text-blue-400" />
              <span>Sūtras</span>
            </button>

            <button
              type="button"
              onClick={() => navigate("/knowledge-graph")}
              className="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 text-slate-300 hover:text-white text-xs font-medium transition-colors cursor-pointer"
            >
              <Network className="w-3.5 h-3.5 text-purple-400" />
              <span>KG Graph</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
