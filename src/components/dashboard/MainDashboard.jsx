import { Routes, Route, Navigate } from 'react-router-dom';
import {
  Cpu,
  BarChart3,
  Sparkles,
} from 'lucide-react';
import Card from '../common/Card';
import QueryInputCard from './QueryInputCard';
import KnowledgeGraphViewer from './KnowledgeGraphViewer';
import RetrievedEvidencePanel from './RetrievedEvidencePanel';
import ReasoningTracePipeline from './ReasoningTracePipeline';
import BottomSectionCards from './BottomSectionCards';
import PancavayavaCard from './PancavayavaCard';
import KnowledgeGraphCard from './KnowledgeGraphCard';
import EpistemicMetricsCard from './EpistemicMetricsCard';
import AnalyticsVisualizations from './AnalyticsVisualizations';
import { useReasoner } from '../../context/ReasonerContext';
import OverviewDashboard from './overview/OverviewDashboard';

function QueryCenterView({ selectedEvidenceId, setSelectedEvidenceId }) {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Query Center Status Indicator */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-white p-3.5 rounded-xl border border-slate-200/80 shadow-2xs">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-purple-50 border border-purple-200 flex items-center justify-center text-purple-600 shadow-2xs">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-900 flex items-center gap-2">
              Query Center
            </h2>
            <p className="text-[11px] text-slate-500">
              Interactive Inquiry Workspace: Formulate queries, inspect retrieved canonical evidence, and review epistemic justifications.
            </p>
          </div>
        </div>
      </div>

      {/* 1. Query / Search Section */}
      <section aria-label="Query and Search Section">
        <QueryInputCard />
      </section>

      {/* 2. Answer / Reasoning Section */}
      <section aria-label="Answer and Reasoning Section">
        <BottomSectionCards
          selectedEvidenceId={selectedEvidenceId}
          onSelectEvidence={setSelectedEvidenceId}
        />
      </section>

      {/* 3. Evidence Section */}
      <section aria-label="Retrieved Evidence Section">
        <RetrievedEvidencePanel />
      </section>
    </div>
  );
}

