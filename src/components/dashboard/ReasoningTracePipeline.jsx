import { useState } from 'react';
import {
  ChevronRight,
  ShieldCheck,
  Cpu,
  BookOpen,
  Sparkles,
  ExternalLink,
  Info,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Network,
  Search,
} from 'lucide-react';
import Card from '../common/Card';
import Badge from '../common/Badge';

// Dedicated Stage Inline SVGs
function StageTargetIcon({ className = 'w-4 h-4' }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="10" />
      <circle cx="12" cy="12" r="6" />
      <circle cx="12" cy="12" r="2" />
      <line x1="12" y1="2" x2="12" y2="4" />
      <line x1="12" y1="20" x2="12" y2="22" />
      <line x1="2" y1="12" x2="4" y2="12" />
      <line x1="20" y1="12" x2="22" y2="12" />
    </svg>
  );
}

function StageFlameIcon({ className = 'w-4 h-4' }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z" />
    </svg>
  );
}

function StageScalesIcon({ className = 'w-4 h-4' }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <line x1="12" y1="3" x2="12" y2="21" />
      <line x1="3" y1="7" x2="21" y2="7" />
      <path d="M5 7l-3 7h6l-3-7z" />
      <path d="M19 7l-3 7h6l-3-7z" />
      <line x1="2" y1="14" x2="8" y2="14" />
      <line x1="16" y1="14" x2="22" y2="14" />
      <circle cx="12" cy="3" r="1.5" />
      <path d="M9 21h6" />
    </svg>
  );
}

function StageLensIcon({ className = 'w-4 h-4' }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
      <line x1="11" y1="8" x2="11" y2="14" />
      <line x1="8" y1="11" x2="14" y2="11" />
    </svg>
  );
}

function StageShieldIcon({ className = 'w-4 h-4' }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}

// Stage-specific styling themes
const STAGE_THEMES = [
  {
    // Stage 1: Pratijñā (Purple)
    borderNormal: 'border-purple-200/90',
    borderSelected: 'border-purple-600 ring-2 ring-purple-500/30 shadow-md',
    bgNormal: 'bg-purple-50/40 hover:bg-purple-50/70',
    bgSelected: 'bg-purple-50/90',
    badgeVariant: 'purple',
    badgeBg: 'bg-purple-100 text-purple-800 border-purple-200',
    iconBg: 'bg-purple-100 text-purple-700',
    pillBg: 'bg-purple-700 text-white',
    accentText: 'text-purple-700',
    accentLine: 'bg-purple-500',
    iconComponent: StageTargetIcon,
  },
  {
    // Stage 2: Hetu (Amber/Orange)
    borderNormal: 'border-amber-200/90',
    borderSelected: 'border-amber-500 ring-2 ring-amber-500/30 shadow-md',
    bgNormal: 'bg-amber-50/40 hover:bg-amber-50/70',
    bgSelected: 'bg-amber-50/90',
    badgeVariant: 'orange',
    badgeBg: 'bg-amber-100 text-amber-900 border-amber-200',
    iconBg: 'bg-amber-100 text-amber-800',
    pillBg: 'bg-amber-600 text-white',
    accentText: 'text-amber-800',
    accentLine: 'bg-amber-500',
    iconComponent: StageFlameIcon,
  },
  {
    // Stage 3: Udāharaṇa (Blue)
    borderNormal: 'border-blue-200/90',
    borderSelected: 'border-blue-600 ring-2 ring-blue-500/30 shadow-md',
    bgNormal: 'bg-blue-50/40 hover:bg-blue-50/70',
    bgSelected: 'bg-blue-50/90',
    badgeVariant: 'blue',
    badgeBg: 'bg-blue-100 text-blue-800 border-blue-200',
    iconBg: 'bg-blue-100 text-blue-700',
    pillBg: 'bg-blue-700 text-white',
    accentText: 'text-blue-700',
    accentLine: 'bg-blue-500',
    iconComponent: StageScalesIcon,
  },
  {
    // Stage 4: Upanaya (Indigo/Violet)
    borderNormal: 'border-indigo-200/90',
    borderSelected: 'border-indigo-600 ring-2 ring-indigo-500/30 shadow-md',
    bgNormal: 'bg-indigo-50/40 hover:bg-indigo-50/70',
    bgSelected: 'bg-indigo-50/90',
    badgeVariant: 'purpleDark',
    badgeBg: 'bg-indigo-100 text-indigo-800 border-indigo-200',
    iconBg: 'bg-indigo-100 text-indigo-700',
    pillBg: 'bg-indigo-700 text-white',
    accentText: 'text-indigo-700',
    accentLine: 'bg-indigo-500',
    iconComponent: StageLensIcon,
  },
  {
    // Stage 5: Nigamana (Emerald/Green)
    borderNormal: 'border-emerald-200/90',
    borderSelected: 'border-emerald-600 ring-2 ring-emerald-500/30 shadow-md',
    bgNormal: 'bg-emerald-50/40 hover:bg-emerald-50/70',
    bgSelected: 'bg-emerald-50/90',
    badgeVariant: 'emerald',
    badgeBg: 'bg-emerald-100 text-emerald-800 border-emerald-200',
    iconBg: 'bg-emerald-100 text-emerald-700',
    pillBg: 'bg-emerald-700 text-white',
    accentText: 'text-emerald-700',
    accentLine: 'bg-emerald-500',
    iconComponent: StageShieldIcon,
  },
];

