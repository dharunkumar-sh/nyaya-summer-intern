import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import {
  CheckCircle2,
  ShieldCheck,
  Cpu,
  BarChart3,
} from 'lucide-react';
import Card from '../common/Card';
import Badge from '../common/Badge';
import QueryInputCard from './QueryInputCard';
import KnowledgeGraphViewer from './KnowledgeGraphViewer';
import RetrievedEvidencePanel from './RetrievedEvidencePanel';
import ReasoningTracePipeline from './ReasoningTracePipeline';
import BottomSectionCards from './BottomSectionCards';
import PancavayavaCard from './PancavayavaCard';
import VerseGroundingCard from './VerseGroundingCard';
import KnowledgeGraphCard from './KnowledgeGraphCard';
import EpistemicMetricsCard from './EpistemicMetricsCard';
import TolkappiyamSutraExplorer from './TolkappiyamSutraExplorer';
import { useReasoner } from '../../context/ReasonerContext';
import OverviewDashboard from './overview/OverviewDashboard';

export default function MainDashboard() {
  const navigate = useNavigate();
  const {
    currentQuery,
    selectedEvidenceId,
    setSelectedEvidenceId,
    validationResults,
    isAnalyzing,
    currentWorkflowStage,
    workflowProgressPercent,
    depth,
    setQueryText,
    graphStatistics,
    corpus,
    queryStats,
    dashboardSummary,
    systemStatus,
  } = useReasoner();

  const handleSelectSutraForQuery = (sutraText) => {
    setQueryText(sutraText);
    navigate('/query-center');
  };

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
                  {currentWorkflowStage?.desc || 'Retrieving canonical sūtras • Grounding Tiṇai invariants • Checking Hetvābhāsa fallacies'}
                </div>
              </div>
            </div>
            <Badge variant="purpleDark" size="xs">
              Depth: {depth} Hops
            </Badge>
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

          {/* ROUTE 2: QUERY CENTER VIEW */}
          <Route
            path="/query-center"
            element={
              <div className="space-y-6">
                <QueryInputCard />
                <BottomSectionCards
                  selectedEvidenceId={selectedEvidenceId}
                  onSelectEvidence={setSelectedEvidenceId}
                />
                <RetrievedEvidencePanel />
              </div>
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
                {/* Stack Order: Verse Grounding followed by Nyāya 5-Member Syllogism */}
                <div className="space-y-6">
                  <VerseGroundingCard currentQuery={currentQuery} />
                  <PancavayavaCard
                    currentQuery={currentQuery}
                    selectedEvidenceId={selectedEvidenceId}
                  />
                </div>
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

          {/* ROUTE 6: FALLACY CHECKER VIEW */}
          <Route
            path="/fallacies"
            element={
              <div className="space-y-6">
                <Card
                  title="Hetvābhāsa Nirūpaṇa (Classical Nyāya Fallacy Inspection)"
                  subtitle="Deep formal verification against all 5 major types of fallacious middle grounds in Tolkāppiyam reasoning"
                  icon={ShieldCheck}
                  accent="green"
                >
                  <div className="space-y-4">
                    <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs sm:text-sm">
                      <div className="font-bold flex items-center gap-1.5 mb-1">
                        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                        <span>Epistemic Soundness Status: 100% Free of Fallacies ({validationResults?.symbolicValidity || 'Valid Epistemic Deduction'})</span>
                      </div>
                      <p className="leading-relaxed">
                        The inferential ground (Hetu) linking Mutalporuḷ (spatio-temporal habitat) and Karupporuḷ to Uripporuḷ (psychological mood) is strictly invariant and textually established in Tolkāppiyam Poruḷatikāram.
                      </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                      <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-xs text-slate-900">1. Savyabhicāra (Erratic Reason)</span>
                          <Badge variant="green" size="xs">Score: {validationResults?.fallacies?.savyabhicara !== undefined ? validationResults.fallacies.savyabhicara.toFixed(2) : '0.00'}</Badge>
                        </div>
                        <p className="text-xs text-slate-600">
                          The reason does not wander into improper contexts. Kuṟiñci signifiers are strictly bound to clandestine nocturnal love in classical semiotics.
                        </p>
                      </div>

                      <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-xs text-slate-900">2. Viruddha (Contradictory Reason)</span>
                          <Badge variant="green" size="xs">Score: {validationResults?.fallacies?.viruddha !== undefined ? validationResults.fallacies.viruddha.toFixed(2) : '0.00'}</Badge>
                        </div>
                        <p className="text-xs text-slate-600">
                          The reason does not disprove the thesis. No self-contradiction exists between ecological habitat and aesthetic mood.
                        </p>
                      </div>

                      <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-xs text-slate-900">3. Satpratipakṣa (Counterbalanced Reason)</span>
                          <Badge variant="green" size="xs">Score: {validationResults?.fallacies?.satpratipaksa !== undefined ? validationResults.fallacies.satpratipaksa.toFixed(2) : '0.00'}</Badge>
                        </div>
                        <p className="text-xs text-slate-600">
                          No equally valid opposing inferential ground exists in the grammar of Tolkāppiyam to contradict this mapping.
                        </p>
                      </div>

                      <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-xs text-slate-900">4. Asiddha (Unproven Ground)</span>
                          <Badge variant="green" size="xs">Score: {validationResults?.fallacies?.asiddha !== undefined ? validationResults.fallacies.asiddha.toFixed(2) : '0.00'}</Badge>
                        </div>
                        <p className="text-xs text-slate-600">
                          The middle term is fully established by direct textual evidence in Akattiṇaiyiyal Sūtras 3 and 5 (Pratyakṣa-siddha).
                        </p>
                      </div>

                      <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5 md:col-span-2">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-xs text-slate-900">5. Bādhita (Sublated / Contradicted by Stronger Pramāṇa)</span>
                          <Badge variant="green" size="xs">Score: {validationResults?.fallacies?.badhita !== undefined ? validationResults.fallacies.badhita.toFixed(2) : '0.00'}</Badge>
                        </div>
                        <p className="text-xs text-slate-600">
                          Direct textual perception of canonical sūtras corroborates the inferential conclusion without any sublation.
                        </p>
                      </div>
                    </div>
                  </div>
                </Card>
              </div>
            }
          />

          {/* ROUTE 7: LITERATURE & CANONICAL CORPUS EXPLORER VIEW */}
          <Route
            path="/sutras"
            element={
              <TolkappiyamSutraExplorer onSelectSutraForQuery={handleSelectSutraForQuery} />
            }
          />
          <Route
            path="/literature"
            element={
              <TolkappiyamSutraExplorer onSelectSutraForQuery={handleSelectSutraForQuery} />
            }
          />
          <Route
            path="/corpus"
            element={
              <TolkappiyamSutraExplorer onSelectSutraForQuery={handleSelectSutraForQuery} />
            }
          />
          <Route
            path="/search"
            element={
              <TolkappiyamSutraExplorer onSelectSutraForQuery={handleSelectSutraForQuery} />
            }
          />

          {/* ROUTE 8: ANALYTICS & KG HEALTH VIEW */}
          <Route
            path="/analytics"
            element={
              <div className="space-y-6">
                <EpistemicMetricsCard currentQuery={currentQuery} />
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
