import { useState } from 'react';
import {
  Gauge,
  CheckCircle2,
  BrainCircuit,
  Clock,
  AlertTriangle,
  Layers,
  Scale,
  ScrollText,
  GitFork,
  Star,
  Info,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
} from 'lucide-react';
import Card from '../common/Card';
import Badge from '../common/Badge';
import { useReasoner } from '../../context/ReasonerContext';
import { getConfidenceLevel, FACTOR_METADATA } from '../../services/confidenceService';

const FACTOR_ICONS = {
  evidence_relevance: Layers,
  source_provenance: ScrollText,
  retrieval_strength: GitFork,
  premise_support: Scale,
  reasoning_consistency: BrainCircuit,
  validation_status: CheckCircle2,
};

export default function EpistemicMetricsCard({ currentQuery: propQuery }) {
  const {
    currentQuery: ctxQuery,
    queryStats,
    finalAnswer,
    validationResults,
    dashboardSummary,
    evidenceRecords,
    confidenceEvaluation,
  } = useReasoner();

  const [showFactorDetails, setShowFactorDetails] = useState(false);
  const currentQuery = propQuery || ctxQuery || {};

  // 1. Dynamic Confidence: derived from real-time confidence evaluation or fallback
  const evalData = confidenceEvaluation || currentQuery?.confidenceEvaluation || null;
  const rawScore = typeof evalData?.confidenceScore === 'number'
    ? evalData.confidenceScore
    : (typeof finalAnswer?.confidenceScore === 'number' ? finalAnswer.confidenceScore : 0.0);

  const confidenceScore = Number(rawScore.toFixed(4));
  const confidencePct = Math.round(confidenceScore * 100);
  const starsCount = evalData?.confidenceStars ?? (typeof finalAnswer?.starsCount === 'number' ? finalAnswer.starsCount : Number((confidenceScore * 5).toFixed(1)));
  const levelInfo = evalData?.levelInfo || getConfidenceLevel(confidenceScore);
  const hasConfidence = confidenceScore > 0 && finalAnswer?.status !== 'insufficient_evidence';

  // 2. Symbolic Soundness: derived from validation results or dashboard soundness rate
  const soundnessRate = validationResults?.soundnessScore ?? validationResults?.soundness ?? dashboardSummary?.reasoning_and_soundness?.soundness_rate;
  const soundnessPct = typeof soundnessRate === 'number'
    ? Math.round(soundnessRate * 100)
    : (finalAnswer?.status === 'sufficient' ? 100 : null);

  // 3. Inference Latency: derived from active queryStats or benchmark average
  const latencyStr = queryStats?.latencyMs
    ? `${queryStats.latencyMs} ms`
    : dashboardSummary?.search_and_rag?.average_inference_ms
    ? `${dashboardSummary.search_and_rag.average_inference_ms} ms`
    : null;

  // 4. 6 Dynamic Supporting Factors
  const factors = evalData?.factors || {};
  const penalties = Array.isArray(evalData?.penalties) ? evalData.penalties : [];

  // 5. Empirical Pramāṇa distribution calculated dynamically from active evidence
  let pratyaksaCount = 0;
  let sabdaCount = 0;
  let anumanaCount = 0;
  let upamanaCount = 0;

  (evidenceRecords || []).forEach((e) => {
    const t = String(e.evidenceType || e.category || e.pramana || '').toLowerCase();
    if (t.includes('direct') || t.includes('pratyak') || t.includes('primary')) {
      pratyaksaCount++;
    } else if (t.includes('infer') || t.includes('anuma')) {
      anumanaCount++;
    } else if (t.includes('anal') || t.includes('upama')) {
      upamanaCount++;
    } else {
      sabdaCount++;
    }
  });

  const totalPramana = pratyaksaCount + sabdaCount + anumanaCount + upamanaCount;
  const pctAnumana = totalPramana > 0 ? Math.round((anumanaCount / totalPramana) * 100) : 0;
  const pctPratyaksa = totalPramana > 0 ? Math.round((pratyaksaCount / totalPramana) * 100) : 0;
  const pctSabda = totalPramana > 0 ? Math.round((sabdaCount / totalPramana) * 100) : 0;
  const pctUpamana = totalPramana > 0 ? Math.max(0, 100 - pctAnumana - pctPratyaksa - pctSabda) : 0;

  return (
    <Card
      title="Epistemic Verification & Dynamic Confidence Metrics"
      subtitle="Real-time multi-dimensional validation across retrieval, provenance, premises, and reasoning"
      icon={Gauge}
      accent="green"
      actions={
        <div className="flex items-center gap-2">
          <Badge
            variant={levelInfo.badgeVariant || (hasConfidence ? 'green' : 'slate')}
            size="xs"
            dot={hasConfidence}
          >
            {levelInfo.labelEnglish} ({levelInfo.labelTamil})
          </Badge>
          <span className="font-mono text-xs font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
            {hasConfidence ? `${confidencePct}%` : '0%'}
          </span>
        </div>
      }
    >
      {/* 3 Top Primary Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5 mb-4">
        {/* Metric 1: Real-Time Dynamic Confidence */}
        <div className={`p-3.5 rounded-xl border transition-all ${levelInfo.bgColor || 'bg-purple-50/60 border-purple-200/80'}`}>
          <div className="flex items-center justify-between text-xs font-semibold mb-1">
            <span className="flex items-center gap-1.5 text-slate-800">
              <BrainCircuit className="w-3.5 h-3.5 text-purple-700" />
              Dynamic Confidence
            </span>
            <div className="flex items-center gap-1 font-mono font-bold text-sm text-slate-900">
              <span>{hasConfidence ? `${confidencePct}%` : '0%'}</span>
              <div className="flex items-center text-amber-500 text-[11px] ml-1" title={`${starsCount} / 5 Stars`}>
                <Star className="w-3 h-3 fill-amber-400 text-amber-500" />
                <span className="ml-0.5 text-[10px] text-slate-600 font-sans">{starsCount}</span>
              </div>
            </div>
          </div>
          <div className="w-full bg-slate-200/80 h-2 rounded-full overflow-hidden mt-2">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                confidencePct >= 85
                  ? 'bg-emerald-600'
                  : confidencePct >= 70
                  ? 'bg-blue-600'
                  : confidencePct >= 50
                  ? 'bg-amber-500'
                  : confidencePct >= 25
                  ? 'bg-orange-500'
                  : 'bg-red-500'
              }`}
              style={{ width: `${confidencePct}%` }}
            />
          </div>
          <div className="flex items-center justify-between text-[10px] mt-1.5 text-slate-600">
            <span className="truncate">{levelInfo.labelEnglish}</span>
            <span className="font-serif text-slate-500 truncate ml-1">({levelInfo.labelTamil})</span>
          </div>
        </div>

        {/* Metric 2: Symbolic Soundness */}
        <div className="p-3.5 rounded-xl bg-emerald-50/60 border border-emerald-200/80">
          <div className="flex items-center justify-between text-xs text-emerald-800 font-semibold mb-1">
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              Symbolic Soundness
            </span>
            <span className="font-mono font-bold text-sm text-emerald-950">
              {soundnessPct !== null ? `${soundnessPct}%` : '--'}
            </span>
          </div>
          <div className="w-full bg-emerald-200 h-2 rounded-full overflow-hidden mt-2">
            <div
              className="bg-emerald-600 h-full rounded-full transition-all duration-500"
              style={{ width: `${soundnessPct || 0}%` }}
            />
          </div>
          <span className="text-[10px] text-emerald-700/80 mt-1.5 block">
            Nyāya First-Order Consistency (Hetvābhāsa-Free)
          </span>
        </div>

        {/* Metric 3: Proof Latency */}
        <div className="p-3.5 rounded-xl bg-blue-50/60 border border-blue-200/80">
          <div className="flex items-center justify-between text-xs text-blue-800 font-semibold mb-1">
            <span className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-blue-600" />
              Proof Latency
            </span>
            <span className="font-mono font-bold text-sm text-blue-950">
              {latencyStr || '--'}
            </span>
          </div>
          <div className="w-full bg-blue-200 h-2 rounded-full overflow-hidden mt-2">
            <div
              className="bg-blue-600 h-full rounded-full transition-all duration-500"
              style={{ width: latencyStr ? '45%' : '0%' }}
            />
          </div>
          <span className="text-[10px] text-blue-700/80 mt-1.5 block">
            End-to-End Resolution Time
          </span>
        </div>
      </div>

      {/* Active Epistemic Penalties Banner (if insufficient, ungrounded, or conflicting) */}
      {penalties.length > 0 && (
        <div className="mb-4 p-3 rounded-xl bg-amber-50 border border-amber-300 text-amber-900 text-xs space-y-2">
          <div className="flex items-center gap-2 font-bold text-amber-950">
            <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0" />
            <span>Epistemic Gating & Penalties Active ({penalties.length}):</span>
          </div>
          <div className="space-y-1 pl-6">
            {penalties.map((p, idx) => (
              <div key={idx} className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-[11px]">
                <div className="flex items-center gap-1.5">
                  <span className="font-mono font-bold text-amber-800 bg-amber-100 px-1.5 py-0.5 rounded border border-amber-200">
                    {p.penalty_name}
                  </span>
                  <span className="text-amber-900">{p.reason}</span>
                </div>
                <div className="flex items-center gap-2 shrink-0 font-mono text-[10px]">
                  <span className="text-red-700 font-bold">-{Math.round((p.deduction || 0) * 100)}%</span>
                  {p.cap !== null && p.cap !== undefined && (
                    <span className="text-amber-800 bg-amber-200/60 px-1.5 py-0.5 rounded font-semibold">
                      Cap: {Math.round(p.cap * 100)}%
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 6 Supporting Factors Accordion / Grid */}
      <div className="mb-4 rounded-xl border border-slate-200 bg-slate-50/70 p-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-purple-700" />
            <span className="text-xs font-bold text-slate-800">
              Supporting Epistemic Factors (6 Dynamic Dimensions)
            </span>
            <span className="text-[10px] text-slate-500 font-serif">
              (சான்றாதாரக் காரணிகள்)
            </span>
          </div>
          <button
            type="button"
            onClick={() => setShowFactorDetails((prev) => !prev)}
            className="flex items-center gap-1 text-[11px] font-semibold text-purple-700 hover:text-purple-900 transition-colors cursor-pointer px-2 py-1 rounded hover:bg-purple-50"
          >
            <span>{showFactorDetails ? 'Hide Rationale' : 'Inspect Rationale'}</span>
            {showFactorDetails ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>

        {/* Factors 6-Column Meter Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 mt-3">
          {Object.entries(FACTOR_METADATA).map(([factorKey, meta]) => {
            const factorData = factors[factorKey] || {};
            const rawScoreVal = typeof factorData.raw_score === 'number' ? factorData.raw_score : 0.0;
            const scorePct = Math.round(rawScoreVal * 100);
            const status = factorData.status || (scorePct >= 70 ? 'PASS' : scorePct >= 40 ? 'MODERATE' : 'WEAK');
            const IconComp = FACTOR_ICONS[factorKey] || Info;

            return (
              <div
                key={factorKey}
                className="p-2.5 bg-white rounded-lg border border-slate-200 shadow-2xs flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between text-[10px] font-bold text-slate-700 mb-1">
                    <div className="flex items-center gap-1 truncate" title={meta.name}>
                      <IconComp className="w-3 h-3 text-purple-700 shrink-0" />
                      <span className="truncate">{meta.name.split(' ')[0]}</span>
                    </div>
                    <span className="font-mono text-purple-900">{scorePct}%</span>
                  </div>
                  <div className="text-[9px] text-slate-500 font-serif truncate mb-1.5" title={meta.tamilName}>
                    {meta.tamilName}
                  </div>
                </div>

                <div>
                  <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden mb-1.5">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        scorePct >= 70 ? 'bg-emerald-500' : scorePct >= 40 ? 'bg-amber-500' : 'bg-red-400'
                      }`}
                      style={{ width: `${scorePct}%` }}
                    />
                  </div>

                  <div className="flex items-center justify-between text-[9px] text-slate-400 font-mono">
                    <span>w={(meta.weight * 100).toFixed(0)}%</span>
                    <span
                      className={`px-1 py-0.2 rounded text-[8px] font-bold ${
                        status === 'PASS'
                          ? 'bg-emerald-100 text-emerald-800'
                          : status === 'MODERATE' || status === 'PARTIAL'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {status}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Detailed Factors Rationale Explanations (when expanded) */}
        {showFactorDetails && (
          <div className="mt-3 pt-3 border-t border-slate-200/80 grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
            {Object.entries(FACTOR_METADATA).map(([factorKey, meta]) => {
              const factorData = factors[factorKey] || {};
              const details = factorData.details || meta.description;
              const IconComp = FACTOR_ICONS[factorKey] || Info;

              return (
                <div key={factorKey} className="p-2.5 rounded-lg bg-white border border-slate-200 space-y-1">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 font-bold text-slate-800">
                      <IconComp className="w-3.5 h-3.5 text-purple-700" />
                      <span>{meta.name}</span>
                      <span className="font-serif text-[11px] text-slate-500 font-normal">({meta.tamilName})</span>
                    </div>
                    <span className="font-mono text-[10px] text-slate-500">
                      Weight: {(meta.weight * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-600 leading-relaxed font-sans">
                    {details}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Pramāṇa Distribution Breakdown Bar */}
      <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs">
        <div className="flex items-center justify-between mb-2">
          <span className="font-semibold text-slate-700">
            Pramāṇa Epistemic Weight Breakdown:
          </span>
          <span className="text-[11px] text-slate-500 font-mono">
            {totalPramana > 0 ? `${totalPramana} Active Grounds (Sum = 100%)` : 'Awaiting Evidence Grounding'}
          </span>
        </div>

        {totalPramana > 0 ? (
          <>
            <div className="h-3 w-full rounded-full overflow-hidden flex bg-slate-200">
              {pctAnumana > 0 && (
                <div
                  className="bg-amber-500 h-full transition-all duration-500"
                  style={{ width: `${pctAnumana}%` }}
                  title={`Anumāna (Inferential): ${pctAnumana}%`}
                />
              )}
              {pctPratyaksa > 0 && (
                <div
                  className="bg-emerald-500 h-full transition-all duration-500"
                  style={{ width: `${pctPratyaksa}%` }}
                  title={`Pratyakṣa (Direct Textual): ${pctPratyaksa}%`}
                />
              )}
              {pctSabda > 0 && (
                <div
                  className="bg-blue-500 h-full transition-all duration-500"
                  style={{ width: `${pctSabda}%` }}
                  title={`Śabda (Canonical Authority): ${pctSabda}%`}
                />
              )}
              {pctUpamana > 0 && (
                <div
                  className="bg-purple-500 h-full transition-all duration-500"
                  style={{ width: `${pctUpamana}%` }}
                  title={`Upamāna (Analogical): ${pctUpamana}%`}
                />
              )}
            </div>
            <div className="flex flex-wrap items-center justify-between gap-2 mt-2 text-[11px] text-slate-600">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                <span>Anumāna ({pctAnumana}%)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                <span>Pratyakṣa ({pctPratyaksa}%)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
                <span>Śabda ({pctSabda}%)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-purple-500" />
                <span>Upamāna ({pctUpamana}%)</span>
              </div>
            </div>
          </>
        ) : (
          <p className="text-[11px] text-slate-500 italic py-1">
            No active evidence retrieved. Run an inquiry to dynamically calibrate Pramāṇa epistemic distribution across canonical sūtras.
          </p>
        )}
      </div>
    </Card>
  );
}
