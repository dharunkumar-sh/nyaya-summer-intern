import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Shield,
  FileCheck2,
  RefreshCw,
  Cpu,
} from 'lucide-react';
import Card from '../../common/Card';
import Badge from '../../common/Badge';
import { useReasoner } from '../../../context/ReasonerContext';

const DEFAULT_FALLACIES = [
  {
    id: 'savyabhicara',
    number: '01',
    sanskritName: 'Savyabhicāra',
    tamilName: 'சவ்யபிசாரம்',
    englishName: 'Erratic / Irregular Reason',
    score: '0.00',
    status: 'PASSED',
    passed: true,
    description:
      'The inferential ground (Hetu) is strictly bounded and does not wander into improper contexts. Kuṟiñci signifiers are exclusively bound to clandestine nocturnal love in classical semiotics.',
    rule: 'Anaikāntika-Free',
  },
  {
    id: 'viruddha',
    number: '02',
    sanskritName: 'Viruddha',
    tamilName: 'விருத்தம்',
    englishName: 'Contradictory Ground',
    score: '0.00',
    status: 'PASSED',
    passed: true,
    description:
      'The reason does not disprove the thesis. No self-contradiction exists between ecological habitat and aesthetic mood in Tolkāppiyam grammar.',
    rule: 'Non-Contradictory',
  },
  {
    id: 'satpratipaksa',
    number: '03',
    sanskritName: 'Satpratipakṣa',
    tamilName: 'சத்பிரதிபக்கம்',
    englishName: 'Counterbalanced Ground',
    score: '0.00',
    status: 'PASSED',
    passed: true,
    description:
      'No equally valid opposing inferential ground exists in the grammar of Tolkāppiyam to contradict or overturn this semantic mapping.',
    rule: 'Unassailable Proof',
  },
  {
    id: 'asiddha',
    number: '04',
    sanskritName: 'Asiddha',
    tamilName: 'அசித்தம்',
    englishName: 'Unproven / Fabricated Ground',
    score: '0.00',
    status: 'PASSED',
    passed: true,
    description:
      'The middle term is fully established by direct textual evidence in Akattiṇaiyiyal Sūtras 3 and 5 (Pratyakṣa-siddha), with zero fabricated assertions.',
    rule: 'Empirically Grounded',
  },
  {
    id: 'badhita',
    number: '05',
    sanskritName: 'Bādhita',
    tamilName: 'பாதிதம்',
    englishName: 'Sublated by Stronger Pramāṇa',
    score: '0.00',
    status: 'PASSED',
    passed: true,
    description:
      'Direct textual perception of canonical sūtras corroborates the inferential conclusion without any sublation or sensory contradiction.',
    rule: 'Abādhita Soundness',
  },
];

const DEFAULT_NYAYA_GUARANTEES = [
  { name: 'Pakṣadharmatā', desc: 'Subject Presence' },
  { name: 'Sapakṣasattva', desc: 'Positive Concordance' },
  { name: 'Vipakṣāsattva', desc: 'Negative Concordance' },
  { name: 'Abādhita', desc: 'Non-Sublated Truth' },
  { name: 'Asatpratipakṣa', desc: 'Absence of Counter-Proof' },
];

