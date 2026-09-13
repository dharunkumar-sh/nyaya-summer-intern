import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Library, BookOpen } from "lucide-react";
import Card from "../../common/Card";
import Badge from "../../common/Badge";
import { useReasoner } from "../../../context/ReasonerContext";

export default function OverviewCorpusAtikaramCard() {
  const navigate = useNavigate();
  const { corpus, dashboardSummary } = useReasoner();

  const handleOpenSutraExplorer = (sectionId = null) => {
    navigate("/sutras", { state: sectionId ? { sectionId } : undefined });
  };

  const corpusData = dashboardSummary?.corpus || corpus;
  const books = corpusData?.books || corpusData?.sections || [];
  const eluttuBook = books.find(
    (b) =>
      b.id === "eluttu" || (b.name && b.name.toLowerCase().includes("eluttu")),
  );
  const colBook = books.find(
    (b) => b.id === "col" || (b.name && b.name.toLowerCase().includes("col")),
  );
  const porulBook = books.find(
    (b) =>
      b.id === "porul" || (b.name && b.name.toLowerCase().includes("porul")),
  );

  const eluttuCount =
    eluttuBook?.canonical_sutras_count ?? eluttuBook?.sutra_count ?? 483;
  const colCount =
    colBook?.canonical_sutras_count ?? colBook?.sutra_count ?? 463;
  const porulCount =
    porulBook?.canonical_sutras_count ?? porulBook?.sutra_count ?? 664;
  const totalSutras =
    corpusData?.total_sutras_canonical ||
    corpusData?.totalSutras ||
    eluttuCount + colCount + porulCount ||
    1610;

  const eluttuPct =
    totalSutras > 0 ? ((eluttuCount / totalSutras) * 100).toFixed(1) : "30.0";
  const colPct =
    totalSutras > 0 ? ((colCount / totalSutras) * 100).toFixed(1) : "28.8";
  const porulPct =
    totalSutras > 0
      ? (100 - parseFloat(eluttuPct) - parseFloat(colPct)).toFixed(1)
      : "41.2";

  const atikarams = useMemo(
    () => [
      {
        id: "eluttu",
        name: "Eḻuttatikāram",
        tamilName: "எழுத்ததிகாரம்",
        englishTitle: "Book of Orthography & Phonology",
        count: eluttuCount,
        percent: `${eluttuPct}%`,
        activeCount: 0,
        color: "blue",
        barBg: "bg-blue-600",
        badgeVariant: "blue",
        btnStyle:
          "bg-blue-50 text-blue-700 hover:bg-blue-600 hover:text-white border-blue-200 hover:border-blue-600",
        iconColor: "text-blue-600 group-hover:text-white",
        focus: "Phonology, Orthography, Morphophonemics, Metrical Acoustics",
        chapters: [
          { en: "Nūṉmarapu", ta: "நூன்மரபு" },
          { en: "Moḻimarapu", ta: "மொழிமரபு" },
          { en: "Piṟappiyal", ta: "பிறப்பியல்" },
          { en: "Puṇariyal", ta: "புணரியல்" },
          { en: "Tokaimarapu", ta: "தொகைமரபு" },
          { en: "Urupiyal", ta: "உருபியல்" },
          { en: "Uyiṟmayaṅkiyal", ta: "உயிர்மயங்கியல்" },
          { en: "Puḷḷimayaṅkiyal", ta: "புள்ளிமயங்கியல்" },
          { en: "Kuṟṟiyalukarappuṇariyal", ta: "குற்றியலுகரப் புணரியல்" },
        ],
      },
      {
        id: "col",
        name: "Collatikāram",
        tamilName: "சொல்லதிகாரம்",
        englishTitle: "Book of Morphology & Syntax",
        count: colCount,
        percent: `${colPct}%`,
        activeCount: 0,
        color: "indigo",
        barBg: "bg-indigo-600",
        badgeVariant: "purple",
        btnStyle:
          "bg-indigo-50 text-indigo-700 hover:bg-indigo-600 hover:text-white border-indigo-200 hover:border-indigo-600",
        iconColor: "text-indigo-600 group-hover:text-white",
        focus:
          "Morphology, Syntax, Semantics, Nominal/Verbal Classes, Semantic Cases",
        chapters: [
          { en: "Kiḷaviyākkam", ta: "கிளவியாக்கம்" },
          { en: "Vēṟṟumaiyiyal", ta: "வேற்றுமையியல்" },
          { en: "Vēṟṟumaimayaṅkiyal", ta: "வேற்றுமை மயங்கியல்" },
          { en: "Viḷimarapu", ta: "விளிமரபு" },
          { en: "Peyariyal", ta: "பெயரியல்" },
          { en: "Viṉaiyiyal", ta: "வினையியல்" },
          { en: "Iṭaiyiyal", ta: "இடையியல்" },
          { en: "Uriyiyal", ta: "உரியியல்" },
          { en: "Eccaviyal", ta: "எச்சவியல்" },
        ],
      },
      {
        id: "porul",
        name: "Poruḷatikāram",
        tamilName: "பொருளதிகாரம்",
        englishTitle: "Book of Poetics & Eco-Semiotics",
        count: porulCount,
        percent: `${porulPct}%`,
        activeCount: 6,
        color: "purple",
        barBg: "bg-purple-600",
        badgeVariant: "purple",
        btnStyle:
          "bg-purple-50 text-purple-700 hover:bg-purple-600 hover:text-white border-purple-200 hover:border-purple-600",
        iconColor: "text-purple-600 group-hover:text-white",
        focus:
          "Poetics, Semiotics, Tiṇai Ecology, Psychology, Aesthetics & Moral Sociology",
        chapters: [
          { en: "Akattiṇaiyiyal", ta: "அகத்திணையியல்" },
          { en: "Puṟattiṇaiyiyal", ta: "புறத்திணையியல்" },
          { en: "Kaḷaviyal", ta: "களவியல்" },
          { en: "Kaṟpiyal", ta: "கற்பியல்" },
          { en: "Poruḷiyal", ta: "பொருளியல்" },
          { en: "Meyppāṭṭiyal", ta: "மெய்ப்பாட்டியல்" },
          { en: "Uvamaviyal", ta: "உவமவியல்" },
          { en: "Ceyyuḷiyal", ta: "செய்யுளியல்" },
          { en: "Marapiyal", ta: "மரபியல்" },
        ],
      },
    ],
    [eluttuCount, colCount, porulCount, eluttuPct, colPct, porulPct],
  );

  return (
    <Card
      title="Tolkāppiyam Canonical Corpus Architecture (நூற்பா கட்டமைப்பு)"
      subtitle={`${totalSutras.toLocaleString()} Sūtras across the 3 Foundational Books (Atikāram) & 27 Chapters (Iyal)`}
      icon={Library}
      accent="purple"
    >
      <div className="space-y-4">
        {/* 3 Atikāram Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {atikarams.map((sec) => (
            <div
              key={sec.id}
              className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs hover:shadow-xs transition-all flex flex-col justify-between"
            >
              <div>
                {/* Card Header row */}
                <div className="flex items-center justify-between gap-1 mb-2">
                  <Badge variant={sec.badgeVariant} size="xs">
                    {sec.percent} of Corpus
                  </Badge>
                  <div className="flex items-center gap-1.5 font-mono text-xs">
                    <span className="font-bold text-slate-900">
                      {sec.count.toLocaleString()} Sūtras
                    </span>
                  </div>
                </div>

                <div className="mb-1">
                  <h4 className="font-bold text-sm text-slate-900 font-serif leading-tight">
                    {sec.name}
                  </h4>
                  <div className="text-[11px] text-purple-700 font-serif mt-0.5">
                    {sec.tamilName} •{" "}
                    <span className="text-slate-500 font-sans">
                      {sec.englishTitle}
                    </span>
                  </div>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed mb-3">
                  {sec.focus}
                </p>

                {/* Subdivisions / Iyal Chips */}
                <div className="space-y-1.5">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                    9 Chapters (இயல்கள்):
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {sec.chapters.map((chap, i) => (
                      <span
                        key={i}
                        title={`${chap.en} (${chap.ta})`}
                        className="text-[10px] px-2 py-0.5 rounded flex items-center gap-1 font-serif select-none bg-slate-100 text-slate-700 border border-slate-200/60"
                      >
                        <span>{chap.en}</span>
                        <span className="text-[9px] text-slate-400 font-sans">
                          ({chap.ta})
                        </span>
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Action Button */}
              <div className="pt-3 mt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => handleOpenSutraExplorer(sec.id)}
                  className={`w-full flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold border transition-all cursor-pointer group shadow-2xs ${sec.btnStyle}`}
                >
                  <BookOpen
                    className={`w-3.5 h-3.5 transition-colors ${sec.iconColor}`}
                  />
                  <span>
                    Browse {sec.name} ({sec.tamilName})
                  </span>
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}