export default function MainDashboard() {
  const {
    currentQuery,
    selectedEvidenceId,
    setSelectedEvidenceId,
    isAnalyzing,
    currentWorkflowStage,
    workflowProgressPercent,
    graphStatistics,
    corpus,
    queryStats,
    dashboardSummary,
    systemStatus,
  } = useReasoner();

  return (
    <main className="flex-1 min-w-0 bg-[#f8fafc] min-h-[calc(100vh-4rem)] lg:ml-80 pt-6 pb-16 px-4 sm:px-6 lg:px-8 xl:px-10 transition-all">
      <div className="max-w-[1600px] mx-auto w-full space-y-6">

        {/* Subtle Loading State Indicator Banner while processing */}
        {isAnalyzing && (
          <div className="mb-6 p-4 rounded-xl bg-purple-950/80 border border-purple-500/50 text-purple-100 flex items-center justify-between gap-4 animate-pulse shadow-md">
            <div className="flex items-center gap-3">
              <Cpu className="w-5 h-5 text-purple-300 animate-spin" />
              <div>
                <div className="font-semibold text-sm">
                  {currentWorkflowStage?.name || 'Executing Tolkāppiyam Neuro-Symbolic Reasoner...'} ({workflowProgressPercent}%)
                </div>
                <div className="text-xs text-purple-300/80">
                  Epistemic validation active across 24 akam canons & 5-stage Pañcāvayava inference.
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold bg-purple-900/60 px-2.5 py-1 rounded-lg border border-purple-500/30">
                STAGE {currentWorkflowStage?.id || '...'}/7
              </span>
            </div>
          </div>
        )}

        {/* REACT ROUTER SEPARATE ROUTES */}
        <Routes>
          {/* ROUTE 1: OVERVIEW DASHBOARD - DEDICATED DOMAIN COMMAND COCKPIT */}
          <Route
            path="/"
            element={<OverviewDashboard />}
          />
          <Route path="/dashboard" element={<Navigate to="/" replace />} />

          {/* ROUTE 2: QUERY CENTER VIEW (Permanent Stack View) */}
          <Route
            path="/query-center"
            element={
              <QueryCenterView
                selectedEvidenceId={selectedEvidenceId}
                setSelectedEvidenceId={setSelectedEvidenceId}
              />
            }
          />

          {/* ROUTE 3: KNOWLEDGE GRAPH VIEW */}
          <Route
            path="/knowledge-graph"
            element={
              <div className="space-y-6">
                <KnowledgeGraphViewer height="h-[680px] lg:h-[750px]" />
                <KnowledgeGraphCard currentQuery={currentQuery} />
              </div>
            }
          />

          {/* ROUTE 4: NYĀYA REASONING TRACE VIEW */}
          <Route
            path="/reasoning"
            element={
              <div className="space-y-6">
                <ReasoningTracePipeline currentQuery={currentQuery} />
                <PancavayavaCard
                  currentQuery={currentQuery}
                  selectedEvidenceId={selectedEvidenceId}
                />
                <BottomSectionCards
                  selectedEvidenceId={selectedEvidenceId}
                  onSelectEvidence={setSelectedEvidenceId}
                  showJustification={false}
                />
              </div>
            }
          />

          {/* ROUTE 5: RETRIEVED EVIDENCE VIEW */}
          <Route
            path="/evidence"
            element={
              <div className="space-y-6">
                <RetrievedEvidencePanel />
                <BottomSectionCards
                  selectedEvidenceId={selectedEvidenceId}
                  onSelectEvidence={setSelectedEvidenceId}
                />
              </div>
            }
          />

          {/* Formal verification route disabled. */}

          {/* ROUTE 7: ANALYTICS & KG HEALTH VIEW */}
          <Route
            path="/analytics"
            element={
              <div className="space-y-6">
                <EpistemicMetricsCard currentQuery={currentQuery} />
                <AnalyticsVisualizations />
                <Card
                  title="Tolkāppiyam Epistemic Benchmark & Latency Analytics"
                  subtitle="Quantitative metrics of the Neuro-Symbolic reasoner operating over Tolkāppiyam"
                  icon={BarChart3}
                  accent="purple"
                >
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                    <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                      <span className="text-slate-500 block text-xs">Knowledge Graph Density</span>
                      <span className="font-mono text-xl font-bold text-slate-900 mt-1 block">
                        {graphStatistics?.total_edges !== undefined
                          ? `${graphStatistics.total_edges.toLocaleString()} Relations`
                          : (systemStatus?.services?.knowledge_graph?.total_edges !== undefined
                            ? `${systemStatus.services.knowledge_graph.total_edges} Relations`
                            : "--")}
                      </span>
                      <span className="text-[11px] text-purple-700 mt-1 block">
                        {graphStatistics?.total_nodes !== undefined
                          ? `${graphStatistics.total_nodes.toLocaleString()} Named Entities`
                          : (systemStatus?.services?.knowledge_graph?.total_nodes !== undefined
                            ? `${systemStatus.services.knowledge_graph.total_nodes} Named Entities`
                            : "--")}
                      </span>
                    </div>
                    <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                      <span className="text-slate-500 block text-xs">Average Inference Latency</span>
                      <span className="font-mono text-xl font-bold text-slate-900 mt-1 block">
                        {queryStats?.latencyMs
                          ? `${queryStats.latencyMs} ms`
                          : (dashboardSummary?.search_and_rag?.average_inference_ms
                            ? `${dashboardSummary.search_and_rag.average_inference_ms} ms`
                            : (systemStatus?.services?.application?.latency_ms
                              ? `${systemStatus.services.application.latency_ms} ms`
                              : "--"))}
                      </span>
                      <span className="text-[11px] text-emerald-700 mt-1 block">
                        {queryStats?.latencyMs ? "Active Query Proof Latency" : "Real-time Nyāya Proof"}
                      </span>
                    </div>
                    <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                      <span className="text-slate-500 block text-xs">Total Indexed Passages</span>
                      <span className="font-mono text-xl font-bold text-slate-900 mt-1 block">
                        {corpus?.total_sutras_canonical || corpus?.canonical_sutras
                          ? `${(corpus.total_sutras_canonical || corpus.canonical_sutras).toLocaleString()} Sūtras`
                          : "--"}
                      </span>
                      <span className="text-[11px] text-blue-700 mt-1 block">
                        {corpus?.books_count || 3} Books ({corpus?.indexed_sutras_active ?? 0} Active Indexed)
                      </span>
                    </div>
                  </div>
                </Card>
              </div>
            }
          />

          {/* CATCH ALL */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </main>
  );
}