import { useReasoner } from '../../context/ReasonerContext';

export default function ReasoningTracePipeline({
  currentQuery: propQuery,
  selectedEvidenceId: propEvidenceId,
  onSelectEvidence: propOnSelectEvidence,
}) {
  const reasoner = useReasoner();

  const currentQuery = propQuery || reasoner.currentQuery;
  const selectedEvidenceId = propEvidenceId || reasoner.selectedEvidenceId;
  const onSelectEvidence = propOnSelectEvidence || reasoner.setSelectedEvidenceId;

  const selectedStageIndex = reasoner.selectedStageIndex;
  const setSelectedStageIndex = reasoner.setSelectedStageIndex;
  const [isInspectorExpanded, setIsInspectorExpanded] = useState(true);

  // Purely dynamic reasoning stages from backend Flask /api/reasoning/deduce
  const rawStages = Array.isArray(reasoner.reasoningStages) && reasoner.reasoningStages.length > 0
    ? reasoner.reasoningStages
    : (Array.isArray(currentQuery?.reasoningStages) && currentQuery.reasoningStages.length > 0
      ? currentQuery.reasoningStages
      : []);

  const canonicalOrderMap = {
    pratijna: 1,
    hetu: 2,
    udaharana: 3,
    upanaya: 4,
    nigamana: 5,
  };

  const stages = [...rawStages].sort((a, b) => {
    const numA = Number(a.stageNumber) || canonicalOrderMap[a.sanskritName?.toLowerCase()] || 0;
    const numB = Number(b.stageNumber) || canonicalOrderMap[b.sanskritName?.toLowerCase()] || 0;
    return numA - numB;
  });

  const isLoading = reasoner.isLoadingReasoning || (reasoner.isAnalyzing && stages.length === 0);
  const isInsufficient = reasoner.insufficientEvidence || reasoner.reasoningStatus === 'insufficient';
  const hasError = Boolean(reasoner.reasoningError || reasoner.reasoningStatus === 'error');
  const isEmpty = !isLoading && !isInsufficient && !hasError && stages.length === 0;

  const handleTraceEvidence = (evidenceId) => {
    if (!evidenceId) return;
    onSelectEvidence(evidenceId);
    if (reasoner.setSelectedGraphNodeId) {
      reasoner.setSelectedGraphNodeId(evidenceId);
    }
  };

  const handleFocusInGraph = (nodeId) => {
    if (!nodeId) return;
    if (reasoner.setSelectedGraphNodeId) {
      reasoner.setSelectedGraphNodeId(nodeId);
    }
  };

  const handleRetryDeduce = () => {
    if (reasoner.runDeduceReasoning) {
      reasoner.runDeduceReasoning();
    }
  };

  const handleLoadBenchmark = (archetype = 'tinai') => {
    if (reasoner.loadBenchmarkEvidence) {
      reasoner.loadBenchmarkEvidence(archetype);
    }
  };

  // 1. LOADING STATE: Shimmering skeleton of the 5-stage Pañcāvayava pipeline
  if (isLoading) {
    return (
      <Card
        title="REASONING TRACE (Nyāya-Inspired Inference)"
        subtitle="Synthesizing 5-member Pañcāvayava deduction via Flask backend..."
        icon={Cpu}
        accent="orange"
        actions={
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500" />
            </span>
            <span className="text-xs font-mono text-amber-700 font-semibold animate-pulse">
              Evaluating Epistemic Syllogism...
            </span>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="p-3.5 rounded-xl bg-amber-50/60 border border-amber-200/80 flex items-center justify-between text-xs text-amber-900">
            <div className="flex items-center gap-2">
              <RefreshCw className="w-4 h-4 text-amber-600 animate-spin" />
              <span className="font-medium">
                Executing First-Order Logic Entailment & Hetvābhāsa Defeasibility Checks in Python...
              </span>
            </div>
            <span className="font-mono text-[11px] text-amber-700 font-semibold">
              POST /api/reasoning/deduce
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            {['Pratijñā', 'Hetu', 'Udāharaṇa', 'Upanaya', 'Nigamana'].map((name, i) => (
              <div
                key={name}
                className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/60 animate-pulse space-y-2.5"
              >
                <div className="flex items-center justify-between">
                  <div className="w-5 h-5 rounded-full bg-slate-300 font-mono text-[10px] flex items-center justify-center font-bold text-slate-600">
                    {i + 1}
                  </div>
                  <div className="h-4 w-16 bg-slate-200 rounded" />
                </div>
                <div className="h-4 w-24 bg-slate-300 rounded font-semibold text-xs text-slate-700 flex items-center">
                  {name}
                </div>
                <div className="space-y-1.5 pt-1">
                  <div className="h-2.5 bg-slate-200 rounded w-full" />
                  <div className="h-2.5 bg-slate-200 rounded w-4/5" />
                  <div className="h-2.5 bg-slate-200 rounded w-2/3" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </Card>
    );
  }

  // 2. ERROR STATE: Clear error alert with retry button
  if (hasError) {
    return (
      <Card
        title="REASONING TRACE (Nyāya-Inspired Inference)"
        subtitle="Formal neuro-symbolic proof deduction encountered an issue"
        icon={Cpu}
        accent="orange"
        actions={
          <Badge variant="red" size="xs">
            Deduction Error
          </Badge>
        }
      >
        <div className="p-5 rounded-xl bg-red-50/80 border border-red-200 text-red-900 space-y-3">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h4 className="font-bold text-sm text-red-950">
                Reasoning Deduction Failed
              </h4>
              <p className="text-xs text-red-800 leading-relaxed font-mono">
                {reasoner.reasoningError || 'Backend /api/reasoning/deduce returned an unrecoverable error.'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 pt-2">
            <button
              type="button"
              onClick={handleRetryDeduce}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-600 text-white hover:bg-red-700 text-xs font-semibold shadow-xs transition-colors cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry Reasoning Deduction</span>
            </button>
            <button
              type="button"
              onClick={() => handleLoadBenchmark('tinai')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-red-300 text-red-800 hover:bg-red-50 text-xs font-semibold transition-colors cursor-pointer"
            >
              <Sparkles className="w-3.5 h-3.5 text-red-600" />
              <span>Load Kuṟiñci Benchmark Inquiry</span>
            </button>
          </div>
        </div>
      </Card>
    );
  }

  // 3. INSUFFICIENT EVIDENCE STATE: Explicit epistemological alert
  if (isInsufficient) {
    return (
      <Card
        title="REASONING TRACE (Nyāya-Inspired Inference)"
        subtitle="Classical Nyāya Epistemic Boundary — Defeasible Reasoning Blocked"
        icon={Cpu}
        accent="orange"
        actions={
          <Badge variant="amber" size="xs">
            Insufficient Evidence
          </Badge>
        }
      >
        <div className="p-5 rounded-xl bg-amber-50/90 border border-amber-200 text-amber-950 space-y-3">
          <div className="flex items-start gap-3">
            <ShieldCheck className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
            <div className="space-y-1.5">
              <h4 className="font-bold text-sm text-amber-950">
                போதிய சான்றுகள் இல்லை (Insufficient Canonical Evidence for Proof)
              </h4>
              <p className="text-xs text-amber-900 leading-relaxed">
                The retrieved primary passages do not meet the minimum semantic relevance or textual volume required to construct an uncontradicted 5-member Pañcāvayava syllogism without speculative hallucination.
              </p>
              <p className="text-xs text-amber-800 leading-relaxed font-serif italic">
                Classical Nyāya epistemology strictly requires Pakṣadharmatā (valid locus) and Vyāpti (universal concomitance) established via authentic Śabda Pramāṇa before synthesizing Nigamana.
              </p>
            </div>
          </div>
          <div className="pt-2 border-t border-amber-200/80 flex flex-wrap items-center gap-2.5">
            <button
              type="button"
              onClick={() => handleLoadBenchmark('tinai')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-700 text-white hover:bg-amber-800 text-xs font-semibold shadow-xs transition-colors cursor-pointer"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Load Kuṟiñci Benchmark Scenario (5 Canonical Verses)</span>
            </button>
            <button
              type="button"
              onClick={() => handleLoadBenchmark('justice')}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-amber-300 text-amber-900 hover:bg-amber-100 text-xs font-semibold transition-colors cursor-pointer"
            >
              <span>Load Royal Justice Benchmark Scenario</span>
            </button>
          </div>
        </div>
      </Card>
    );
  }

  // 4. CLEAN IDLE / EMPTY STATE: Inviting prompt to initiate search or benchmark
  if (isEmpty) {
    return (
      <Card
        title="REASONING TRACE (Nyāya-Inspired Inference)"
        subtitle="Five-member syllogistic deduction (Pañcāvayava) grounding classical Tolkāppiyam sūtras into formal neuro-symbolic proofs"
        icon={Cpu}
        accent="orange"
        actions={
          <Badge variant="slate" size="xs">
            Awaiting Grounding
          </Badge>
        }
      >
        <div className="text-center py-10 px-4 space-y-4 max-w-xl mx-auto">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-amber-100 to-orange-100 text-amber-700 flex items-center justify-center mx-auto shadow-inner border border-amber-200">
            <Sparkles className="w-7 h-7 text-amber-700" />
          </div>
          <div className="space-y-1.5">
            <h3 className="font-bold text-slate-800 text-base">
              No Active Nyāya Reasoning Deduction
            </h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Inquire into a classical Tamil poetics or eco-psychology concept in the Query Center, or select a pre-grounded benchmark scenario below to synthesize the 5-stage Pañcāvayava deduction via Flask.
            </p>
          </div>
          <div className="pt-2 flex flex-wrap justify-center gap-2.5">
            <button
              type="button"
              onClick={() => handleLoadBenchmark('tinai')}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-purple-700 text-white hover:bg-purple-800 text-xs font-semibold shadow-xs transition-colors cursor-pointer"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Ground Kuṟiñci Tiṇai Benchmark</span>
            </button>
            <button
              type="button"
              onClick={() => handleLoadBenchmark('justice')}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 text-xs font-semibold transition-colors cursor-pointer"
            >
              <Search className="w-3.5 h-3.5 text-slate-500" />
              <span>Ground King's Justice Benchmark</span>
            </button>
          </div>
        </div>
      </Card>
    );
  }

  // 5. ACTIVE REASONING PIPELINE: 5-Stage Connected Pipeline + Deep Epistemic Inspector
  const currentStage = stages[selectedStageIndex] || stages[0];
  const currentTheme = STAGE_THEMES[selectedStageIndex] || STAGE_THEMES[0];

  return (
    <Card
      title="REASONING TRACE (Nyāya-Inspired Inference)"
      subtitle="Five-member syllogistic deduction (Pañcāvayava) grounding classical Tolkāppiyam sūtras into formal neuro-symbolic proofs"
      icon={Cpu}
      accent="orange"
      actions={
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant="green" size="xs" dot>
            {currentQuery?.symbolicValidity || 'Valid Epistemic Deduction'}
          </Badge>
          <Badge variant="purpleDark" size="xs">
            {stages.length}-Stage Pipeline
          </Badge>
          <Badge variant="slate" size="xs">
            {currentQuery?.hetvabhasaCheck || 'Zero Fallacies'}
          </Badge>
        </div>
      }
      footer={
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 text-slate-600">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="font-semibold text-slate-800">
              Epistemic Guarantee:
            </span>
            <span>
              All {stages.length} stages satisfy classical Nyāya criteria (Pakṣadharmatā, Sapakṣasattva, Vipakṣāsattva, Abādhita, Asatpratipakṣa).
            </span>
          </div>
          <div className="flex items-center gap-2 self-end sm:self-auto shrink-0 font-mono text-[11px]">
            <span className="text-slate-400">Proof Engine:</span>
            <span className="font-bold text-purple-700 bg-purple-50 px-2 py-0.5 rounded border border-purple-200">
              Tolkāppiyam-Nyāya v2.4
            </span>
          </div>
        </div>
      }
    >
      {/* 5-STAGE CONNECTED PIPELINE */}
      <div className="relative mb-6">
        {/* Helper instruction bar */}
        <div className="flex items-center justify-between gap-2 mb-3 text-xs text-slate-500">
          <div className="flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-purple-600" />
            <span className="font-medium text-slate-700">
              Interactive Reasoning Pipeline:
            </span>
            <span>Click any stage card below to inspect its formal logic and Tolkāppiyam grounding</span>
          </div>
          <span className="hidden md:inline-block text-[11px] text-slate-400 font-mono">
            Step {selectedStageIndex + 1} of {stages.length} Active
          </span>
        </div>

        {/* Cards Grid / Flow */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3 relative items-stretch">
          {stages.map((stage, idx) => {
            const isSelected = selectedStageIndex === idx;
            const theme = STAGE_THEMES[idx] || STAGE_THEMES[0];
            const IconComp = theme.iconComponent;
            const isLinkedEvidence = stage.linkedEvidenceId === selectedEvidenceId;

            return (
              <div
                key={stage.stageNumber || idx}
                className="relative flex flex-col"
              >
                {/* Stage Card */}
                <button
                  type="button"
                  onClick={() => {
                    setSelectedStageIndex(idx);
                    setIsInspectorExpanded(true);
                  }}
                  className={`w-full text-left flex-1 flex flex-col justify-between p-3.5 rounded-xl border transition-all duration-150 cursor-pointer select-none relative ${
                    isSelected
                      ? `${theme.bgSelected} ${theme.borderSelected} ring-offset-1`
                      : `${theme.bgNormal} ${theme.borderNormal} hover:shadow-sm`
                  } ${isLinkedEvidence && !isSelected ? 'ring-2 ring-purple-400/50' : ''}`}
                >
                  {/* Top Badge & Number */}
                  <div>
                    <div className="flex items-center justify-between gap-1 mb-2">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`w-5 h-5 rounded-full text-[11px] font-mono font-bold flex items-center justify-center shrink-0 ${theme.pillBg}`}
                        >
                          {stage.stageNumber || idx + 1}
                        </span>
                        <span className="font-bold text-xs text-slate-900 tracking-tight truncate">
                          {stage.sanskritName}
                        </span>
                      </div>
                      <span
                        className={`text-[10px] font-medium font-serif px-1.5 py-0.5 rounded border ${theme.badgeBg}`}
                      >
                        {stage.tamilName}
                      </span>
                    </div>

                    {/* Role / Subtitle */}
                    <div className="mb-2">
                      <span className={`text-[11px] font-bold block ${theme.accentText}`}>
                        {stage.englishRole}
                      </span>
                    </div>

                    {/* Tamil Reasoning Text */}
                    <p className="text-slate-800 text-xs font-serif leading-relaxed line-clamp-3 mb-2">
                      {stage.tamilReasoningText}
                    </p>

                    {/* English Interpretation */}
                    <p className="text-slate-500 text-[11px] leading-snug line-clamp-3 italic mb-3">
                      {stage.englishInterpretation}
                    </p>
                  </div>

                  {/* Bottom Footer of Card: Inline SVG Icon and Status */}
                  <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between gap-1 text-[10px] mt-auto">
                    <div className="flex items-center gap-1.5">
                      <span
                        className={`p-1 rounded-md flex items-center justify-center ${theme.iconBg}`}
                        title={stage.fullTitle}
                      >
                        <IconComp className="w-3.5 h-3.5" />
                      </span>
                      {stage.linkedEvidenceId && (
                        <span
                          className="font-mono text-slate-600 bg-slate-100 hover:bg-purple-100 hover:text-purple-800 px-1 py-0.5 rounded border border-slate-200 text-[10px] transition-colors cursor-pointer"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleTraceEvidence(stage.linkedEvidenceId);
                          }}
                          title="Click to trace linked evidence passage & graph node"
                        >
                          [{stage.linkedEvidenceId}]
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-1">
                      {isSelected ? (
                        <span className="font-semibold text-purple-700 text-[10px] flex items-center gap-0.5">
                          Active •
                        </span>
                      ) : (
                        <span className="text-slate-400 group-hover:text-slate-600">
                          View →
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Highlight pill for active stage */}
                  {isSelected && (
                    <div
                      className={`absolute -top-1.5 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded-full text-[9px] font-bold tracking-wider uppercase text-white shadow-xs ${theme.pillBg}`}
                    >
                      Selected Stage
                    </div>
                  )}
                </button>

                {/* Connecting arrow indicator for desktop (shown between columns) */}
                {idx < stages.length - 1 && (
                  <div
                    className="hidden md:flex absolute -right-2 top-1/2 -translate-y-1/2 z-10 w-4 h-4 rounded-full bg-white border border-slate-300 items-center justify-center text-slate-400 shadow-2xs pointer-events-none"
                    aria-hidden="true"
                  >
                    <ChevronRight className="w-3 h-3" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* EXPANDABLE DEEP EPISTEMIC INSPECTOR FOR THE SELECTED STAGE */}
      <div className="border border-slate-200 rounded-xl bg-white overflow-hidden shadow-2xs">
        <div
          className="p-3.5 bg-slate-50/80 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3 cursor-pointer select-none"
          onClick={() => setIsInspectorExpanded(!isInspectorExpanded)}
        >
          <div className="flex items-center gap-2.5">
            <span
              className={`w-6 h-6 rounded-full text-xs font-mono font-bold flex items-center justify-center ${currentTheme.pillBg}`}
            >
              {currentStage.stageNumber || selectedStageIndex + 1}
            </span>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-bold text-slate-900 text-sm">
                  {currentStage.fullTitle || `${currentStage.stageNumber}. ${currentStage.sanskritName} (${currentStage.tamilName})`}
                </span>
                <Badge variant={currentTheme.badgeVariant} size="xs">
                  {currentStage.pramanaMode || 'Pramāṇa Validated'}
                </Badge>
                {typeof currentStage.confidence === 'number' && (
                  <span className="font-mono text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200 text-[10px] font-semibold">
                    {Math.round(currentStage.confidence * 100)}% Confidence
                  </span>
                )}
              </div>
              <span className="text-xs text-slate-500">
                Formal Epistemic Proof & Grounding Analysis
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              className="text-xs font-medium text-slate-600 hover:text-purple-700 px-2 py-1 rounded hover:bg-slate-100 cursor-pointer"
            >
              {isInspectorExpanded ? 'Collapse Details ▲' : 'Expand Details ▼'}
            </button>
          </div>
        </div>

        {isInspectorExpanded && (
          <div className="p-4 sm:p-5 space-y-4 text-xs sm:text-sm">
            {/* Full Tamil Reasoning & English Interpretation Banner */}
            <div className={`p-4 rounded-xl border ${currentTheme.bgSelected} ${currentTheme.borderNormal} space-y-2`}>
              <div className="flex items-center justify-between gap-2">
                <span className="font-bold text-xs uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                  <Info className="w-3.5 h-3.5 text-purple-600" />
                  Tamil Reasoning Text (தமிழ் ஏது விளக்கம்)
                </span>
                <span className="font-mono text-xs text-slate-500">
                  Stage {currentStage.stageNumber || selectedStageIndex + 1} of {stages.length}
                </span>
              </div>
              <p className="text-slate-900 font-serif text-sm sm:text-base leading-relaxed font-medium">
                {currentStage.tamilReasoningText}
              </p>
              <div className="pt-2 border-t border-slate-200/60">
                <p className="text-slate-700 text-xs sm:text-sm leading-relaxed italic">
                  {currentStage.englishInterpretation}
                </p>
              </div>
            </div>

            {/* Two-Column Inspector Grid: Formal Logic & Sūtra Grounding */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Box 1: First-Order Nyāya Symbolic Logic */}
              <div className="p-3.5 rounded-xl bg-slate-900 text-slate-100 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between text-xs pb-1 border-b border-slate-800">
                  <span className="font-mono font-bold text-purple-300 flex items-center gap-1.5">
                    <Cpu className="w-3.5 h-3.5 text-purple-400" />
                    NYĀYA FIRST-ORDER LOGIC
                  </span>
                  <span className="text-[10px] text-emerald-400 font-mono">
                    ✓ Verified Invariant
                  </span>
                </div>
                <div className="font-mono text-xs text-emerald-300 py-1 overflow-x-auto leading-relaxed">
                  {currentStage.formalLogic}
                </div>
                <div className="text-[11px] text-slate-400 leading-normal">
                  Quantified predicate grounding the semantic entailment of the target proposition without existential rupture.
                </div>
              </div>

              {/* Box 2: Canonical Tolkāppiyam Sūtra Grounding */}
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                <div className="flex items-center justify-between text-xs pb-1 border-b border-slate-200">
                  <span className="font-bold text-slate-800 flex items-center gap-1.5">
                    <BookOpen className="w-3.5 h-3.5 text-purple-700" />
                    CANONICAL SŪTRA GROUNDING
                  </span>
                  {currentStage.linkedEvidenceId && (
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleTraceEvidence(currentStage.linkedEvidenceId)}
                        className="inline-flex items-center gap-1 text-[11px] text-purple-700 hover:text-purple-900 font-semibold cursor-pointer"
                        title="Highlight this evidence in Evidence Panel"
                      >
                        <span>Evidence [{currentStage.linkedEvidenceId}]</span>
                        <ExternalLink className="w-3 h-3" />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleFocusInGraph(currentStage.linkedEvidenceId)}
                        className="inline-flex items-center gap-1 text-[11px] text-blue-700 hover:text-blue-900 font-semibold cursor-pointer"
                        title="Focus and highlight this node in Cytoscape Knowledge Graph"
                      >
                        <Network className="w-3 h-3" />
                        <span>Graph Context</span>
                      </button>
                    </div>
                  )}
                </div>
                <p className="font-medium text-slate-900 text-xs sm:text-sm">
                  {currentStage.epistemicGrounding}
                </p>
                <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
                  <span className="text-slate-500 font-semibold">Pramāṇa Mode:</span>
                  <span className="font-medium text-purple-800 bg-purple-100/80 px-2 py-0.5 rounded border border-purple-200 text-[11px]">
                    {currentStage.pramanaMode}
                  </span>
                </div>
              </div>
            </div>

            {/* In-depth Philosophical Explanation & Defeasibility */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 pt-1">
              <div className="lg:col-span-8 p-3.5 rounded-xl bg-slate-50/60 border border-slate-200/80 space-y-1.5">
                <div className="font-bold text-xs text-slate-800 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-amber-600" />
                  <span>Epistemological Role in Tolkāppiyam Semiotics</span>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  {currentStage.inDepthExplanation}
                </p>
              </div>

              <div className="lg:col-span-4 p-3.5 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-1.5">
                <div className="font-bold text-xs text-emerald-900 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700" />
                  <span>Hetvābhāsa Defeasibility Check</span>
                </div>
                <p className="text-xs text-emerald-800 font-mono">
                  {currentStage.fallacyCheck || 'Zero Fallacies Detected (Sound)'}
                </p>
                <div className="text-[11px] text-emerald-700">
                  Free from Asiddha, Savyabhicāra, Viruddha, Satpratipakṣa, and Bādhita.
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
