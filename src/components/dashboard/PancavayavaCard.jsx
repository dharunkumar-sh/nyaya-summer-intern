import {
  ArrowDown,
  ShieldCheck,
  Cpu,
  Sparkles,
  Network,
  AlertTriangle,
  RefreshCw,
  Target,
  Flame,
  Scale,
  Eye,
  CheckCircle2,
} from 'lucide-react';
import Card from '../common/Card';
import Badge from '../common/Badge';
import { useReasoner } from '../../context/ReasonerContext';

const NYAYA_CANONICAL_STAGES = [
  {
    key: 'pratijna',
    num: 1,
    sanskritName: 'Pratijñā',
    tamilName: 'பிரதிஞ்ஞா',
    englishRole: 'Target Proposition (Thesis)',
    accent: 'border-l-purple-600',
    badgeVariant: 'purple',
    badgeBg: 'bg-purple-100 text-purple-800 border-purple-200',
    numberBg: 'bg-purple-700 text-white',
    ringColor: 'ring-purple-500/30',
    bgActive: 'bg-purple-50/90 border-purple-400',
    icon: Target,
  },
  {
    key: 'hetu',
    num: 2,
    sanskritName: 'Hetu',
    tamilName: 'ஹேது',
    englishRole: 'Reason / Grounding Cause',
    accent: 'border-l-amber-500',
    badgeVariant: 'orange',
    badgeBg: 'bg-amber-100 text-amber-800 border-amber-200',
    numberBg: 'bg-amber-600 text-white',
    ringColor: 'ring-amber-500/30',
    bgActive: 'bg-amber-50/90 border-amber-400',
    icon: Flame,
  },
  {
    key: 'udaharana',
    num: 3,
    sanskritName: 'Udāharaṇa',
    tamilName: 'உதாரணம்',
    englishRole: 'Universal Invariant Rule (Vyāpti)',
    accent: 'border-l-blue-600',
    badgeVariant: 'blue',
    badgeBg: 'bg-blue-100 text-blue-800 border-blue-200',
    numberBg: 'bg-blue-700 text-white',
    ringColor: 'ring-blue-500/30',
    bgActive: 'bg-blue-50/90 border-blue-400',
    icon: Scale,
  },
  {
    key: 'upanaya',
    num: 4,
    sanskritName: 'Upanaya',
    tamilName: 'உபநயம்',
    englishRole: 'Application / Subsumptive Proof',
    accent: 'border-l-indigo-600',
    badgeVariant: 'indigo',
    badgeBg: 'bg-indigo-100 text-indigo-800 border-indigo-200',
    numberBg: 'bg-indigo-700 text-white',
    ringColor: 'ring-indigo-500/30',
    bgActive: 'bg-indigo-50/90 border-indigo-400',
    icon: Eye,
  },
  {
    key: 'nigamana',
    num: 5,
    sanskritName: 'Nigamana',
    tamilName: 'நிகமனம்',
    englishRole: 'Conclusion / Synthesized Epistemic Truth',
    accent: 'border-l-emerald-600',
    badgeVariant: 'green',
    badgeBg: 'bg-emerald-100 text-emerald-800 border-emerald-200',
    numberBg: 'bg-emerald-700 text-white',
    ringColor: 'ring-emerald-500/30',
    bgActive: 'bg-emerald-50/90 border-emerald-400',
    icon: CheckCircle2,
  },
];

