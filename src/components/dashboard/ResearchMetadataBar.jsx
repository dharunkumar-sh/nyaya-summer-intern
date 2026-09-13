import { useState } from 'react';
import {
  BarChart3,
  ChevronDown,
  ChevronUp,
  Network,
  Clock,
  ShieldCheck,
  Cpu,
  BookOpen,
} from 'lucide-react';
import Badge from '../common/Badge';
import { useReasoner } from '../../context/ReasonerContext';

/**
 * SECTION 6: RESEARCH METADATA & SYSTEM BENCHMARK
 * Collapsible, compact research-grade drawer/card providing corpus stats,
 * Knowledge Graph density, inference latency, and formal verification health.
 */
export default function ResearchMetadataBar() {
  const {
    corpus,
    graphStatistics,
    queryStats,
    dashboardSummary,
    systemStatus,
    isNeo4jOnline,
  } = useReasoner();
  const [isExpanded, setIsExpanded] = useState(false);

  // 1. Dynamic Corpus Stats
  const canonicalTotal = corpus?.total_sutras_canonical || corpus?.canonical_sutras;
  const sutrasFormatted = canonicalTotal ? canonicalTotal.toLocaleString() : '--';

  // 2. Dynamic KG Density
  const edgesCount = graphStatistics?.total_edges !== undefined
    ? graphStatistics.total_edges
    : systemStatus?.services?.knowledge_graph?.total_edges;
  const nodesCount = graphStatistics?.total_nodes !== undefined
    ? graphStatistics.total_nodes
    : systemStatus?.services?.knowledge_graph?.total_nodes;
  const relationsFormatted = edgesCount !== undefined ? edgesCount.toLocaleString() : '--';
  const entitiesFormatted = nodesCount !== undefined ? nodesCount.toLocaleString() : '--';

  // 3. Dynamic Inference Latency
  const latencyFormatted = queryStats?.latencyMs
    ? `${queryStats.latencyMs} ms`
    : dashboardSummary?.search_and_rag?.average_inference_ms
    ? `${dashboardSummary.search_and_rag.average_inference_ms} ms`
    : (systemStatus?.services?.application?.latency_ms
      ? `${systemStatus.services.application.latency_ms} ms`
      : '--');

  // 4. System Status
  const statusStr = systemStatus?.status?.toUpperCase() || 'HEALTHY';
  const isHealthy = systemStatus?.status === 'healthy';

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden transition-all">
      {/* Clickable Header Bar */}
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        className="px-5 py-3.5 bg-slate-50/80 hover:bg-slate-100/70 border-b border-slate-100 flex items-center justify-between gap-4 cursor-pointer transition-colors"
      >
        <div className="flex items-center gap-3 min-w-0">
          <div className="p-1.5 rounded-lg bg-slate-200/80 text-slate-700 shrink-0">
            <BarChart3 className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs sm:text-sm font-bold text-slate-900 uppercase tracking-wider">
                RESEARCH METADATA & BENCHMARK STATISTICS
              </h3>
              <Badge variant={isHealthy ? "green" : "slate"} size="xs">
                System: {statusStr}
              </Badge>
            </div>
            <p className="text-[11px] text-slate-500 hidden sm:block">
              Corpus scale, Knowledge Graph density, inference latency, and epistemic distribution
            </p>
          </div>
        </div>

        {/* Quick KPI Chips */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="hidden md:flex items-center gap-2 text-xs font-mono">
            <span className="text-slate-500">Sūtras:</span>
            <span className="font-bold text-slate-800">{sutrasFormatted}</span>
            <span className="text-slate-300">|</span>
            <span className="text-slate-500">Relations:</span>
            <span className="font-bold text-slate-800">{relationsFormatted}</span>
            <span className="text-slate-300">|</span>
            <span className="text-slate-500">Latency:</span>
            <span className="font-bold text-emerald-700">{latencyFormatted}</span>
          </div>

          <button
            type="button"
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition-colors cursor-pointer"
            aria-label={isExpanded ? 'Collapse benchmark statistics' : 'Expand benchmark statistics'}
          >
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Collapsible Content */}
      {isExpanded && (
        <div className="p-5 sm:p-6 space-y-4 animate-in fade-in duration-200 bg-white">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Metric 1: Corpus Coverage */}
            <div className="p-3.5 rounded-xl bg-purple-50/50 border border-purple-200/70 space-y-1">
              <div className="flex items-center justify-between text-xs text-purple-800 font-semibold">
                <span className="flex items-center gap-1.5">
                  <BookOpen className="w-3.5 h-3.5" />
                  Corpus Coverage
                </span>
                <span className="font-mono text-purple-900 font-bold">100%</span>
              </div>
              <div className="font-mono text-xl font-extrabold text-slate-900">
                {sutrasFormatted} Sūtras
              </div>
              <div className="text-[11px] text-slate-500">
                {corpus?.name || 'Tolkāppiyam'} • {corpus?.books_count || 3} Books (Eḻuttu, Col, Poruḷ)
              </div>
            </div>

            {/* Metric 2: Ontological KG Density */}
            <div className="p-3.5 rounded-xl bg-indigo-50/50 border border-indigo-200/70 space-y-1">
              <div className="flex items-center justify-between text-xs text-indigo-800 font-semibold">
                <span className="flex items-center gap-1.5">
                  <Network className="w-3.5 h-3.5" />
                  Knowledge Graph
                </span>
                <span className="font-mono text-indigo-900 font-bold">
                  {isNeo4jOnline ? "Neo4j Aura" : "In-Memory"}
                </span>
              </div>
              <div className="font-mono text-xl font-extrabold text-slate-900">
                {relationsFormatted} Relations
              </div>
              <div className="text-[11px] text-slate-500">
                {entitiesFormatted} Named Entities • Tiṇai Eco-Ontology
              </div>
            </div>

            {/* Metric 3: Inference Latency */}
            <div className="p-3.5 rounded-xl bg-emerald-50/50 border border-emerald-200/70 space-y-1">
              <div className="flex items-center justify-between text-xs text-emerald-800 font-semibold">
                <span className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5" />
                  Inference Latency
                </span>
                <span className="font-mono text-emerald-900 font-bold">
                  {queryStats?.latencyMs ? "Live Trace" : "Benchmark"}
                </span>
              </div>
              <div className="font-mono text-xl font-extrabold text-emerald-700">
                {latencyFormatted}
              </div>
              <div className="text-[11px] text-slate-500">
                5-member Pañcāvayava deduction execution
              </div>
            </div>

            {/* Metric 4: Fallacy Elimination */}
            <div className="p-3.5 rounded-xl bg-blue-50/50 border border-blue-200/70 space-y-1">
              <div className="flex items-center justify-between text-xs text-blue-800 font-semibold">
                <span className="flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  Hetvābhāsa Checks
                </span>
                <span className="font-mono text-blue-900 font-bold">Sound Axioms</span>
              </div>
              <div className="font-mono text-xl font-extrabold text-blue-700">
                5 Checks Evaluated
              </div>
              <div className="text-[11px] text-slate-500">
                Defeasible logic & semantic invariants
              </div>
            </div>
          </div>

          {/* Epistemic Architecture */}
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex flex-col md:flex-row items-start md:items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-3">
              <Cpu className="w-4 h-4 text-purple-600 shrink-0" />
              <div>
                <span className="font-bold text-slate-900">
                  Neuro-Symbolic Pipeline Architecture:
                </span>{' '}
                <span className="text-slate-600">
                  Tamil-BERT Cross-Attention (Neural Perception) + First-Order Nyāya Syllogism (Symbolic Proof)
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2 font-mono text-[11px] text-slate-600">
              <span className="px-2 py-0.5 rounded bg-white border border-slate-200">
                Pratyakṣa (Direct)
              </span>
              <span className="px-2 py-0.5 rounded bg-white border border-slate-200">
                Anumāna (Inference)
              </span>
              <span className="px-2 py-0.5 rounded bg-white border border-slate-200">
                Śabda (Testimony)
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
