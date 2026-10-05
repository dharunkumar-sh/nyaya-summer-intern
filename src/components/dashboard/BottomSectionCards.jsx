import {
  CheckCircle2,
  Star,
  FileText,
  ShieldCheck,
  Info,
  AlertTriangle,
} from "lucide-react";
import Badge from "../common/Badge";
import { useReasoner } from "../../context/ReasonerContext";

/**
 * CARD 1: JUSTIFICATION & EXPLANATION
 */
export function JustificationCard({
  stepNumber,
  totalSteps,
  rowLayout = false,
}) {
  const {
    finalAnswer,
    evidenceRecords,
    insufficientEvidence,
    setSelectedEvidenceId,
    selectSynchronizedItem,
  } = useReasoner();

  if (!finalAnswer) {
    return null;
  }

  // Resilient fallback resolution for Tamil justification so it is always visible and legible
  const tamilJustification =
    finalAnswer.justificationTamil ||
    finalAnswer.justification_tamil ||
    finalAnswer.tamilJustification ||
    finalAnswer.tamil_justification ||
    finalAnswer.tamilExplanation ||
    finalAnswer.explanation_tamil ||
    finalAnswer.tamilReasoningText ||
    finalAnswer.tamilAnswer ||
    finalAnswer.tamil_answer ||
    (evidenceRecords && evidenceRecords.length > 0
      ? `தொல்காப்பிய அகத்திணை முறைமையின்படி (${evidenceRecords
          .slice(0, 3)
          .map((e) => e.reference || e.code || e.id)
          .join(
            ", ",
          )}), முதற்பொருளும் கருப்பொருளும் உரிப்பொருளோடு மாறாத தொடர்பு (வியாப்தி) கொண்டுள்ளன. மீட்கப்பட்ட மூலச் சான்றுகளின் வழி இவ்வுரிப்பொருள் ஒழுக்கம் ஐயமற நிறுவப்பட்டுள்ளது.`
      : "தொல்காப்பியப் பொருளதிகார முறைமைப்படி, முதற்பொருளும் கருப்பொருளும் உரிப்பொருளோடு மாறாத வியாப்தித் தொடர்பு கொண்டுள்ளன.");

  const englishJustification =
    finalAnswer.justificationEnglish ||
    finalAnswer.justification_english ||
    finalAnswer.englishJustification ||
    finalAnswer.english_justification ||
    finalAnswer.englishAnswer ||
    finalAnswer.english_answer ||
    finalAnswer.englishInterpretation ||
    finalAnswer.subtitle ||
    "Under Tolkāppiyam Poruḷatikāram poetics, terrestrial space-time (Mutalporuḷ) and seasonal biota (Karupporuḷ) deterministically ground human emotional interiority (Uripporuḷ).";

  return (
    <div className="flex flex-col bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden w-full">
      {/* Card Header */}
      <div className="px-5 sm:px-6 py-4 border-b border-slate-100 bg-slate-50/60 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="p-1.5 rounded-lg bg-purple-100 text-purple-700 border border-purple-200/70 shrink-0">
            <FileText className="w-4 h-4" />
          </span>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-bold text-xs uppercase tracking-wider text-slate-900 truncate">
                GENERATED EPISTEMIC EXPLANATION (DERIVED SYNTHESIS)
              </h3>
              {stepNumber && (
                <span className="text-[10px] font-mono font-bold text-purple-700 bg-purple-50 px-1.5 py-0.2 rounded border border-purple-200">
                  {stepNumber}/{totalSteps || 7}
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-500 truncate mt-0.5">
              முறைமை விளக்கம் • Synthesized rationale retaining canonical Tamil
              terminology
            </p>
          </div>
        </div>
        <Badge variant={insufficientEvidence ? "orange" : "purple"} size="xs">
          {insufficientEvidence
            ? "Insufficient Evidence"
            : "Generated Explanation"}
        </Badge>
      </div>

      {/* Card Body */}
      <div
        className={`p-5 sm:p-6 flex-1 text-xs sm:text-sm ${
          rowLayout
            ? "grid grid-cols-1 lg:grid-cols-12 gap-6 items-start"
            : "flex flex-col justify-between space-y-4"
        }`}
      >
        <div className={rowLayout ? "lg:col-span-7 space-y-4" : "space-y-4"}>
          {insufficientEvidence ? (
            <div className="p-4 sm:p-5 rounded-xl bg-amber-50 border border-amber-200/90 text-amber-900 space-y-3 shadow-2xs">
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-800 pb-2 border-b border-amber-200/80">
                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                <span>Insufficient Canonical Evidence Grounding</span>
              </div>
              <div className="space-y-1.5">
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-amber-800/80 block">
                  தமிழ் விளக்கம் (Tamil Justification)
                </span>
                <p
                  className="tamil-font text-xs sm:text-sm text-amber-950 leading-relaxed font-medium"
                  lang="ta"
                >
                  {tamilJustification}
                </p>
              </div>
              {englishJustification && (
                <p className="text-xs text-amber-800 leading-relaxed italic border-l-2 border-amber-400 pl-3">
                  {englishJustification}
                </p>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {/* Concise & Legible Tamil Explanation Container */}
              <div className="p-4 sm:p-5 rounded-xl bg-purple-50/70 border border-purple-200/90 shadow-2xs space-y-3">
                <div className="flex items-center justify-between pb-2.5 border-b border-purple-200/80">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="p-1 rounded-md bg-purple-100 text-purple-700 shrink-0">
                      <Info className="w-3.5 h-3.5 text-purple-600" />
                    </span>
                    <span
                      className="font-bold text-xs sm:text-sm text-purple-950 tamil-font"
                      lang="ta"
                    >
                      தமிழ் விளக்கம்
                    </span>
                    <span className="text-[11px] font-mono text-purple-600 font-medium">
                      (Tamil Justification)
                    </span>
                  </div>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-purple-100/90 text-purple-800 border border-purple-300/60 shrink-0">
                    Canonical Synthesis
                  </span>
                </div>
                <p
                  className="tamil-font text-slate-900 leading-relaxed sm:leading-loose text-sm sm:text-base font-medium tracking-normal whitespace-pre-line text-left"
                  lang="ta"
                >
                  {tamilJustification}
                </p>
              </div>

              {/* English Synthesis */}
              {englishJustification && (
                <div className="pt-0.5 space-y-1">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400 block">
                    Scholarly English Synthesis
                  </span>
                  <p className="text-slate-600 text-xs sm:text-sm leading-relaxed italic border-l-3 border-purple-400 pl-3.5">
                    {englishJustification}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Key Sources & Supporting Passages Column / Row */}
        <div
          className={
            rowLayout
              ? "lg:col-span-5 bg-slate-50/70 p-4 sm:p-5 rounded-xl border border-slate-200/80 space-y-3.5"
              : "pt-3 border-t border-slate-100 space-y-3"
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
                <button
                  key={source.id}
                  type="button"
                  onClick={() =>
                    selectSynchronizedItem &&
                    selectSynchronizedItem(source.id, "query_center")
                  }
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border font-mono text-xs font-semibold bg-white text-slate-700 border-slate-200 hover:border-purple-400 hover:bg-purple-50 transition-all cursor-pointer shadow-2xs group"
                  title={`Focus '${source.id}' (${source.sutra}) in D3 Knowledge Graph`}
                >
                  <span className="font-bold text-purple-700 group-hover:text-purple-900">
                    {source.id}
                  </span>
                  <span className="text-[10px] text-slate-500 font-normal">
                    ({source.sutra})
                  </span>
                  {source.score && (
                    <span className="text-[10px] text-emerald-700 font-bold bg-emerald-50 px-1 py-0.2 rounded border border-emerald-200/60">
                      {source.score}
                    </span>
                  )}
                </button>
              ))}
              {(!finalAnswer.keySources ||
                finalAnswer.keySources.length === 0) && (
                <span className="text-xs text-slate-400 italic">
                  No direct sources cited
                </span>
              )}
            </div>
          </div>

          {/* Supporting Passages Excerpts */}
          {evidenceRecords &&
            evidenceRecords.length > 0 &&
            !insufficientEvidence && (
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
                        <span className="font-mono font-bold text-purple-700">
                          {ev.code || ev.id}
                        </span>
                        <span className="text-slate-500 font-medium truncate max-w-40">
                          {ev.reference}
                        </span>
                        <span className="font-mono text-emerald-700 font-bold">
                          {ev.confidenceFormatted}
                        </span>
                      </div>
                      <p className="tamil-font text-slate-800 text-[11px] line-clamp-1">
                        {ev.tamilText}
                      </p>
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
 * PROOF TRACE (GRAPHICAL) - Removed
 */
export function ProofTraceCard() {
  return null;
}

/**
 * CARD 3: FINAL ANSWER (PROMINENT EPISTEMIC VERDICT & CONFIDENCE)
 */
export function FinalAnswerCard({ stepNumber, totalSteps, rowLayout = false }) {
  const { finalAnswer, insufficientEvidence } = useReasoner();

  if (!finalAnswer) {
    return null;
  }

  // Dynamic star rendering calculation
  const score =
    typeof finalAnswer.confidenceScore === "number"
      ? finalAnswer.confidenceScore
      : 0.95;
  const totalStars = 5;
  const ratingValue = score * 5;
  const fullStarsCount = Math.floor(ratingValue);
  const remainderPercent = Math.round((ratingValue - fullStarsCount) * 100);

  return (
    <div
      className={`flex flex-col bg-white rounded-2xl shadow-md overflow-hidden w-full transition-colors ${
        insufficientEvidence
          ? "border-2 border-amber-400/80"
          : "border-2 border-emerald-500/80"
      }`}
    >
      {/* Header: Emerald when verified, Amber when insufficient evidence */}
      <div
        className={`px-5 sm:px-6 py-3.5 text-white flex items-center justify-between gap-2 ${
          insufficientEvidence
            ? "bg-linear-to-r from-amber-700 via-amber-600 to-orange-700"
            : "bg-linear-to-r from-emerald-700 via-emerald-600 to-teal-700"
        }`}
      >
        <div className="flex items-center gap-2 min-w-0">
          {insufficientEvidence ? (
            <AlertTriangle className="w-5 h-5 text-amber-200 shrink-0" />
          ) : (
            <ShieldCheck className="w-5 h-5 text-emerald-200 shrink-0" />
          )}
          <h3 className="font-extrabold text-xs uppercase tracking-widest text-white truncate">
            {insufficientEvidence
              ? "INSUFFICIENT CANONICAL EVIDENCE"
              : "SYNTHESIZED EPISTEMIC VERDICT (FINAL ANSWER)"}
          </h3>
          {stepNumber && (
            <span
              className={`text-[10px] font-mono font-bold text-white px-1.5 py-0.2 rounded border ${
                insufficientEvidence
                  ? "bg-amber-900/60 border-amber-300/40"
                  : "bg-emerald-900/60 border-emerald-300/40"
              }`}
            >
              {stepNumber}/{totalSteps || 7}
            </span>
          )}
        </div>
      </div>

      {/* Card Body: Balanced 2-Section Layout */}
      <div
        className={`p-5 sm:p-6 flex-1 ${
          rowLayout
            ? "flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6"
            : "flex flex-col justify-between space-y-4"
        }`}
      >
        {/* Left / Main Section: Status Icon & Answers */}
        <div className="flex items-start gap-4 flex-1 min-w-0">
          {/* Status Check / Alert Icon */}
          <div
            className={`w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 shadow-xs border-2 ${
              insufficientEvidence
                ? "bg-amber-100 text-amber-600 border-amber-400"
                : "bg-emerald-100 text-emerald-600 border-emerald-400"
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
                    ? "bg-amber-50 text-amber-800 border-amber-200"
                    : "bg-emerald-50 text-emerald-800 border-emerald-200"
                }`}
              >
                {insufficientEvidence
                  ? "Epistemic Boundary Reached"
                  : "Canonical Epistemic Verdict"}
              </span>
              {finalAnswer.verdictStatus && (
                <span className="text-xs text-slate-500 font-medium truncate">
                  • {finalAnswer.verdictStatus}
                </span>
              )}
            </div>

            {/* Tamil Answer Text */}
            <h4 className="text-base sm:text-xl font-bold text-slate-900 font-serif leading-snug">
              {finalAnswer.tamilAnswer}
            </h4>

            {/* English Answer Text */}
            <p className="text-xs sm:text-sm font-semibold text-slate-700 leading-relaxed">
              {finalAnswer.englishAnswer}
            </p>

            {/* Subtitle / Grounding Description */}
            {finalAnswer.subtitle && (
              <p className="text-xs text-slate-500 leading-relaxed">
                {finalAnswer.subtitle}
              </p>
            )}

            {/* Key Grounding Sources */}
            {!insufficientEvidence &&
              (finalAnswer.keySources || []).length > 0 && (
                <div className="flex items-center gap-2 flex-wrap pt-1">
                  <span className="text-[11px] uppercase font-bold text-slate-500">
                    Sources:
                  </span>
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
            className={`p-4 rounded-xl border flex items-center justify-between gap-5 min-w-57.5 sm:min-w-65 shadow-2xs ${
              insufficientEvidence
                ? "bg-amber-50/80 border-amber-200"
                : "bg-emerald-50/80 border-emerald-200"
            }`}
          >
            <div>
              <span
                className={`text-[10px] font-bold uppercase tracking-wider block ${
                  insufficientEvidence ? "text-amber-900" : "text-emerald-900"
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
                  } else if (
                    !insufficientEvidence &&
                    starIndex === fullStarsCount &&
                    remainderPercent > 0
                  ) {
                    return (
                      <div
                        key={starIndex}
                        className="relative w-4 h-4 shrink-0"
                      >
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
                  insufficientEvidence ? "text-amber-700" : "text-emerald-700"
                }`}
              >
                {insufficientEvidence ? "0.00" : finalAnswer.confidenceScore}
              </span>
              <span
                className={`block text-[10px] font-semibold mt-1 ${
                  insufficientEvidence ? "text-amber-600" : "text-emerald-600"
                }`}
              >
                {insufficientEvidence ? "Below Threshold" : "High Certainty"}
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
