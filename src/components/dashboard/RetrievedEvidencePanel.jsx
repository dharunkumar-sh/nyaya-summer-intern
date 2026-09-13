import { useState } from 'react';
import {
  BookOpen,
  AlertTriangle,
  Network,
  BarChart2,
  ChevronDown,
  ChevronUp,
  Compass,
  CheckCircle2,
} from 'lucide-react';
import Badge from '../common/Badge';
import Button from '../common/Button';
import { useReasoner } from '../../context/ReasonerContext';

export default function RetrievedEvidencePanel({ gridLayout = false }) {
  const {
    evidenceRecords,
    selectedEvidenceId,
    setSelectedEvidenceId,
    setSelectedGraphNodeId,
    isAnalyzing,
    queryStatus,
    insufficientEvidence,
    loadBenchmarkEvidence,
    queryStats,
    topK,
    searchMode,
  } = useReasoner();

  const [expandedScoresCardId, setExpandedScoresCardId] = useState(null);

  // Badge variant mapping for evidence categories
  const getBadgeClass = (variant) => {
    switch (variant) {
      case 'purple':
        return 'bg-purple-50 text-purple-700 border-purple-200/90';
      case 'blue':
        return 'bg-blue-50 text-blue-700 border-blue-200/90';
      case 'emerald':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200/90';
      case 'orange':
        return 'bg-amber-50 text-amber-700 border-amber-200/90';
      case 'indigo':
        return 'bg-indigo-50 text-indigo-700 border-indigo-200/90';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  const selectedEvidence =
    evidenceRecords.find((e) => e.id === selectedEvidenceId || e.passageId === selectedEvidenceId) || evidenceRecords[0];

  const handleSelectEvidence = (item) => {
    if (!item) return;
    const targetId = item.passageId || item.id;
    if (setSelectedEvidenceId) {
      setSelectedEvidenceId(item.id);
    }
    if (setSelectedGraphNodeId) {
      setSelectedGraphNodeId(targetId);
    }
  };

  const handleConceptTagClick = (e, conceptId) => {
    e.stopPropagation();
    if (setSelectedGraphNodeId && conceptId) {
      setSelectedGraphNodeId(conceptId);
    }
  };

  const toggleScoreBreakdown = (e, id) => {
    e.stopPropagation();
    setExpandedScoresCardId((prev) => (prev === id ? null : id));
  };

  const formatRetrievalMethod = (method) => {
    if (!method) return 'Hybrid';
    const lower = String(method).toLowerCase();
    if (lower.includes('semantic') || lower.includes('vector')) return 'Semantic Vector';
    if (lower.includes('keyword') || lower.includes('bm25') || lower.includes('lexical')) return 'BM25 Lexical';
    if (lower.includes('graph')) return 'KG Traversal';
    if (lower.includes('hybrid')) return 'Hybrid RAG';
    return String(method);
  };

  const isLoading = isAnalyzing || queryStatus === 'loading';

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-xs border-t-4 border-t-blue-600 flex flex-col h-full transition-all">
      {/* Header */}
      <div className="flex items-center justify-between px-4 sm:px-5 py-3.5 border-b border-slate-100 bg-slate-50/50">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="p-1.5 rounded-lg bg-blue-50 text-blue-700 border border-blue-200/70 shrink-0">
            <BookOpen className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <h2 className="text-xs sm:text-sm font-bold text-slate-900 tracking-tight flex items-center gap-2 truncate">
              <span>RETRIEVED EVIDENCE (Top-{evidenceRecords.length > 0 ? evidenceRecords.length : (topK || 5)})</span>
              <Badge variant={queryStats?.provider ? 'purple' : 'blue'} size="xs">
                {queryStats?.provider ? 'Live RAG' : 'Ranked'}
              </Badge>
              {searchMode && (
                <span className="text-[10px] font-mono font-semibold text-purple-700 bg-purple-100/60 px-1.5 py-0.2 rounded border border-purple-200">
                  {searchMode.toUpperCase()}
                </span>
              )}
            </h2>
            <p className="text-[11px] text-slate-500 truncate">
              Canonical classical verses grounded via Flask Hybrid RAG & Knowledge Graph
            </p>
          </div>
        </div>
      </div>

      {/* Selected Evidence Context Pill (Graph Hook) */}
      {selectedEvidence && !isLoading && !insufficientEvidence && (
        <div className="px-4 py-2 bg-gradient-to-r from-purple-50/90 via-indigo-50/50 to-blue-50/40 border-b border-purple-100 flex items-center justify-between text-[11px] text-purple-900">
          <div className="flex items-center gap-1.5 truncate">
            <span className="font-bold font-mono bg-purple-700 text-white px-1.5 py-0.2 rounded text-[10px]">
              {selectedEvidence.code}
            </span>
            {selectedEvidence.passageId && (
              <span className="font-mono text-[10px] bg-purple-100 text-purple-800 px-1.5 py-0.2 rounded border border-purple-200">
                {selectedEvidence.passageId}
              </span>
            )}
            <span className="font-semibold text-purple-950">Active in Knowledge Graph:</span>
            <span className="truncate text-purple-800 font-medium">
              {selectedEvidence.work || selectedEvidence.source || selectedEvidence.reference}
            </span>
          </div>
          <span className="text-[10px] text-purple-700 font-mono font-semibold shrink-0 hidden sm:inline-flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-purple-600 animate-ping" />
            Graph Synchronized
          </span>
        </div>
      )}

      {/* Evidence Items List or Grid */}
      <div
        className={`p-3 sm:p-4 flex-1 ${
          gridLayout
            ? 'grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3.5'
            : 'space-y-2.5 overflow-y-auto max-h-[520px]'
        }`}
      >
        {/* State 1: Loading Skeleton */}
        {isLoading ? (
          <div className="space-y-3 py-2 col-span-full">
            {[1, 2, 3].map((n) => (
              <div
                key={n}
                className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/60 animate-pulse space-y-2.5"
              >
                <div className="flex items-center justify-between">
                  <div className="h-4 w-32 bg-slate-200 rounded" />
                  <div className="h-4 w-14 bg-slate-200 rounded-full" />
                </div>
                <div className="h-3 w-full bg-slate-200 rounded" />
                <div className="h-3 w-4/5 bg-slate-200 rounded" />
                <div className="flex gap-2 pt-1">
                  <div className="h-3 w-16 bg-slate-200 rounded" />
                  <div className="h-3 w-20 bg-slate-200 rounded" />
                </div>
              </div>
            ))}
            <div className="text-center py-2 text-xs text-purple-700 font-medium flex items-center justify-center gap-2">
              <span className="w-2 h-2 rounded-full bg-purple-600 animate-ping" />
              Retrieving grounded passages from Tolkāppiyam via Hybrid RAG...
            </div>
          </div>
        ) : insufficientEvidence ? (
          /* State 2: Insufficient Evidence Alert */
          <div className="py-8 px-4 text-center space-y-3 bg-amber-50/70 rounded-xl border border-amber-200 col-span-full animate-in fade-in duration-150">
            <div className="w-10 h-10 mx-auto rounded-full bg-amber-100 flex items-center justify-center text-amber-600 shadow-2xs">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div className="space-y-1">
              <p className="text-xs font-bold text-amber-900">Insufficient Canonical Evidence Grounding</p>
              <p className="text-[11px] text-amber-800 max-w-md mx-auto leading-relaxed">
                The Hybrid RAG pipeline evaluated candidate passages against the minimum relevance threshold (0.30) and determined that canonical texts do not sufficiently ground an unambiguous conclusion for this query.
              </p>
            </div>
            <div className="pt-2 flex items-center justify-center gap-2">
              <Button
                variant="primary"
                size="xs"
                onClick={() => loadBenchmarkEvidence('tinai')}
                className="cursor-pointer"
              >
                Load Benchmark Grounding
              </Button>
            </div>
          </div>
        ) : evidenceRecords.length === 0 ? (
          /* State 3: Empty State */
          <div className="py-12 px-4 text-center space-y-3 bg-slate-50/60 rounded-xl border border-dashed border-slate-200 col-span-full">
            <div className="w-10 h-10 mx-auto rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
              <BookOpen className="w-5 h-5" />
            </div>
            <div className="space-y-1">
              <p className="text-xs font-bold text-slate-700">No Grounded Evidence Records</p>
              <p className="text-[11px] text-slate-500 max-w-sm mx-auto">
                Execute a research query in the Query Center above to retrieve grounded passages from the Tolkāppiyam knowledge base.
              </p>
            </div>
          </div>
        ) : (
          /* State 4: Real Retrieved Evidence Records (Fields rendered conditionally) */
          evidenceRecords.map((item) => {
            const isSelected = selectedEvidenceId === item.id || selectedEvidenceId === item.passageId;
            const isScoresExpanded = expandedScoresCardId === item.id;
            const components = item.scoreComponents || item.rawItem?.score_components;
            const relScores = item.relevanceScores || item.rawItem?.relevance_scores;
            const graphCtx = item.graphContext || item.rawItem?.graph_context;
            const associatedEntities = (item.entities && item.entities.length > 0)
              ? item.entities
              : (graphCtx?.associated_entities || []);
            const associatedConcepts = (item.concepts && item.concepts.length > 0)
              ? item.concepts
              : (graphCtx?.concepts || []);
            const provenanceSteps = Array.isArray(item.provenance) && item.provenance.length > 0
              ? item.provenance
              : (Array.isArray(item.graph_path) && item.graph_path.length > 0 ? item.graph_path : null);
            const methods = Array.isArray(item.retrievalMethods) && item.retrievalMethods.length > 0
              ? item.retrievalMethods
              : (item.retrievalMethod ? [item.retrievalMethod] : []);

            return (
              <div
                key={item.id}
                onClick={() => handleSelectEvidence(item)}
                className={`group p-3.5 rounded-xl border transition-all duration-150 cursor-pointer relative space-y-2 ${
                  isSelected
                    ? 'bg-purple-50/70 border-purple-400 shadow-xs ring-2 ring-purple-500/25'
                    : 'bg-white border-slate-200/90 hover:border-slate-300 hover:bg-slate-50/70 hover:shadow-2xs'
                }`}
              >
                {/* 1. Header Bar: Evidence Code + Passage ID + Evidence Type + Relevance Score */}
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <div className="flex items-center gap-1.5 flex-wrap min-w-0">
                    {/* Evidence Code Tag */}
                    <span
                      className={`font-mono text-[11px] font-extrabold px-1.5 py-0.5 rounded-md border shrink-0 transition-colors ${
                        isSelected
                          ? 'bg-purple-700 text-white border-purple-800'
                          : 'bg-slate-100 text-slate-800 border-slate-300 group-hover:bg-purple-100 group-hover:text-purple-900 group-hover:border-purple-300'
                      }`}
                    >
                      {item.code}
                    </span>

                    {/* Passage ID (rendered only when present) */}
                    {item.passageId && (
                      <span
                        className="font-mono text-[10px] font-semibold px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 shrink-0"
                        title="Canonical Passage Identifier"
                      >
                        {item.passageId}
                      </span>
                    )}

                    {/* Evidence Type (rendered only when present) */}
                    {item.evidenceType && (
                      <span
                        className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200/80 shrink-0"
                        title="Evidence Epistemic Type"
                      >
                        {item.evidenceType}
                      </span>
                    )}
                  </div>

                  {/* Relevance Score (rendered only when present) */}
                  {item.relevanceScore !== null && item.relevanceScore !== undefined && (
                    <Badge variant="purple" size="xs">
                      {typeof item.relevanceScore === 'number'
                        ? `${Math.round(item.relevanceScore > 1 ? item.relevanceScore : item.relevanceScore * 100)}% Match`
                        : `${item.relevanceScore}`}
                    </Badge>
                  )}
                </div>

                {/* 2. Source, Work & Section Line (rendered only when fields are present) */}
                {(item.work || item.section || item.chapter || item.source) && (
                  <div className="flex items-center gap-1.5 text-[11px] text-slate-600 flex-wrap">
                    {item.work && (
                      <span className="font-bold text-slate-900">
                        {item.work}
                      </span>
                    )}
                    {item.work && (item.section || item.chapter) && (
                      <span className="text-slate-300">•</span>
                    )}
                    {item.section && (
                      <span className="font-medium text-slate-700">
                        {item.section}
                      </span>
                    )}
                    {item.sutraNumber && (
                      <>
                        <span className="text-slate-300">•</span>
                        <span className="font-mono text-[10px] text-slate-600 font-medium">
                          Sūtra {item.sutraNumber}
                        </span>
                      </>
                    )}
                    {item.tinai && item.tinai !== 'General' && item.tinai !== 'all' && (
                      <>
                        <span className="text-slate-300">•</span>
                        <span className="text-[10px] text-emerald-700 font-semibold bg-emerald-50 px-1 rounded border border-emerald-200/60">
                          {item.tinai}
                        </span>
                      </>
                    )}
                    {item.source && item.source !== item.work && (
                      <span className="text-[10px] text-slate-400 italic truncate max-w-[200px]" title={item.source}>
                        ({item.source})
                      </span>
                    )}
                  </div>
                )}

                {/* 3. Provenance Hierarchy Breadcrumb (rendered only when present) */}
                {provenanceSteps && provenanceSteps.length > 0 && (
                  <div className="flex items-center gap-1 text-[10px] text-slate-600 font-mono py-1 px-2 bg-slate-50/90 rounded-md border border-slate-200/70 overflow-x-auto">
                    <Compass className="w-2.5 h-2.5 text-indigo-600 shrink-0" />
                    <span className="text-slate-400 font-semibold uppercase text-[9px] shrink-0">Provenance:</span>
                    {provenanceSteps.map((step, sIdx) => {
                      const label = typeof step === 'string' ? step : (step.name || step.label || step.id);
                      const stepId = typeof step === 'object' ? (step.id || label) : label;
                      return (
                        <span key={sIdx} className="inline-flex items-center gap-1 shrink-0">
                          {sIdx > 0 && <span className="text-slate-300">›</span>}
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              if (stepId && setSelectedGraphNodeId) setSelectedGraphNodeId(stepId);
                            }}
                            className="hover:text-purple-700 hover:underline cursor-pointer text-slate-700"
                            title={`Focus '${label}' in Knowledge Graph`}
                          >
                            {label}
                          </button>
                        </span>
                      );
                    })}
                  </div>
                )}

                {/* 4. Classical Tamil Passage Text (rendered only when present) */}
                {(item.tamilText || item.text) && (
                  <p className="tamil-font text-xs font-semibold text-slate-900 group-hover:text-purple-950 line-clamp-3 leading-relaxed whitespace-pre-line">
                    {item.tamilText || item.text}
                  </p>
                )}

                {/* 5. English Translation / Paraphrase (rendered only when present) */}
                {item.translation && (
                  <p className="text-[11px] text-slate-500 italic line-clamp-2 leading-relaxed">
                    {item.translation}
                  </p>
                )}

                {/* 6. Retrieval Method Tags (rendered only when present) */}
                {methods.length > 0 && (
                  <div className="flex items-center gap-1 flex-wrap pt-0.5">
                    <span className="text-[9px] uppercase font-mono text-slate-400 font-bold">Method:</span>
                    {methods.map((method, mIdx) => (
                      <span
                        key={mIdx}
                        className="text-[9px] font-mono font-medium px-1.5 py-0.2 rounded bg-indigo-50 text-indigo-700 border border-indigo-200/70"
                      >
                        {formatRetrievalMethod(method)}
                      </span>
                    ))}
                  </div>
                )}

                {/* 7. Connected Knowledge Graph Context Tags (rendered only when present) */}
                {(associatedConcepts.length > 0 || associatedEntities.length > 0) && (
                  <div className="flex items-center gap-1 flex-wrap pt-1 border-t border-slate-100/70">
                    <span className="text-[9px] font-mono text-purple-700 font-semibold flex items-center gap-0.5 shrink-0">
                      <Network className="w-2.5 h-2.5 text-purple-600" />
                      KG:
                    </span>
                    {associatedConcepts.map((concept, cIdx) => {
                      const conceptLabel = typeof concept === 'string' ? concept : (concept?.label || concept?.name || concept?.id || 'Concept');
                      const conceptId = typeof concept === 'string' ? concept : (concept?.id || concept?.label || conceptLabel);
                      return (
                        <button
                          key={`c-${cIdx}`}
                          type="button"
                          onClick={(e) => handleConceptTagClick(e, conceptId)}
                          className="text-[9px] font-mono font-medium px-1.5 py-0.2 rounded bg-purple-50 text-purple-700 border border-purple-200/70 hover:bg-purple-200/80 transition-colors cursor-pointer"
                          title={`Focus concept '${conceptLabel}' in Knowledge Graph Viewer`}
                        >
                          {conceptLabel}
                        </button>
                      );
                    })}
                    {associatedEntities.map((entity, eIdx) => {
                      const entityLabel = typeof entity === 'string' ? entity : (entity?.label || entity?.name || entity?.id || 'Entity');
                      const entityId = typeof entity === 'string' ? entity : (entity?.id || entity?.label || entityLabel);
                      return (
                        <button
                          key={`e-${eIdx}`}
                          type="button"
                          onClick={(e) => handleConceptTagClick(e, entityId)}
                          className="text-[9px] font-mono font-medium px-1.5 py-0.2 rounded bg-amber-50 text-amber-800 border border-amber-200/70 hover:bg-amber-200/80 transition-colors cursor-pointer"
                          title={`Focus entity '${entityLabel}' in Knowledge Graph Viewer`}
                        >
                          {entityLabel}
                        </button>
                      );
                    })}
                  </div>
                )}

                {/* 8. Expandable Score Breakdown Drawer (rendered only when present) */}
                {isScoresExpanded && (components || relScores) && (
                  <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-[10px] font-mono text-slate-700 space-y-1 animate-in fade-in duration-100">
                    <div className="flex items-center justify-between text-slate-500 font-bold uppercase tracking-wider text-[9px] pb-1 border-b border-slate-200/60">
                      <span>Retrieval Signal</span>
                      <span>Weight / Score</span>
                    </div>
                    {relScores?.combined_score !== undefined && (
                      <div className="flex items-center justify-between">
                        <span className="text-purple-900 font-semibold">Combined Relevance:</span>
                        <span className="font-bold text-purple-700">{Math.round(relScores.combined_score * 100)}%</span>
                      </div>
                    )}
                    {(relScores?.semantic_score !== undefined || components?.semantic_similarity !== undefined) && (
                      <div className="flex items-center justify-between">
                        <span className="text-purple-700">Semantic Vector:</span>
                        <span className="font-bold">{Math.round((relScores?.semantic_score ?? components?.semantic_similarity) * 100)}%</span>
                      </div>
                    )}
                    {(relScores?.lexical_score !== undefined || components?.bm25_score !== undefined) && (
                      <div className="flex items-center justify-between">
                        <span className="text-blue-700">BM25 Lexical:</span>
                        <span className="font-bold">{Math.round((relScores?.lexical_score ?? components?.bm25_score) * 100)}%</span>
                      </div>
                    )}
                    {(relScores?.graph_score !== undefined || components?.graph_centrality !== undefined) && (
                      <div className="flex items-center justify-between">
                        <span className="text-emerald-700">KG Traversal Centrality:</span>
                        <span className="font-bold">{Math.round((relScores?.graph_score ?? components?.graph_centrality) * 100)}%</span>
                      </div>
                    )}
                    {components?.source_reliability !== undefined && (
                      <div className="flex items-center justify-between">
                        <span className="text-amber-800">Source Reliability:</span>
                        <span className="font-bold">{Math.round(components.source_reliability * 100)}%</span>
                      </div>
                    )}
                  </div>
                )}

                {/* 9. Bottom Row: Score Toggle + Selection & Graph Sync Status */}
                <div className="flex items-center justify-between gap-2 pt-1 border-t border-slate-100">
                  <div className="flex items-center gap-1 overflow-hidden">
                    {(components || relScores) && (
                      <button
                        type="button"
                        onClick={(e) => toggleScoreBreakdown(e, item.id)}
                        className="text-[9px] font-mono font-medium px-1.5 py-0.5 rounded border border-slate-200 text-slate-500 hover:text-purple-700 hover:border-purple-300 bg-white inline-flex items-center gap-0.5 cursor-pointer"
                        title="Toggle individual relevance score signals"
                      >
                        <BarChart2 className="w-2.5 h-2.5" />
                        <span>Scores</span>
                        {isScoresExpanded ? <ChevronUp className="w-2.5 h-2.5" /> : <ChevronDown className="w-2.5 h-2.5" />}
                      </button>
                    )}

                    {(item.badges || []).slice(0, 1).map((badge, idx) => (
                      <span
                        key={idx}
                        className={`text-[9px] font-medium px-1.5 py-0.2 rounded border truncate ${getBadgeClass(
                          badge.variant
                        )}`}
                      >
                        {badge.label}
                      </span>
                    ))}
                  </div>

                  {/* Knowledge Graph Synchronization Status */}
                  <div className="flex items-center gap-1 shrink-0">
                    {isSelected ? (
                      <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-purple-700 font-mono">
                        <CheckCircle2 className="w-3 h-3 text-purple-600" />
                        Focused in Graph
                      </span>
                    ) : (
                      <span className="text-[10px] text-slate-400 group-hover:text-purple-600 transition-colors">
                        Click to focus graph
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