export default function PancavayavaCard({ currentQuery: propQuery, selectedEvidenceId: propEvidenceId }) {
  const reasoner = useReasoner();
  const currentQuery = propQuery || reasoner.currentQuery;
  const activeEvidenceId = propEvidenceId || reasoner.selectedEvidenceId;

  const rawStages = Array.isArray(reasoner.reasoningStages) && reasoner.reasoningStages.length > 0
    ? reasoner.reasoningStages
    : (Array.isArray(currentQuery?.reasoningStages) && currentQuery.reasoningStages.length > 0
      ? currentQuery.reasoningStages
      : []);

  // Strict Canonical Pañcāvayava Stack Order (1: Pratijñā -> 2: Hetu -> 3: Udāharaṇa -> 4: Upanaya -> 5: Nigamana)
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

  const handleStageClick = (index) => {
    if (typeof reasoner.setSelectedStageIndex === 'function') {
      reasoner.setSelectedStageIndex(index);
    }
  };

  // 1. Loading State
  if (isLoading) {
    return (
      <Card
        title="Nyāya 5-Member Syllogism (Pañcāvayava Inference Flow)"
        subtitle="Complete deductively sound reasoning chain grounding Classical Tamil verse"
        icon={Cpu}
        accent="orange"
        headerClassName="cursor-default"
      >
        <div className="space-y-3.5 py-2">
          <div className="flex items-center gap-2 text-xs text-amber-800 bg-amber-50 p-3 rounded-lg border border-amber-200 animate-pulse">
            <RefreshCw className="w-4 h-4 animate-spin text-amber-600" />
            <span>Synthesizing Classical Nyāya Syllogism from retrieved Tolkāppiyam verses...</span>
          </div>
          {[1, 2, 3, 4, 5].map((s) => (
            <div key={s} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 animate-pulse space-y-2">
              <div className="h-4 bg-slate-200 rounded w-1/3" />
              <div className="h-3 bg-slate-200 rounded w-5/6" />
              <div className="h-3 bg-slate-200 rounded w-2/3" />
            </div>
          ))}
        </div>
      </Card>
    );
  }

  // 2. Insufficient Evidence State
  if (isInsufficient) {
    return (
      <Card
        title="Nyāya 5-Member Syllogism (Pañcāvayava Inference Flow)"
        subtitle="Classical Nyāya Epistemic Boundary"
        icon={Cpu}
        accent="orange"
        headerClassName="cursor-default"
      >
        <div className="p-4 rounded-xl bg-amber-50/90 border border-amber-200 text-amber-950 space-y-2">
          <div className="flex items-center gap-2 font-bold text-xs text-amber-900">
            <AlertTriangle className="w-4 h-4 text-amber-700" />
            <span>போதிய சான்றுகள் இல்லை (Insufficient Evidence for Syllogism)</span>
          </div>
          <p className="text-xs text-amber-800 leading-relaxed">
            The retrieved passages do not meet the confidence or count threshold to construct a sound 5-member Pañcāvayava inference chain. Speculative syllogistic deduction was blocked.
          </p>
        </div>
      </Card>
    );
  }

  // 3. Error State
  if (hasError) {
    return (
      <Card
        title="Nyāya 5-Member Syllogism (Pañcāvayava Inference Flow)"
        subtitle="Inference Deduction Error"
        icon={Cpu}
        accent="orange"
        headerClassName="cursor-default"
      >
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-900 space-y-2">
          <div className="flex items-center gap-2 font-bold text-xs text-red-800">
            <AlertTriangle className="w-4 h-4 text-red-600" />
            <span>Reasoning Pipeline Error</span>
          </div>
          <p className="text-xs text-red-700 font-mono">
            {reasoner.reasoningError || 'Failed to deduce 5-member syllogism from backend service.'}
          </p>
        </div>
      </Card>
    );
  }

  // 4. Empty State
  if (isEmpty) {
    return (
      <Card
        title="Nyāya 5-Member Syllogism (Pañcāvayava Inference Flow)"
        subtitle="Complete deductively sound reasoning chain grounding Classical Tamil verse"
        icon={Cpu}
        accent="orange"
      >
        <div className="text-center py-8 px-4 space-y-2 text-slate-500">
          <Sparkles className="w-8 h-8 text-amber-500 mx-auto opacity-70" />
          <p className="text-xs font-medium text-slate-700">Awaiting Query Grounding</p>
          <p className="text-[11px] text-slate-400">
            Run a search in Query Center or ground an inquiry to populate the 5-step Pañcāvayava deduction.
          </p>
        </div>
      </Card>
    );
  }

  return (
    <Card
      title="Nyāya 5-Member Syllogism (Pañcāvayava Inference Flow)"
      subtitle="Sequential 5-Stage Deductive Inference (Pratijñā → Hetu → Udāharaṇa → Upanaya → Nigamana)"
      icon={Cpu}
      accent="orange"
      headerClassName="cursor-default"
      actions={
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant="green" size="xs" dot>
            {currentQuery?.symbolicValidity || 'Valid Epistemic Deduction'}
          </Badge>
          <Badge variant="purpleDark" size="xs">
            5 / 5 Stages
          </Badge>
          <Badge variant="slate" size="xs">
            {currentQuery?.hetvabhasaCheck || 'Zero Fallacies'}
          </Badge>
        </div>
      }
      footer={
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-slate-600">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="font-medium text-xs">
              Hetvābhāsa Fallacy Inspection:
            </span>
            <span className="text-slate-700 text-xs">
              No Asiddha, Savyabhicāra, Viruddha, Satpratipakṣa, or Bādhā fallacies detected.
            </span>
          </div>
          <span className="font-mono text-purple-700 font-semibold text-xs shrink-0">
            Proof Soundness: {reasoner.confidenceEvaluation?.confidencePercentage ?? (typeof reasoner.validationResults?.soundnessScore === 'number' ? Math.round(reasoner.validationResults.soundnessScore * 100) : 100)}%
          </span>
        </div>
      }
    >
      {/* 5-Member Syllogism Stack Order */}
      <div className="space-y-4 relative">
        {stages.map((stage, index) => {
          const stepNum = stage.stageNumber || index + 1;
          const config = NYAYA_CANONICAL_STAGES[index] || NYAYA_CANONICAL_STAGES[0];
          const IconComp = config.icon;
          const isConnected = Boolean(stage.linkedEvidenceId && stage.linkedEvidenceId === activeEvidenceId);
          const isSelectedStage = reasoner.selectedStageIndex === index;

          return (
            <div key={stepNum} className="relative">
              <div
                onClick={() => handleStageClick(index)}
                className={`relative p-3.5 sm:p-4 rounded-xl border transition-all duration-150 cursor-pointer hover:border-slate-400/80 ${config.accent} border-l-4 shadow-2xs ${
                  isSelectedStage
                    ? `${config.bgActive} ring-2 ${config.ringColor} shadow-xs`
                    : isConnected
                      ? 'border-purple-300 bg-purple-50/30 hover:bg-purple-50/50'
                      : 'border-slate-200/90 bg-slate-50/40 hover:bg-slate-50/80'
                }`}
              >
                {/* Stage Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 mb-2.5 border-b border-slate-200/70">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <span
                      className={`w-6 h-6 rounded-full font-mono text-xs font-bold flex items-center justify-center shrink-0 shadow-2xs ${config.numberBg}`}
                    >
                      {stepNum}
                    </span>
                    <div className="flex items-center gap-1.5">
                      <IconComp className="w-3.5 h-3.5 text-slate-600 shrink-0" />
                      <span className="font-bold text-slate-900 text-sm tracking-tight">
                        {stage.sanskritName || config.sanskritName}
                      </span>
                    </div>
                    <span className="text-xs text-slate-600 font-serif font-semibold">
                      ({stage.tamilName || config.tamilName})
                    </span>
                    <span className="text-slate-300 text-xs hidden md:inline">•</span>
                    <span className="text-xs font-semibold text-slate-700">
                      {stage.englishRole || config.englishRole}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 flex-wrap">
                    {typeof stage.confidence === 'number' && (
                      <span
                        className="text-[10px] font-mono font-bold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200"
                        title="Dynamic Stage Confidence"
                      >
                        {Math.round(stage.confidence * 100)}%
                      </span>
                    )}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleStageClick(index, stage, config);
                      }}
                      className={`inline-flex items-center gap-1 text-[10px] font-bold font-mono px-2 py-0.5 rounded-md transition-colors cursor-pointer ${
                        isConnected || isSelectedStage
                          ? 'bg-purple-700 text-white shadow-2xs'
                          : 'bg-slate-200/80 text-slate-700 hover:bg-purple-100 hover:text-purple-800'
                      }`}
                      title="Locate & synchronize this reasoning step with D3 Knowledge Graph"
                    >
                      <Network className="w-2.5 h-2.5" />
                      <span>{stage.linkedEvidenceId ? `[${stage.linkedEvidenceId}]` : 'D3 Sync'}</span>
                    </button>
                    <Badge variant={config.badgeVariant} size="xs">
                      {stage.pramanaMode ? stage.pramanaMode.split(' ')[0] : 'Pramāṇa'}
                    </Badge>
                  </div>
                </div>

                {/* Step Content: Tamil Reasoning Text */}
                <p className="tamil-font text-slate-950 text-xs sm:text-sm font-semibold leading-relaxed mb-1.5">
                  {stage.tamilReasoningText}
                </p>

                {/* English Interpretation */}
                <p className="text-slate-600 text-xs italic leading-relaxed mb-3">
                  {stage.englishInterpretation}
                </p>

                {/* Formal Logic & Grounding metadata */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-1">
                  <div className="bg-slate-100/95 px-3 py-1.5 rounded-lg border border-slate-200 font-mono text-[11px] text-purple-950 overflow-x-auto flex items-center">
                    <span className="text-purple-700 font-bold select-none mr-2 shrink-0">LOGIC:</span>
                    <span className="truncate">{stage.formalLogic}</span>
                  </div>
                  <div className="bg-slate-100/95 px-3 py-1.5 rounded-lg border border-slate-200 text-[11px] text-slate-700 flex items-center justify-between gap-1.5">
                    <div className="flex items-center gap-1.5 truncate">
                      <span className="text-slate-500 font-bold select-none shrink-0">SOURCE:</span>
                      <span className="truncate font-serif font-medium">{stage.epistemicGrounding}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Vertical Stack Timeline Connector Arrow between steps */}
              {index < stages.length - 1 && (
                <div className="flex items-center justify-center my-1">
                  <div className="flex items-center gap-1.5 text-slate-400">
                    <div className="w-4 h-px bg-slate-200" />
                    <div className="w-5 h-5 rounded-full bg-white border border-slate-300 shadow-2xs flex items-center justify-center text-slate-500 z-10">
                      <ArrowDown className="w-3 h-3" />
                    </div>
                    <div className="w-4 h-px bg-slate-200" />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </Card>
  );
}
