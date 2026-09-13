import { useState, useMemo } from "react";
import {
  Scale,
  Eye,
  Cpu,
  GitCompare,
  BookMarked,
  CheckCircle2,
  BookOpen,
  Sparkles,
} from "lucide-react";
import Card from "../../common/Card";
import Badge from "../../common/Badge";
import { useReasoner } from "../../../context/ReasonerContext";

const PRAMANA_SYSTEM = [
  {
    id: "anumana",
    name: "Anumāna",
    tamilName: "கருதல்",
    sanskritRole: "Inferential Syllogism",
    tamilDescription: "ஐந்துறுப்புப் பஞ்சாவயவ நியாய அனுமானம்",
    weight: 45,
    color: "amber",
    icon: Cpu,
    status: "Primary Active Engine",
    badgeVariant: "orange",
    barColor: "bg-amber-500",
    iconBg: "bg-amber-100 text-amber-800 border-amber-200",
    selectedRing: "ring-amber-500/40 border-amber-500 bg-amber-50/40",
    description:
      "Deductive formal syllogism moving from the observed ecological marker (Lingam) to the unobserved psychological state (Sādhya) via invariant concomitance (Vyāpti).",
    canonicalGround: "Nyāya Sūtra 1.1.5 + Tolkāppiyam Poruḷatikāram Semiotics",
    operationalRole:
      "Synthesizes the 5-step Pañcāvayava deduction & formal theorem proving.",
  },
  {
    id: "pratyaksa",
    name: "Pratyakṣa",
    tamilName: "காட்சி",
    sanskritRole: "Direct Perception",
    tamilDescription: "நேரடி மூலநூற்பா வாசக ஆய்வு",
    weight: 25,
    color: "emerald",
    icon: Eye,
    status: "Direct Grounding",
    badgeVariant: "green",
    barColor: "bg-emerald-500",
    iconBg: "bg-emerald-100 text-emerald-800 border-emerald-200",
    selectedRing: "ring-emerald-500/40 border-emerald-500 bg-emerald-50/40",
    description:
      "Direct textual perception of canonical sūtra tokens, orthography, and morphosyntactic structures in the original classical Tamil text.",
    canonicalGround: "Tolkāppiyam (1,610 Sūtras across 3 Books)",
    operationalRole:
      "Cross-attention semantic retrieval and citation ground verification via Tamil-BERT.",
  },
  {
    id: "sabda",
    name: "Śabda",
    tamilName: "ஆகமம் / உரை",
    sanskritRole: "Verbal Testimony & Authority",
    tamilDescription: "தொல்காப்பியர் மரபும் உரையாசிரியர் நெறியும்",
    weight: 18,
    color: "purple",
    icon: BookMarked,
    status: "Axiomatic Ground",
    badgeVariant: "purple",
    barColor: "bg-purple-600",
    iconBg: "bg-purple-100 text-purple-800 border-purple-200",
    selectedRing: "ring-purple-500/40 border-purple-500 bg-purple-50/40",
    description:
      "Incontestable authority of master grammarian Tolkāppiyar and scholastic traditions of ancient commentators (Iḷampūraṇar, Naccinarkkiniyar, Pērāciriyar).",
    canonicalGround: "Marapiyal, Poruḷiyal & Classical Commentaries",
    operationalRole:
      "Establishes inviolable grammar rules, literary conventions (Valakku & Ceyyuḷ).",
  },
  {
    id: "upamana",
    name: "Upamāna",
    tamilName: "உவமம்",
    sanskritRole: "Analogical Cognition",
    tamilDescription: "திணை உவமவியல் மற்றும் உள்ளுறை இறைச்சி",
    weight: 12,
    color: "blue",
    icon: GitCompare,
    status: "Analogical Mapping",
    badgeVariant: "blue",
    barColor: "bg-blue-500",
    iconBg: "bg-blue-100 text-blue-800 border-blue-200",
    selectedRing: "ring-blue-500/40 border-blue-500 bg-blue-50/40",
    description:
      "Recognition of structural similarity between the natural environment and interior human experience through explicit similes (Uvamam) and implicit eco-metaphors (Uḷḷuṟai / Iraicci).",
    canonicalGround: "Tolkāppiyam Poruḷatikāram (Uvamaviyal 272–310)",
    operationalRole:
      "Enables cross-domain semantic transfer between ecological tokens and affective moods.",
  },
];

