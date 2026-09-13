import {
  CheckCircle2,
  BookOpen,
  Sparkles,
  AlertTriangle,
} from 'lucide-react';
import Card from '../common/Card';
import Badge from '../common/Badge';
import { useReasoner } from '../../context/ReasonerContext';

export default function RetrievedEvidenceCard() {
  const { finalAnswer, evidenceRecords, insufficientEvidence } = useReasoner();

  const isInsufficient = insufficientEvidence || finalAnswer?.status === 'insufficient_evidence';
  const hasAnswer = finalAnswer && finalAnswer.status !== 'idle';
  const scorePercent = typeof finalAnswer?.confidenceScore === 'number'
    ? (finalAnswer.confidenceScore * 100).toFixed(1)
    : '0.0';

  return (
    <div className="space-y-6">
      {/* Synthesized Epistemic Answer Card */}
      {hasAnswer ? (
        <Card
          title={isInsufficient ? "Insufficient Evidence Detected (போதிய சான்றுகள் இல்லை)" : "Synthesized Epistemic Verdict (முடிவு)"}
          subtitle={isInsufficient ? "Grounding verification requires additional canonical sources" : "Nyāya Resolution & Grounded Literary Inference"}
          icon={isInsufficient ? AlertTriangle : Sparkles}
          accent={isInsufficient ? "orange" : "purple"}
          actions={
            <div className="flex items-center gap-2">
              <Badge variant={isInsufficient ? "orange" : "green"} size="xs" dot>
                {finalAnswer.verdictStatus || (isInsufficient ? "Insufficient Evidence" : "Sound Grounding")}
              </Badge>
              <Badge variant="purple" size="xs">
                Soundness: {scorePercent}%
              </Badge>
            </div>
          }
        >
          <div className="space-y-3.5">
            {/* Tamil Epistemic Summary */}
            <div className={`p-4 rounded-xl border ${isInsufficient ? 'bg-amber-50/70 border-amber-200 text-amber-950' : 'bg-purple-50/70 border-purple-200/90 text-purple-950'}`}>
              <div className="text-[11px] font-bold uppercase tracking-wider mb-1 flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full ${isInsufficient ? 'bg-amber-600' : 'bg-purple-600'}`} />
                {isInsufficient ? "ஆய்வு நிலை (Inquiry Status)" : "தீர்ப்பின் ஆய்வுத் தொகுப்பு (Philosophical Summary)"}
              </div>
              <p className="tamil-font text-base sm:text-lg font-semibold leading-relaxed">
                "{finalAnswer.tamilAnswer}"
              </p>
            </div>

            {/* English Scholarly Rationale */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs sm:text-sm text-slate-700 leading-relaxed">
              <span className="font-semibold text-slate-900 block mb-1">
                Scholarly Rationale:
              </span>
              <p>{finalAnswer.justificationEnglish || finalAnswer.englishAnswer}</p>
            </div>

            {/* Key Grounding */}
            {finalAnswer.justificationTamil && (
              <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-900 flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold">Textual Grounding:</span>{' '}
                  {finalAnswer.justificationTamil}
                </div>
              </div>
            )}
          </div>
        </Card>
      ) : (
        <Card
          title="Synthesized Epistemic Verdict (முடிவு)"
          subtitle="Awaiting search execution from Query Center"
          icon={Sparkles}
          accent="purple"
        >
          <div className="py-8 px-4 text-center space-y-2 bg-slate-50/60 rounded-xl border border-dashed border-slate-200">
            <p className="text-xs font-bold text-slate-700">Ready for Inquiry</p>
            <p className="text-[11px] text-slate-500 max-w-sm mx-auto">
              Execute a research inquiry in the Query Center to synthesize an evidence-grounded epistemic verdict.
            </p>
          </div>
        </Card>
      )}

      {/* Retrieved Textual Evidence Card */}
      <Card
        title="Retrieved Canonical Evidence & Passages"
        subtitle="Ranked textual passages extracted via Hybrid RAG"
        icon={BookOpen}
        accent="blue"
        actions={
          <Badge variant="blue" size="xs">
            {evidenceRecords.length} Passages Retrieved
          </Badge>
        }
      >
        {evidenceRecords.length === 0 ? (
          <div className="py-8 px-4 text-center space-y-2 bg-slate-50/60 rounded-xl border border-dashed border-slate-200">
            <p className="text-xs font-bold text-slate-700">No Evidence Records Retrieved</p>
            <p className="text-[11px] text-slate-500 max-w-sm mx-auto">
              Submit a query in the Query Center above to fetch live passages from the Tolkāppiyam corpus.
            </p>
          </div>
        ) : (
          <div className="space-y-3.5">
            {evidenceRecords.map((item) => (
              <div
                key={item.id}
                className="p-4 rounded-xl bg-slate-50/70 hover:bg-slate-50 border border-slate-200 hover:border-blue-300 transition-all space-y-2.5"
              >
                {/* Header */}
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-blue-900 bg-blue-100 px-2 py-0.5 rounded">
                      {item.code || item.passageId}
                    </span>
                    <span className="text-xs font-semibold text-slate-700">
                      {item.source} • {item.section}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-mono text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 font-medium">
                      Score: {item.confidenceFormatted || Number(item.confidence || 0).toFixed(2)}
                    </span>
                    <Badge variant="purple" size="xs">
                      {item.badges?.[0]?.label || 'Hybrid RAG'}
                    </Badge>
                  </div>
                </div>

                {/* Tamil Quote */}
                <div className="bg-white p-3 rounded-lg border border-slate-200 font-serif text-slate-900 text-sm font-semibold whitespace-pre-line leading-relaxed shadow-2xs">
                  {item.tamilText}
                </div>

                {/* English Translation */}
                <p className="text-xs text-slate-600 leading-relaxed italic">
                  {item.translation}
                </p>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
