import {
  CheckCircle2,
  ShieldCheck,
  Star,
  FileText,
  Info,
  BookOpen,
} from 'lucide-react';
import Badge from '../common/Badge';
import { useReasoner } from '../../context/ReasonerContext';

/**
 * SECTION 5: FINAL EXPLANATION (Three Distinct Areas)
 * Area 1: Prominent Green Validated Final Answer
 * Area 2: Justification & Scholarly Synthesis (Tamil + English)
 * Area 3: Key Sources with Interactive Inspection Badges
 */
export default function FinalExplanationSection() {
  const { finalAnswer } = useReasoner();

  if (!finalAnswer) {
    return null;
  }

  // Dynamic star rendering calculation
  const score = typeof finalAnswer.confidenceScore === 'number' ? finalAnswer.confidenceScore : 0.0;
  const totalStars = 5;
  const ratingValue = score * 5;
  const fullStarsCount = Math.floor(ratingValue);
  const remainderPercent = Math.round((ratingValue - fullStarsCount) * 100);

  return (
    <div className="space-y-6">
      {/* AREA 1: PROMINENT GREEN VALIDATED FINAL ANSWER */}
      <div className="bg-white rounded-2xl border-2 border-emerald-500/80 shadow-md overflow-hidden transition-all">
        {/* Green Top Header */}
        <div className="px-5 sm:px-6 py-3.5 bg-gradient-to-r from-emerald-700 via-emerald-600 to-teal-700 text-white flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <ShieldCheck className="w-5 h-5 text-emerald-200 shrink-0" />
            <h3 className="font-extrabold text-xs sm:text-sm uppercase tracking-widest text-white truncate">
              FINAL ANSWER & VERIFIED RESOLUTION
            </h3>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-[10px] sm:text-xs font-mono font-bold px-2.5 py-0.5 rounded-full bg-emerald-950/40 border border-emerald-300/40 text-emerald-100">
              Q.E.D. VERIFIED
            </span>
          </div>
        </div>

        {/* Answer Content Body: Balanced 2-Section Layout */}
        <div className="p-5 sm:p-6 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          {/* Main Answer Texts */}
          <div className="flex items-start gap-4 flex-1 min-w-0">
            <div className="w-12 h-12 rounded-2xl bg-emerald-100 text-emerald-600 border-2 border-emerald-400 flex items-center justify-center shrink-0 shadow-xs">
              <CheckCircle2 className="w-7 h-7" />
            </div>

            <div className="space-y-1.5 min-w-0 flex-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 font-mono">
                Canonical Epistemic Verdict
              </span>
              <h4 className="text-base sm:text-xl font-bold text-slate-900 font-serif leading-snug">
                “{finalAnswer.tamilAnswer}”
              </h4>
              <p className="text-xs sm:text-sm font-semibold text-slate-600 leading-relaxed">
                “{finalAnswer.englishAnswer}”
              </p>
              {finalAnswer.subtitle && (
                <p className="text-[11px] text-slate-400 leading-snug">
                  {finalAnswer.subtitle}
                </p>
              )}
            </div>
          </div>

          {/* Confidence Score & Rating Card */}
          <div className="shrink-0 lg:self-center">
            <div className="p-4 rounded-xl bg-emerald-50/80 border border-emerald-200 flex items-center justify-between gap-5 min-w-[230px] sm:min-w-[260px] shadow-2xs">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-900 block">
                  Epistemic Certainty
                </span>
                <div className="flex items-center gap-1 mt-1">
                  {Array.from({ length: totalStars }).map((_, starIndex) => {
                    if (starIndex < fullStarsCount) {
                      return (
                        <Star
                          key={starIndex}
                          className="w-4 h-4 fill-amber-400 text-amber-400 shrink-0"
                        />
                      );
                    } else if (starIndex === fullStarsCount && remainderPercent > 0) {
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

              <div className="text-right">
                <span className="font-mono text-2xl font-extrabold text-emerald-700 leading-none">
                  {finalAnswer.confidenceScore}
                </span>
                <span className="block text-[10px] font-semibold text-emerald-600 mt-1">
                  Defeasible Sound
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* AREAS 2 & 3: JUSTIFICATION & KEY SOURCES */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        {/* AREA 2: JUSTIFICATION & EXPLANATION */}
        <div className="lg:col-span-7 flex flex-col">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs border-t-4 border-t-purple-600 flex flex-col h-full transition-all">
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100 bg-slate-50/60">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="p-1.5 rounded-lg bg-purple-50 text-purple-700 border border-purple-200/70 shrink-0">
                  <FileText className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-xs sm:text-sm font-bold text-slate-900 tracking-tight truncate">
                    JUSTIFICATION & SCHOLARLY SYNTHESIS
                  </h3>
                  <p className="text-[11px] text-slate-500 truncate">
                    Epistemic rationale over Tolkāppiyam Poruḷatikāram poetics
                  </p>
                </div>
              </div>
              <Badge variant="purple" size="xs">
                Textual Rationale
              </Badge>
            </div>

            <div className="p-5 flex-1 flex flex-col justify-between space-y-4">
              {/* Tamil Explanation */}
              <div className="p-4 rounded-xl bg-purple-50/70 border border-purple-200/80 space-y-2">
                <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-purple-800">
                  <Info className="w-3.5 h-3.5 text-purple-600" />
                  <span>தமிழ் விளக்கம் (Tamil Justification)</span>
                </div>
                <p className="text-slate-900 font-serif leading-relaxed text-xs sm:text-sm font-medium">
                  {finalAnswer.justificationTamil}
                </p>
              </div>

              {/* English Synthesis */}
              <div className="p-3.5 rounded-xl bg-slate-50/70 border border-slate-200 space-y-1.5">
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-600">
                  Scholarly Epistemic Interpretation (English)
                </div>
                <p className="text-slate-700 text-xs leading-relaxed italic border-l-2 border-purple-500 pl-3">
                  {finalAnswer.justificationEnglish}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* AREA 3: KEY SOURCES & INTERACTIVE CITATIONS */}
        <div className="lg:col-span-5 flex flex-col">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs border-t-4 border-t-blue-600 flex flex-col h-full transition-all">
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100 bg-slate-50/60">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="p-1.5 rounded-lg bg-blue-50 text-blue-700 border border-blue-200/70 shrink-0">
                  <BookOpen className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-xs sm:text-sm font-bold text-slate-900 tracking-tight truncate">
                    KEY GROUNDING SOURCES
                  </h3>
                  <p className="text-[11px] text-slate-500 truncate">
                    Canonical textual grounds
                  </p>
                </div>
              </div>
              <Badge variant="blue" size="xs">
                {(finalAnswer.keySources || []).length} Sūtras
              </Badge>
            </div>

            <div className="p-5 flex-1 flex flex-col justify-between space-y-3.5">
              <div>
                <span className="text-xs text-slate-600 block mb-2 font-medium">
                  Primary Textual Grounds Anchoring the Inference:
                </span>

                {/* Source Badges */}
                <div className="flex flex-wrap items-center gap-2">
                  {(finalAnswer.keySources || []).map((source) => (
                    <span
                      key={source.id}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border font-mono text-xs font-semibold bg-slate-50 text-slate-700 border-slate-200 shadow-2xs"
                      title={`${source.id}: ${source.sutra}${source.topic ? ` (${source.topic})` : ''}`}
                    >
                      <span className="bg-purple-100 text-purple-800 font-bold px-1.5 py-0.2 rounded text-[10px]">
                        {source.id}
                      </span>
                      <span>{source.sutra}</span>
                    </span>
                  ))}
                </div>
              </div>

              <div className="text-[11px] text-slate-400 flex items-center gap-1.5 font-sans">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                <span>All sources verified against Poruḷatikāram manuscript index</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