export default function OverviewPramanaMatrix() {
  const [selectedPramanaId, setSelectedPramanaId] = useState("anumana");
  const { dashboardSummary } = useReasoner();

  const backendWeights = dashboardSummary?.reasoning_and_soundness?.epistemic_pramana_weights;
  const anumanaWeight = backendWeights?.anumana ?? 45;
  const pratyaksaWeight = backendWeights?.pratyaksa ?? 25;
  const sabdaWeight = backendWeights?.sabda ?? 18;
  const upamanaWeight = backendWeights?.upamana ?? 12;

  const pramanas = useMemo(() => {
    return PRAMANA_SYSTEM.map((p) => {
      let w = p.weight;
      if (p.id === 'anumana') w = anumanaWeight;
      else if (p.id === 'pratyaksa') w = pratyaksaWeight;
      else if (p.id === 'sabda') w = sabdaWeight;
      else if (p.id === 'upamana') w = upamanaWeight;
      return { ...p, weight: w };
    });
  }, [anumanaWeight, pratyaksaWeight, sabdaWeight, upamanaWeight]);

  const activePramana =
    pramanas.find((p) => p.id === selectedPramanaId) || pramanas[0];

  return (
    <Card
      title="Nyāya Pramāṇa Epistemic Instruments (அளவையியல் முறைமை)"
      subtitle="The 4 Valid Means of Knowledge Cognition in Neuro-Symbolic Tolkāppiyam Reasoning"
      icon={Scale}
      accent="orange"
    >
      <div className="space-y-6">
        {/* Cumulative Pramāṇa Weight Distribution Bar */}
        <div className="p-4 sm:p-5 bg-linear-to-r from-slate-50 via-white to-slate-50 rounded-2xl border border-slate-200 shadow-2xs space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs sm:text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-500" />
              Epistemic Weight Distribution Across Cognitive Channels
            </span>
            <span className="font-mono text-xs text-emerald-700 font-semibold bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              100% Validated Epistemic Grounding
            </span>
          </div>

          {/* Stacked Progress Bar with Clear Proportions */}
          <div className="w-full h-3.5 rounded-full overflow-hidden flex bg-slate-200 shadow-inner p-0.5">
            <div
              className="bg-amber-500 h-full rounded-l-full transition-all duration-300"
              style={{ width: `${anumanaWeight}%` }}
              title={`Anumāna (Inferential): ${anumanaWeight}%`}
            />
            <div
              className="bg-emerald-500 h-full transition-all duration-300"
              style={{ width: `${pratyaksaWeight}%` }}
              title={`Pratyakṣa (Direct Perception): ${pratyaksaWeight}%`}
            />
            <div
              className="bg-purple-600 h-full transition-all duration-300"
              style={{ width: `${sabdaWeight}%` }}
              title={`Śabda (Canonical Authority): ${sabdaWeight}%`}
            />
            <div
              className="bg-blue-500 h-full rounded-r-full transition-all duration-300"
              style={{ width: `${upamanaWeight}%` }}
              title={`Upamāna (Analogical): ${upamanaWeight}%`}
            />
          </div>

          {/* Legend Chips with High Contrast & Readability */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-xs">
            {pramanas.map((p) => {
              const isSelected = selectedPramanaId === p.id;
              return (
                <div
                  key={p.id}
                  className={`flex items-center justify-between p-2 rounded-xl border transition-all ${
                    isSelected
                      ? "bg-slate-100 border-slate-400 font-semibold shadow-2xs"
                      : "bg-white border-slate-200 hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={`w-3 h-3 rounded-full shrink-0 ${p.barColor}`}
                    />
                    <span className="text-slate-800 text-xs">
                      {p.name} ({p.tamilName})
                    </span>
                  </div>
                  <span className="font-mono font-bold text-slate-900 text-xs">
                    {p.weight}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* 4 Pramāṇa Interactive Cards with Generous Spacing */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {pramanas.map((pramana) => {
            const IconComp = pramana.icon;
            const isSelected = selectedPramanaId === pramana.id;

            return (
              <button
                key={pramana.id}
                type="button"
                onClick={() => setSelectedPramanaId(pramana.id)}
                className={`p-4 sm:p-5 rounded-2xl border text-left transition-all duration-200 cursor-pointer flex flex-col justify-between group shadow-2xs hover:shadow-md ${
                  isSelected
                    ? `${pramana.selectedRing} ring-2 shadow-sm`
                    : "bg-white border-slate-200/90 hover:bg-slate-50 hover:border-slate-300"
                }`}
              >
                <div>
                  {/* Top row: Icon + Weight Badge */}
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <div
                      className={`p-2.5 rounded-xl border ${pramana.iconBg}`}
                    >
                      <IconComp className="w-5 h-5" />
                    </div>
                    <Badge variant={pramana.badgeVariant} size="sm">
                      {pramana.weight}% Weight
                    </Badge>
                  </div>

                  {/* Title & Tamil Name */}
                  <div className="space-y-0.5">
                    <div className="text-base font-extrabold text-slate-900 tracking-tight">
                      {pramana.name}{" "}
                      <span className="text-slate-600 font-serif font-normal">
                        ({pramana.tamilName})
                      </span>
                    </div>
                    <div className="text-xs font-semibold text-purple-700">
                      {pramana.sanskritRole}
                    </div>
                  </div>

                  {/* Tamil Description */}
                  <p className="text-xs text-slate-500 font-serif mt-2 leading-relaxed">
                    {pramana.tamilDescription}
                  </p>
                </div>

                {/* Footer status row */}
                <div className="mt-4 pt-3 border-t border-slate-200/80 flex items-center justify-between text-xs">
                  <span className="text-slate-500 font-medium">Status</span>
                  <span className="inline-flex items-center gap-1.5 font-semibold text-emerald-700">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    {pramana.status}
                  </span>
                </div>
              </button>
            );
          })}
        </div>

        {/* Selected Pramāṇa Detailed Inspection Card */}
        {activePramana && (
          <div className="p-5 sm:p-6 rounded-2xl bg-slate-50 border border-slate-200 shadow-xs space-y-4 animate-in fade-in duration-150">
            <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-200">
              <div className="flex items-center gap-3">
                <span className="w-9 h-9 rounded-xl bg-amber-100 border border-amber-200 text-amber-800 font-extrabold flex items-center justify-center font-mono text-sm">
                  {activePramana.weight}%
                </span>
                <div>
                  <h4 className="text-base sm:text-lg font-bold text-slate-900 font-serif">
                    {activePramana.name} ({activePramana.tamilName}) —{" "}
                    {activePramana.sanskritRole}
                  </h4>
                  <p className="text-xs text-slate-500">
                    Epistemic Instrument in Classical Tamil Nyāya Reasoning
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Badge variant={activePramana.badgeVariant} size="md">
                  {activePramana.status}
                </Badge>
              </div>
            </div>

            {/* In-depth definition */}
            <p className="text-xs sm:text-sm text-slate-700 leading-relaxed bg-white p-3.5 rounded-xl border border-slate-200/80">
              {activePramana.description}
            </p>

            {/* 2 Detailed Breakdown Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 text-xs">
              <div className="p-4 rounded-xl bg-white border border-slate-200 space-y-1 shadow-2xs">
                <div className="flex items-center gap-2 text-slate-900 font-bold mb-1">
                  <BookOpen className="w-4 h-4 text-purple-600" />
                  <span>Classical Textual Ground (சான்று முறைமை)</span>
                </div>
                <p className="text-slate-600 leading-relaxed">
                  {activePramana.canonicalGround}
                </p>
              </div>

              <div className="p-4 rounded-xl bg-white border border-slate-200 space-y-1 shadow-2xs">
                <div className="flex items-center gap-2 text-slate-900 font-bold mb-1">
                  <Cpu className="w-4 h-4 text-amber-600" />
                  <span>Operational Reasoner Function (இயக்க நெறிமுறை)</span>
                </div>
                <p className="text-slate-600 leading-relaxed">
                  {activePramana.operationalRole}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
