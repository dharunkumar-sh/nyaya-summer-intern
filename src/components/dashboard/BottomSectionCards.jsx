import { useState } from 'react';
import {
  CheckCircle2,
  Star,
  FileText,
  Sparkles,
  ShieldCheck,
  Info,
  RotateCcw,
  AlertTriangle,
  Loader2,
  ShieldAlert,
  ExternalLink,
} from 'lucide-react';
import Badge from '../common/Badge';
import { useReasoner } from '../../context/ReasonerContext';
import KnowledgeGraphViewer from './KnowledgeGraphViewer';

/**
 * CARD 1: JUSTIFICATION & EXPLANATION
 */
export function JustificationCard({
  stepNumber,
  totalSteps,
  rowLayout = false,
}) {
  const { finalAnswer, evidenceRecords, insufficientEvidence, setSelectedEvidenceId } = useReasoner();

  if (!finalAnswer) {
    return null;
  }

  return (
    <div className="flex flex-col bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden w-full">
      {/* Card Header */}
      <div className="px-5 sm:px-6 py-4 border-b border-slate-100 bg-slate-50/60 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="p-1.5 rounded-lg bg-purple-100 text-purple-700 border border-purple-200/70 shrink-0">
            <FileText className="w-4 h-4" />
          </span>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-xs uppercase tracking-wider text-slate-900 truncate">
                JUSTIFICATION & EXPLANATION
              </h3>
              {stepNumber && (
                <span className="text-[10px] font-mono font-bold text-purple-700 bg-purple-50 px-1.5 py-0.2 rounded border border-purple-200">
                  {stepNumber}/{totalSteps || 7}
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-500 truncate">
              Epistemic & Textual Provenance
            </p>
          </div>
        </div>
        <Badge variant={insufficientEvidence ? 'orange' : 'purple'} size="xs">
          {insufficientEvidence ? 'Insufficient Evidence' : 'Evidence-Grounded'}
        </Badge>
      </div>

      {/* Card Body */}
      <div
        className={`p-5 sm:p-6 flex-1 text-xs sm:text-sm ${
          rowLayout
            ? 'grid grid-cols-1 lg:grid-cols-12 gap-6 items-start'
            : 'flex flex-col justify-between space-y-4'
        }`}
      >
        <div className={rowLayout ? 'lg:col-span-7 space-y-3.5' : 'space-y-4'}>
          {insufficientEvidence ? (
            <div className="p-4 rounded-xl bg-amber-50 border border-amber-200/90 text-amber-900 space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-800">
                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                <span>Insufficient Canonical Evidence Grounding</span>
              </div>
              <p className="text-xs text-amber-900 leading-relaxed font-serif">
                {finalAnswer.justificationTamil}
              </p>
              <p className="text-xs text-amber-800 leading-relaxed italic border-l-2 border-amber-400 pl-3">
                {finalAnswer.justificationEnglish}
              </p>
            </div>
          ) : (
            <>
              {/* Concise Tamil Explanation */}
              <div className="p-4 rounded-xl bg-purple-50/60 border border-purple-200/80 space-y-2">
                <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-purple-800">
                  <Info className="w-3.5 h-3.5 text-purple-600" />
                  <span>தமிழ் விளக்கம் (Tamil Justification)</span>
                </div>
                <p className="text-slate-900 font-serif leading-relaxed text-sm sm:text-base font-medium">
                  {finalAnswer.justificationTamil}
                </p>
              </div>

              {/* English Synthesis */}
              <p className="text-slate-600 text-xs sm:text-sm leading-relaxed italic border-l-3 border-purple-400 pl-3.5">
                {finalAnswer.justificationEnglish}
              </p>
            </>
          )}
        </div>

        {/* Key Sources & Supporting Passages Column / Row */}
        <div
          className={
            rowLayout
              ? 'lg:col-span-5 bg-slate-50/70 p-4 sm:p-5 rounded-xl border border-slate-200/80 space-y-3.5'
              : 'pt-3 border-t border-slate-100 space-y-3'
          }
        >
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-700">
                Key Grounding Sources:
              </span>
              <span className="text-[10px] font-mono text-slate-400">
                {(finalAnswer.keySources || []).length} Citations
              </span>
            </div>

            {/* Source Badges Row */}
            <div className="flex items-center gap-2 flex-wrap">
              {(finalAnswer.keySources || []).map((source) => (
                <span
                  key={source.id}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border font-mono text-xs font-semibold bg-white text-slate-700 border-slate-200 shadow-2xs"
                  title={`${source.id}: ${source.sutra}${source.topic ? ` (${source.topic})` : ''}`}
                >
                  <span className="font-bold text-purple-700">{source.id}</span>
                  <span className="text-[10px] text-slate-500 font-normal">
                    ({source.sutra})
                  </span>
                  {source.score && (
                    <span className="text-[10px] text-emerald-700 font-bold bg-emerald-50 px-1 py-0.2 rounded border border-emerald-200/60">
                      {source.score}
                    </span>
                  )}
                </span>
              ))}
              {(!finalAnswer.keySources || finalAnswer.keySources.length === 0) && (
                <span className="text-xs text-slate-400 italic">No direct sources cited</span>
              )}
            </div>
          </div>

          {/* Supporting Passages Excerpts */}
          {evidenceRecords && evidenceRecords.length > 0 && !insufficientEvidence && (
            <div className="pt-2 border-t border-slate-200/60 space-y-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-700 block">
                Supporting Passages:
              </span>
              <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                {evidenceRecords.slice(0, 3).map((ev) => (
                  <div
                    key={ev.id}
                    onClick={() => setSelectedEvidenceId?.(ev.id)}
                    className="p-2 rounded-lg bg-white border border-slate-200/80 hover:border-purple-300 hover:bg-purple-50/40 transition-colors cursor-pointer text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="font-mono font-bold text-purple-700">{ev.code || ev.id}</span>
                      <span className="text-slate-500 font-medium truncate max-w-[160px]">{ev.reference}</span>
                      <span className="font-mono text-emerald-700 font-bold">{ev.confidenceFormatted}</span>
                    </div>
                    <p className="tamil-font text-slate-800 text-[11px] line-clamp-1">{ev.tamilText}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * CARD 2: PROOF TRACE (GRAPHICAL)
 */
export function ProofTraceCard({ stepNumber, totalSteps, rowLayout = false }) {
  const {
    proofNodes,
    proofTraceData,
    selectedProofNodeId,
    setSelectedProofNodeId,
    showProofTrace,
    resetGraph,
    isShowingProofTrace,
    insufficientEvidence,
    isLoadingProofTrace,
    isAnalyzing,
    loadBenchmarkEvidence,
  } = useReasoner();

  const [viewMode, setViewMode] = useState('cytoscape');

  const isInsufficient =
    insufficientEvidence ||
    proofTraceData?.status === 'INSUFFICIENT_EVIDENCE' ||
    proofTraceData?.insufficient_evidence ||
    (proofNodes.length === 0 && !isLoadingProofTrace && !isAnalyzing);

  const isLoading = isLoadingProofTrace || isAnalyzing;

  const activeNode =
    proofNodes.find((n) => n.id === selectedProofNodeId) ||
    proofNodes[0] ||
    null;

  const svgWidth = 540;
  const svgPadding = 36;
  const getNodeCx = (index, total) => {
    if (total <= 1) return svgWidth / 2;
    return Math.round(svgPadding + (index / (total - 1)) * (svgWidth - 2 * svgPadding));
  };

  return (
    <div className="flex flex-col bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden h-full">
      {/* Card Header */}
      <div className="px-5 py-3.5 border-b border-slate-100 bg-slate-50/60 flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2.5 min-w-0">
          <span
            className={`p-1.5 rounded-lg border shrink-0 ${
              isInsufficient
                ? 'bg-amber-100 text-amber-800 border-amber-200/80'
                : 'bg-blue-100 text-blue-700 border-blue-200/70'
            }`}
          >
            {isInsufficient ? (
              <AlertTriangle className="w-4 h-4 text-amber-700" />
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
          </span>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-xs uppercase tracking-wider text-slate-900 truncate">
                PROOF TRACE (Graphical)
              </h3>
              {stepNumber && (
                <span className="text-[10px] font-mono font-bold text-blue-700 bg-blue-50 px-1.5 py-0.2 rounded border border-blue-200">
                  {stepNumber}/{totalSteps || 7}
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-500 truncate">
              {isInsufficient
                ? 'Proof Chain Unavailable (Insufficient Evidence)'
                : proofNodes.length > 0
                  ? proofNodes.map((n) => n.label || n.id).join(' → ')
                  : 'E1 → P1 → E2 → P2 → R1 → I1 → C1'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0 flex-wrap">
          {!isInsufficient && proofNodes.length > 0 && (
            <>
              {/* View Mode Toggle: Cytoscape Graph vs Linear SVG */}
              <div className="flex items-center bg-slate-100 p-0.5 rounded-lg text-[10px] font-semibold border border-slate-200/80">
                <button
                  type="button"
                  onClick={() => setViewMode('cytoscape')}
                  className={`px-2 py-0.5 rounded-md transition-all cursor-pointer ${
                    viewMode === 'cytoscape'
                      ? 'bg-white text-purple-900 shadow-2xs font-bold'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                  title="Interactive Cytoscape Proof Trace Graph"
                >
                  Cytoscape Graph
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode('svg')}
                  className={`px-2 py-0.5 rounded-md transition-all cursor-pointer ${
                    viewMode === 'svg'
                      ? 'bg-white text-purple-900 shadow-2xs font-bold'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                  title="Linear Pipeline SVG"
                >
                  Linear SVG
                </button>
              </div>

              {/* Quick Action: Show Proof Trace */}
              <button
                type="button"
                onClick={isShowingProofTrace ? resetGraph : showProofTrace}
                className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-bold transition-all cursor-pointer shadow-2xs ${
                  isShowingProofTrace
                    ? 'bg-amber-500 text-white hover:bg-amber-600 ring-2 ring-amber-400/40'
                    : 'bg-white text-slate-700 hover:bg-amber-50 hover:text-amber-900 border border-slate-200'
                }`}
                title="Focus Cytoscape on Nyāya Proof Trace"
              >
                <Sparkles className={`w-3 h-3 ${isShowingProofTrace ? 'text-white' : 'text-amber-600'}`} />
                <span>{isShowingProofTrace ? 'Proof Path Active' : 'Show Proof Trace'}</span>
              </button>

              {/* Quick Action: Reset Graph */}
              <button
                type="button"
                onClick={resetGraph}
                className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-bold bg-white text-slate-700 hover:bg-purple-50 hover:text-purple-900 border border-slate-200 transition-all shadow-2xs cursor-pointer"
                title="Restore complete graph and clear proof isolation"
              >
                <RotateCcw className="w-3 h-3 text-purple-600" />
                <span>Reset</span>
              </button>
            </>
          )}

          <Badge variant={isInsufficient ? 'orange' : 'blue'} size="xs">
            {isInsufficient
              ? 'Unavailable'
              : `${proofNodes.length} Nodes Grounded`}
          </Badge>
        </div>
      </div>

      {/* Card Body */}
      <div className="p-4 sm:p-5 flex-1 flex flex-col justify-between space-y-3.5">
        {/* State 1: Loading Skeleton */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center p-8 rounded-xl bg-slate-50 border border-slate-200 text-center space-y-3">
            <Loader2 className="w-6 h-6 text-blue-600 animate-spin" />
            <div className="space-y-1">
              <h4 className="text-xs font-bold text-slate-800">
                Generating Epistemic Proof Trace DAG...
              </h4>
              <p className="text-[11px] text-slate-500 max-w-sm">
                Evaluating retrieved canonical verses and verifying uninterrupted path to conclusion.
              </p>
            </div>
          </div>
        )}

        {/* State 2: Explicit Insufficient Evidence State (Never hardcode fake nodes!) */}
        {!isLoading && isInsufficient && (
          <div className="rounded-xl p-4 bg-amber-50/80 border border-amber-200/90 text-amber-950 space-y-3">
            <div className="flex items-start gap-2.5">
              <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
              <div className="space-y-1 min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <h4 className="font-bold text-xs uppercase tracking-wider text-amber-900">
                    Proof Trace Unavailable / Insufficient Evidence
                  </h4>
                  <span className="text-[10px] font-mono text-amber-800 bg-amber-100/80 px-2 py-0.5 rounded border border-amber-300/70 font-semibold">
                    Unestablished Vyāpti
                  </span>
                </div>
                <p className="text-xs text-amber-900/90 leading-relaxed">
                  {proofTraceData?.reason ||
                    'The current query retrieved insufficient canonical sūtras to establish an unbroken Nyāya proof chain. At least 2 grounded verses are required to derive universal concomitance (Vyāpti).'}
                </p>
              </div>
            </div>

            {/* Missing Requirements List */}
            <div className="bg-white/80 p-3 rounded-lg border border-amber-200/70 space-y-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-amber-800 block">
                Missing Canonical Requirements for Sound Deduction:
              </span>
              <ul className="list-disc list-inside space-y-1 text-xs text-amber-950 pl-1 font-mono">
                {(proofTraceData?.missing_requirements && proofTraceData.missing_requirements.length > 0
                  ? proofTraceData.missing_requirements
                  : [
                      'Terrestrial habitat (Mutalporuḷ) canonical verse',
                      'Corroborating biotic signifier (Karupporuḷ) canonical verse to establish Vyāpti',
                    ]
                ).map((req, idx) => (
                  <li key={idx} className="text-[11px]">
                    {req}
                  </li>
                ))}
              </ul>
            </div>

            <div className="flex items-center justify-between pt-1 flex-wrap gap-2 text-xs">
              <span className="text-[11px] text-amber-800 italic">
                Synthetic proof generation blocked to maintain epistemic truthfulness.
              </span>
              {loadBenchmarkEvidence && (
                <button
                  type="button"
                  onClick={() => loadBenchmarkEvidence('tinai')}
                  className="px-2.5 py-1 rounded-lg text-xs font-bold bg-amber-600 hover:bg-amber-700 text-white transition-colors cursor-pointer shadow-2xs inline-flex items-center gap-1"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Load Canonical Benchmark</span>
                </button>
              )}
            </div>
          </div>
        )}

        {/* State 3: Valid Dynamic Proof Trace (Nodes exist) */}
        {!isLoading && !isInsufficient && proofNodes.length > 0 && (
          <>
            {/* VIEW MODE 1: CYTOSCAPE GRAPH */}
            {viewMode === 'cytoscape' && (
              <div className="rounded-xl overflow-hidden border border-slate-200 shadow-inner bg-slate-50/50">
                <KnowledgeGraphViewer
                  height="h-[280px] sm:h-[310px]"
                  showToolbar={false}
                  showLegend={false}
                  initialLayout="cose"
                  className="!border-0 !rounded-none !shadow-none"
                />
              </div>
            )}

            {/* VIEW MODE 2: SVG VISUAL FLOW */}
            {viewMode === 'svg' && (
              <div className="bg-slate-900/95 rounded-xl p-3 border border-slate-800 shadow-inner overflow-x-auto">
                <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1 font-mono">
                  <span>CANONICAL INFERENCE GRAPH (SVG)</span>
                  <span>Click step to inspect & highlight in graph</span>
                </div>

                <svg
                  viewBox={`0 0 ${svgWidth} 76`}
                  className="w-full h-auto min-w-[420px] select-none"
                  style={{ maxHeight: '82px' }}
                >
                  <defs>
                    <marker
                      id="traceArrow"
                      viewBox="0 0 10 10"
                      refX="8"
                      refY="5"
                      markerWidth="6"
                      markerHeight="6"
                      orient="auto-start-reverse"
                    >
                      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#64748b" />
                    </marker>
                    <marker
                      id="traceArrowActive"
                      viewBox="0 0 10 10"
                      refX="8"
                      refY="5"
                      markerWidth="6"
                      markerHeight="6"
                      orient="auto-start-reverse"
                    >
                      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#a855f7" />
                    </marker>
                  </defs>

                  {/* Connecting Directed Lines between Adjacent Nodes */}
                  {proofNodes.map((node, i) => {
                    if (i === proofNodes.length - 1) return null;
                    const nextNode = proofNodes[i + 1];
                    const cx1 = getNodeCx(i, proofNodes.length);
                    const cx2 = getNodeCx(i + 1, proofNodes.length);
                    const isNodeActive =
                      selectedProofNodeId === node.id || selectedProofNodeId === nextNode.id;

                    return (
                      <line
                        key={`line-${node.id}-${nextNode.id}`}
                        x1={cx1 + 16}
                        y1={38}
                        x2={cx2 - 16}
                        y2={38}
                        stroke={isNodeActive ? '#a855f7' : '#334155'}
                        strokeWidth={isNodeActive ? 2.2 : 1.5}
                        markerEnd={isNodeActive ? 'url(#traceArrowActive)' : 'url(#traceArrow)'}
                        strokeDasharray={node.typeShort === 'R' ? '3,3' : 'none'}
                      />
                    );
                  })}

                  {/* Circular Nodes */}
                  {proofNodes.map((node, i) => {
                    const isSelected = selectedProofNodeId === node.id;
                    const cx = getNodeCx(i, proofNodes.length);

                    return (
                      <g
                        key={node.id}
                        onClick={() => setSelectedProofNodeId(node.id)}
                        className="cursor-pointer group"
                      >
                        {/* Active glow ring */}
                        {isSelected && (
                          <circle
                            cx={cx}
                            cy={38}
                            r={21}
                            fill="none"
                            stroke={node.color || '#a855f7'}
                            strokeWidth="2.5"
                            opacity="0.95"
                            className="animate-pulse"
                          />
                        )}

                        {/* Main Node Circle */}
                        <circle
                          cx={cx}
                          cy={38}
                          r={15}
                          fill={node.color || '#3b82f6'}
                          stroke={isSelected ? '#ffffff' : '#0f172a'}
                          strokeWidth={isSelected ? 2 : 1.5}
                          className="transition-transform duration-150 group-hover:scale-110"
                        />

                        {/* Node Label Text (E1, P1, etc.) */}
                        <text
                          x={cx}
                          y={42}
                          textAnchor="middle"
                          fill="#ffffff"
                          fontSize="10"
                          fontWeight="bold"
                          fontFamily="monospace"
                          className="pointer-events-none"
                        >
                          {node.label || node.id}
                        </text>
                      </g>
                    );
                  })}
                </svg>

                {/* Flow Direction summary */}
                <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 font-mono">
                  <span>Start: {proofNodes[0]?.label} ({proofNodes[0]?.type || 'Evidence'})</span>
                  <span className="text-purple-400">→ Invariant Rule (R1) →</span>
                  <span className="text-emerald-400">Conclusion: {proofNodes[proofNodes.length - 1]?.label}</span>
                </div>
              </div>
            )}

            {/* Interactive Step Chips Bar */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-thin">
              {proofNodes.map((node) => {
                const isSelected = selectedProofNodeId === node.id;
                return (
                  <button
                    key={`pill-${node.id}`}
                    type="button"
                    onClick={() => setSelectedProofNodeId(node.id)}
                    className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg font-mono text-[11px] font-bold transition-all cursor-pointer shrink-0 border ${
                      isSelected
                        ? 'bg-purple-700 text-white border-purple-800 shadow-xs ring-2 ring-purple-300/50'
                        : 'bg-slate-50 hover:bg-purple-50 text-slate-700 border-slate-200'
                    }`}
                  >
                    <span
                      className={`w-2 h-2 rounded-full ${
                        node.bg || 'bg-blue-600'
                      }`}
                    />
                    <span>{node.label || node.id}</span>
                    <span className="text-[9px] opacity-75 font-normal">
                      ({node.typeShort || (node.type ? node.type[0] : 'S')})
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Selected Node Details Box & Legend */}
            {activeNode && (
              <div
                className={
                  rowLayout
                    ? 'grid grid-cols-1 lg:grid-cols-12 gap-4 items-start'
                    : 'space-y-3'
                }
              >
                <div className={rowLayout ? 'lg:col-span-8' : ''}>
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <div className="flex items-center gap-2 min-w-0">
                        <span
                          className={`w-6 h-6 rounded-full text-white text-[11px] font-mono font-bold flex items-center justify-center shrink-0 ${
                            activeNode.bg || 'bg-purple-600'
                          }`}
                        >
                          {activeNode.label || activeNode.id}
                        </span>
                        <div className="min-w-0">
                          <span className="font-bold text-xs text-slate-900 block truncate">
                            {activeNode.name}
                          </span>
                          {activeNode.tamilName && (
                            <span className="text-[10px] text-slate-500 font-serif block truncate">
                              {activeNode.tamilName}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5 shrink-0">
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-200/90 text-slate-800 font-bold">
                          {activeNode.type || 'Step'}
                        </span>
                        {activeNode.relationshipLabel && (
                          <span className="text-[10px] font-mono text-purple-700 bg-purple-50 px-2 py-0.5 rounded border border-purple-200/80">
                            → {activeNode.relationshipLabel}
                          </span>
                        )}
                      </div>
                    </div>

                    <p className="text-xs text-slate-700 font-medium leading-relaxed">
                      {activeNode.summary || activeNode.explanation}
                    </p>

                    {activeNode.formalLogic && (
                      <div className="font-mono text-[10px] text-purple-900 bg-purple-50/80 p-2 rounded-lg border border-purple-200/70 truncate">
                        <span className="font-bold text-purple-700 mr-1.5">LOGIC:</span>
                        {activeNode.formalLogic}
                      </div>
                    )}

                    {/* Citation / Source Reference */}
                    {(activeNode.sourceReference || activeNode.citation || activeNode.passageId) && (
                      <div className="flex items-center justify-between text-[10px] font-mono text-slate-600 bg-white p-2 rounded-lg border border-slate-200 flex-wrap gap-1">
                        <span className="truncate">
                          <span className="font-bold text-slate-400 mr-1.5">SOURCE:</span>
                          {activeNode.sourceReference || activeNode.citation || activeNode.passageId}
                        </span>
                        <button
                          type="button"
                          onClick={() => setSelectedProofNodeId(activeNode.id)}
                          className="text-blue-600 hover:text-blue-800 font-semibold inline-flex items-center gap-0.5 cursor-pointer ml-auto"
                          title="Highlight corresponding node and edges in Knowledge Graph"
                        >
                          <ExternalLink className="w-2.5 h-2.5" />
                          <span>Graph Sync</span>
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                <div
                  className={
                    rowLayout
                      ? 'lg:col-span-4 bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-2'
                      : 'pt-2 border-t border-slate-100 flex items-center justify-between text-[10px] font-mono text-slate-500'
                  }
                >
                  <div
                    className={
                      rowLayout
                        ? 'grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-600'
                        : 'flex items-center justify-between w-full text-[10px] font-mono text-slate-500'
                    }
                  >
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-blue-600" /> E: Evidence
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-purple-600" /> P: Premise
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-amber-600" /> R: Rule
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-indigo-600" /> I: Infer
                    </span>
                    <span className="flex items-center gap-1 col-span-2">
                      <span className="w-2 h-2 rounded-full bg-emerald-600" /> C: Concl
                    </span>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

/**
 * CARD 3: FINAL ANSWER (PROMINENT EPISTEMIC VERDICT & CONFIDENCE)
 */
export function FinalAnswerCard({ stepNumber, totalSteps, rowLayout = false }) {
  const {
    finalAnswer,
    insufficientEvidence,
  } = useReasoner();

  if (!finalAnswer) {
    return null;
  }

  // Dynamic star rendering calculation
  const score = typeof finalAnswer.confidenceScore === 'number' ? finalAnswer.confidenceScore : 0.95;
  const totalStars = 5;
  const ratingValue = score * 5;
  const fullStarsCount = Math.floor(ratingValue);
  const remainderPercent = Math.round((ratingValue - fullStarsCount) * 100);

  return (
    <div
      className={`flex flex-col bg-white rounded-2xl shadow-md overflow-hidden w-full transition-colors ${
        insufficientEvidence
          ? 'border-2 border-amber-400/80'
          : 'border-2 border-emerald-500/80'
      }`}
    >
      {/* Header: Emerald when verified, Amber when insufficient evidence */}
      <div
        className={`px-5 sm:px-6 py-3.5 text-white flex items-center justify-between gap-2 ${
          insufficientEvidence
            ? 'bg-gradient-to-r from-amber-700 via-amber-600 to-orange-700'
            : 'bg-gradient-to-r from-emerald-700 via-emerald-600 to-teal-700'
        }`}
      >
        <div className="flex items-center gap-2 min-w-0">
          {insufficientEvidence ? (
            <AlertTriangle className="w-5 h-5 text-amber-200 shrink-0" />
          ) : (
            <ShieldCheck className="w-5 h-5 text-emerald-200 shrink-0" />
          )}
          <h3 className="font-extrabold text-xs uppercase tracking-widest text-white truncate">
            {insufficientEvidence ? 'INSUFFICIENT EVIDENCE' : 'FINAL ANSWER'}
          </h3>
          {stepNumber && (
            <span
              className={`text-[10px] font-mono font-bold text-white px-1.5 py-0.2 rounded border ${
                insufficientEvidence
                  ? 'bg-amber-900/60 border-amber-300/40'
                  : 'bg-emerald-900/60 border-emerald-300/40'
              }`}
            >
              {stepNumber}/{totalSteps || 7}
            </span>
          )}
        </div>
        <span
          className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border text-white shrink-0 ${
            insufficientEvidence
              ? 'bg-amber-950/40 border-amber-300/40'
              : 'bg-emerald-950/40 border-emerald-300/40 text-emerald-100'
          }`}
        >
          {insufficientEvidence ? 'DEFEASIBLE STOP' : 'Q.E.D. VERIFIED'}
        </span>
      </div>

      {/* Card Body: Balanced 2-Section Layout */}
      <div
        className={`p-5 sm:p-6 flex-1 ${
          rowLayout
            ? 'flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6'
            : 'flex flex-col justify-between space-y-4'
        }`}
      >
        {/* Left / Main Section: Status Icon & Answers */}
        <div className="flex items-start gap-4 flex-1 min-w-0">
          {/* Status Check / Alert Icon */}
          <div
            className={`w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 shadow-xs border-2 ${
              insufficientEvidence
                ? 'bg-amber-100 text-amber-600 border-amber-400'
                : 'bg-emerald-100 text-emerald-600 border-emerald-400'
            }`}
          >
            {insufficientEvidence ? (
              <AlertTriangle className="w-7 h-7" />
            ) : (
              <CheckCircle2 className="w-7 h-7" />
            )}
          </div>

          <div className="space-y-2 min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span
                className={`text-[10px] font-bold uppercase tracking-wider font-mono px-2 py-0.5 rounded border ${
                  insufficientEvidence
                    ? 'bg-amber-50 text-amber-800 border-amber-200'
                    : 'bg-emerald-50 text-emerald-800 border-emerald-200'
                }`}
              >
                {insufficientEvidence ? 'Epistemic Boundary Reached' : 'Canonical Epistemic Verdict'}
              </span>
              {finalAnswer.verdictStatus && (
                <span className="text-xs text-slate-500 font-medium truncate">
                  • {finalAnswer.verdictStatus}
                </span>
              )}
            </div>

            {/* Tamil Answer Text */}
            <h4 className="text-base sm:text-xl font-bold text-slate-900 font-serif leading-snug">
              “{finalAnswer.tamilAnswer}”
            </h4>

            {/* English Answer Text */}
            <p className="text-xs sm:text-sm font-semibold text-slate-700 leading-relaxed">
              “{finalAnswer.englishAnswer}”
            </p>

            {/* Subtitle / Grounding Description */}
            {finalAnswer.subtitle && (
              <p className="text-xs text-slate-500 leading-relaxed">
                {finalAnswer.subtitle}
              </p>
            )}

            {/* Key Grounding Sources */}
            {!insufficientEvidence && (finalAnswer.keySources || []).length > 0 && (
              <div className="flex items-center gap-2 flex-wrap pt-1">
                <span className="text-[11px] uppercase font-bold text-slate-500">Sources:</span>
                {finalAnswer.keySources.map((s) => (
                  <span
                    key={s.id}
                    className="text-xs font-mono font-semibold px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200 shadow-2xs"
                  >
                    {s.sutra || s.id}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Section: Confidence Score Card */}
        <div className="shrink-0 lg:self-center">
          <div
            className={`p-4 rounded-xl border flex items-center justify-between gap-5 min-w-[230px] sm:min-w-[260px] shadow-2xs ${
              insufficientEvidence
                ? 'bg-amber-50/80 border-amber-200'
                : 'bg-emerald-50/80 border-emerald-200'
            }`}
          >
            <div>
              <span
                className={`text-[10px] font-bold uppercase tracking-wider block ${
                  insufficientEvidence ? 'text-amber-900' : 'text-emerald-900'
                }`}
              >
                Confidence Score
              </span>
              {/* Star Icons */}
              <div className="flex items-center gap-1 mt-1">
                {Array.from({ length: totalStars }).map((_, starIndex) => {
                  if (!insufficientEvidence && starIndex < fullStarsCount) {
                    return (
                      <Star
                        key={starIndex}
                        className="w-4 h-4 fill-amber-400 text-amber-400 shrink-0"
                      />
                    );
                  } else if (!insufficientEvidence && starIndex === fullStarsCount && remainderPercent > 0) {
                    return (
                      <div key={starIndex} className="relative w-4 h-4 shrink-0">
                        <Star className="w-4 h-4 text-slate-300" />
                        <div
                          className="absolute inset-0 overflow-hidden"
                          style={{ width: `${remainderPercent}%` }}
                        >
                          <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
                        </div>
                      </div>
                    );
                  } else {
                    return (
                      <Star
                        key={starIndex}
                        className="w-4 h-4 text-slate-300 shrink-0"
                      />
                    );
                  }
                })}
              </div>
            </div>

            {/* Numerical Score & Status */}
            <div className="text-right">
              <span
                className={`font-mono text-2xl font-extrabold leading-none ${
                  insufficientEvidence ? 'text-amber-700' : 'text-emerald-700'
                }`}
              >
                {insufficientEvidence ? '0.00' : finalAnswer.confidenceScore}
              </span>
              <span
                className={`block text-[10px] font-semibold mt-1 ${
                  insufficientEvidence ? 'text-amber-600' : 'text-emerald-600'
                }`}
              >
                {insufficientEvidence ? 'Below Threshold' : 'High Certainty'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * DEFAULT COMBINED EXPORT: Stacked layout with Justification followed by Final Answer
 */
export default function BottomSectionCards({
  selectedEvidenceId,
  onSelectEvidence,
  rowLayout = true,
  showJustification = true,
  showFinalAnswer = true,
}) {
  return (
    <div className="flex flex-col space-y-6 animate-in fade-in duration-200">
      {/* 1. JUSTIFICATION & EXPLANATION (Epistemic & Textual Rationale) */}
      {showJustification && (
        <JustificationCard
          selectedEvidenceId={selectedEvidenceId}
          onSelectEvidence={onSelectEvidence}
          rowLayout={rowLayout}
        />
      )}

      {/* 2. FINAL ANSWER (Q.E.D. Verified Verdict & Resolution) */}
      {showFinalAnswer && <FinalAnswerCard rowLayout={rowLayout} />}
    </div>
  );
}