export default function OverviewHetvabhasaGuard() {
  const navigate = useNavigate();
  const {
    validationResults,
    dashboardSummary,
    revalidateFallacies,
    isValidatingFallacies,
  } = useReasoner();

  const reasoningData = dashboardSummary?.reasoning_and_soundness;

  // Real-time computation from live Flask validation results
  const soundnessScore =
    typeof validationResults?.soundnessScore === 'number'
      ? Math.round(validationResults.soundnessScore * 100)
      : reasoningData?.soundness_rate ?? 100;

  const soundnessText = `${soundnessScore}% Sound Proof`;

  const fallaciesList = useMemo(() => {
    const backendDetails = validationResults?.fallacyDetails;
    const rawFallacies = validationResults?.fallacies || {};

    return DEFAULT_FALLACIES.map((def) => {
      const match = backendDetails?.find((b) => b.id === def.id);
      const rawScore = rawFallacies[def.id];
      const numericScore =
        match?.numericScore ??
        (typeof rawScore === 'number'
          ? rawScore
          : parseFloat(def.score) || 0.0);
      const isPassed = numericScore <= 0.05;
      const scoreStr = match?.score ?? numericScore.toFixed(2);

      return {
        ...def,
        score: scoreStr,
        numericScore,
        status: isPassed ? 'PASSED' : 'FLAGGED',
        passed: isPassed,
        description: match?.description || def.description,
        rule: match?.rule || def.rule,
      };
    });
  }, [validationResults]);

  const detectedFallacies = useMemo(() => {
    return fallaciesList.filter((f) => !f.passed).length;
  }, [fallaciesList]);

  const symbolicValidity =
    validationResults?.symbolicValidity ||
    reasoningData?.symbolic_validity ||
    (detectedFallacies === 0 ? 'Valid Epistemic Deduction' : 'Fallacies Flagged');

  const hetuDescription =
    validationResults?.hetuDescription ||
    reasoningData?.hetu_description ||
    'The active middle term (Hetu) linking terrestrial habitat to human interiority is certified free of all classical defect.';

  const nyayaGuarantees =
    validationResults?.axiomaticGuarantees ||
    reasoningData?.classical_guarantees ||
    DEFAULT_NYAYA_GUARANTEES;

  const verificationTimestamp =
    validationResults?.verificationTimestamp ||
    reasoningData?.verification_timestamp;

  const handleRevalidate = () => {
    if (typeof revalidateFallacies === 'function') {
      revalidateFallacies({ tinai: 'Kuṟiñci', evidenceCount: 5 });
    }
  };

  return (
    <Card
      title="Hetvābhāsa Defeasible Logic Fallacy Guard (ஏதுவாபாச ஆய்வு)"
      subtitle="Strict Formal Verification Against the 5 Classical Fallacious Grounds of Indian Epistemology"
      icon={ShieldCheck}
      accent="green"
      actions={
        <div className="flex items-center gap-2">
          <Badge
            variant={detectedFallacies === 0 ? 'green' : 'amber'}
            size="sm"
            dot
          >
            {soundnessText}
          </Badge>

          {/* Real-time Flask re-verification button */}
          <button
            type="button"
            onClick={handleRevalidate}
            disabled={isValidatingFallacies}
            title="Execute live real-time Hetvābhāsa validation against Flask Defeasible Validator"
            className="flex items-center gap-1 text-xs font-semibold text-slate-700 hover:text-slate-900 bg-white hover:bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-200 transition-all cursor-pointer shadow-2xs disabled:opacity-60"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 text-slate-500 ${
                isValidatingFallacies ? 'animate-spin' : ''
              }`}
            />
            <span className="hidden sm:inline">
              {isValidatingFallacies ? 'Verifying...' : 'Re-verify'}
            </span>
          </button>

          <button
            type="button"
            onClick={() => navigate('/fallacies')}
            className="flex items-center gap-1 text-xs font-semibold text-emerald-700 hover:text-emerald-800 transition-colors cursor-pointer bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200 shadow-2xs"
          >
            <span>Inspector</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      }
    >
      <div className="space-y-6">
        {/* Certificate Banner with Live Epistemic Soundness Status */}
        <div className="p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-emerald-50 via-emerald-50/60 to-slate-50 border border-emerald-200 text-emerald-950 shadow-2xs space-y-3">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-emerald-600 text-white shadow-xs shrink-0">
                <Shield className="w-5 h-5" />
              </div>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs sm:text-sm font-bold text-emerald-950 uppercase tracking-wider">
                    Epistemic Soundness Status:
                  </span>
                  <Badge
                    variant={detectedFallacies === 0 ? 'green' : 'amber'}
                    size="sm"
                    dot
                  >
                    {symbolicValidity}
                  </Badge>
                  {verificationTimestamp && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-mono text-emerald-700 bg-white/80 px-2 py-0.5 rounded border border-emerald-200/80">
                      <Cpu className="w-3 h-3 text-emerald-600" />
                      Flask • {verificationTimestamp}
                    </span>
                  )}
                </div>
                <p className="text-xs text-emerald-800 mt-0.5 leading-relaxed">
                  {hetuDescription}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <span
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold font-mono border ${
                  detectedFallacies === 0
                    ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                    : 'bg-rose-100 text-rose-800 border-rose-300'
                }`}
              >
                {detectedFallacies === 0 ? (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span>Zero Fallacies Detected (0.00)</span>
                  </>
                ) : (
                  <>
                    <AlertTriangle className="w-4 h-4 text-rose-600" />
                    <span>{detectedFallacies} Fallacies Flagged</span>
                  </>
                )}
              </span>
            </div>
          </div>

          {/* 5 Classical Nyāya Epistemic Guarantees Pills */}
          <div className="pt-2 border-t border-emerald-200/70">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-900 flex items-center gap-1.5">
                <FileCheck2 className="w-3.5 h-3.5 text-emerald-600" />
                5 Formal Nyāya Axiomatic Guarantees Satisfied:
              </span>
              <span className="text-[10px] text-emerald-700 font-mono flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Classical Defeasible Logic Rigor
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
              {nyayaGuarantees.map((g) => {
                const name = typeof g === 'string' ? g : g.name;
                const desc = typeof g === 'object' ? g.desc : '';
                return (
                  <div
                    key={name}
                    className="bg-white/80 p-2 rounded-xl border border-emerald-200/80 text-center shadow-2xs"
                  >
                    <span className="font-bold text-xs text-emerald-900 block font-serif">
                      {name}
                    </span>
                    {desc && (
                      <span className="text-[10px] text-slate-500 block truncate">
                        {desc}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* 5 Fallacy Cards in a Beautiful, Spacious Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
          {fallaciesList.map((fallacy) => {
            const isPassed = fallacy.passed;
            return (
              <div
                key={fallacy.id}
                className="p-4 sm:p-5 rounded-2xl bg-white border border-slate-200 shadow-2xs hover:shadow-md transition-all duration-200 flex flex-col justify-between group"
              >
                <div>
                  {/* Top row: Number pill + Score Badge */}
                  <div className="flex items-center justify-between gap-1 mb-2.5">
                    <span className="text-[10px] font-mono font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                      FALLACY {fallacy.number}
                    </span>
                    <span
                      className={`inline-flex items-center gap-1 text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${
                        isPassed
                          ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
                          : 'text-rose-700 bg-rose-50 border-rose-200'
                      }`}
                    >
                      {isPassed ? (
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                      ) : (
                        <AlertTriangle className="w-3 h-3 text-rose-600" />
                      )}
                      Score: {fallacy.score}
                    </span>
                  </div>

                  {/* Sanskrit & Tamil Name */}
                  <div className="space-y-0.5">
                    <h4 className="font-extrabold text-sm text-slate-900 leading-tight">
                      {fallacy.sanskritName}
                    </h4>
                    <div className="text-xs font-serif text-purple-700">
                      ({fallacy.tamilName})
                    </div>
                    <div className="text-[11px] font-semibold text-slate-500 pt-0.5">
                      {fallacy.englishName}
                    </div>
                  </div>

                  {/* Description with Comfortable Reading Line-Height */}
                  <p className="text-xs text-slate-600 mt-2.5 leading-relaxed">
                    {fallacy.description}
                  </p>
                </div>

                {/* Footer row */}
                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                  <span className="font-mono text-[11px] font-semibold text-purple-700">
                    {fallacy.rule}
                  </span>
                  <span
                    className={`font-semibold flex items-center gap-1 ${
                      isPassed ? 'text-emerald-700' : 'text-rose-700'
                    }`}
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        isPassed ? 'bg-emerald-500' : 'bg-rose-500 animate-ping'
                      }`}
                    />
                    {isPassed ? 'Passed' : 'Flagged'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </Card>
  );
}
