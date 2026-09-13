import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Trees,
  Mountain,
  Waves,
  SunMedium,
  Compass,
  ArrowRight,
  Heart,
  Calendar,
  Sparkles,
  Church,
} from "lucide-react";
import Card from "../../common/Card";
import Badge from "../../common/Badge";
import { useReasoner } from "../../../context/ReasonerContext";

const TINAIS = [
  {
    id: "kurinji",
    name: "Kurinji",
    tamilName: "குறிஞ்சி",
    landscape: "Mountainous and Hilly Land",
    tamilLandscape: "மலை மற்றும் மலை சார்ந்த நிலம்",
    image: "/lands/mountain.png",
    icon: Mountain,
    color: "purple",
    badgeColor: "purple",
    cardBorder: "border-purple-300",
    selectedBg: "bg-purple-50 text-purple-900 border-purple-500",
    deity: "Cēyōṉ (சேயோன் / Murugaṉ)",
    timeAndSeason:
      "Midnight (யாமம்) • Cool Season & Early-Dew Season (கூதிர் & முன்பனி)",
    mutalporul:
      "Spacious steep mountains, cascading torrents, deep bamboo ravines, misty cold night",
    karupporul:
      "Vēṅkai blossoms, Peacocks, Elephants, Wild Honeycombs, Mountain Tribes (Kāṉavar)",
    uripporul:
      "Puṇartal (புணர்தல்) — Clandestine union and ecstatic reunion of lovers",
    sutraCitation: "Akattiṇaiyiyal Sūtra 5 (சேயோன் மேய மைவரை உலகமும்...)",
    sampleQueryText:
      "குறிஞ்சி நிலத்தின் முதற்பொருள், கருப்பொருள், உரிப்பொருள் தொடர்பு எவ்வாறு அக ஒழுக்கத்தை உணர்த்துகிறது?",
  },
  {
    id: "mullai",
    name: "Mullai",
    tamilName: "முல்லை",
    landscape: "Pastoral Forest and Woodland",
    tamilLandscape: "காடு மற்றும் காடு சார்ந்த நிலம்",
    image: "/lands/forest.png",
    icon: Trees,
    color: "emerald",
    badgeColor: "green",
    cardBorder: "border-emerald-300",
    selectedBg: "bg-emerald-50 text-emerald-900 border-emerald-500",
    deity: "Māyōṉ (மாயோன் / Vishnu / Krishna)",
    timeAndSeason: "Twilight / Evening (மாலை) • Rainy Monsoon (கார்காலம்)",
    mutalporul:
      "Steep mountains, waterfalls, bamboo-filled ravines, mist, and the cool night",
    karupporul:
      "Vēṅkai flowers, Peacocks, Elephants, Wild Honey, Mountain People (Kāṉavar)",
    uripporul: "Puṇartal (புணர்தல்) — Union and intimate meeting of the lovers",
    sutraCitation: "Akattiṇaiyiyal 5 (சேயோன் மேய மைவரை உலகமும்...)",
    sampleQueryText:
      "மாயோன் மேய காடுறை உலகமும் முல்லைத் திணையின் ஆற்றுதல் ஒழுக்கமும் எவ்வாறு அமைகிறது?",
  },
  {
    id: "marutham",
    name: "Marutham",
    tamilName: "மருதம்",
    landscape: "Fertile Agricultural River Plains",
    tamilLandscape: "வயலும் வயல் சார்ந்த செழிப்பான நிலம்",
    image: "/lands/farm.png",
    icon: Waves,
    color: "blue",
    badgeColor: "blue",
    cardBorder: "border-blue-300",
    selectedBg: "bg-blue-50 text-blue-900 border-blue-500",
    deity: "Vēntaṉ (வேந்தன் / Sovereign of Heavens)",
    timeAndSeason:
      "Dawn / Pre-sunrise (விடியல்) • All six seasons (இருதுக்கள்)",
    mutalporul:
      "Rain-fed forests, woodland clearings, streams, and the calm evening",
    karupporul: "Mullai flowers, Deer, Cattle, Flute (Kuḻal), Cowherds (Āyar)",
    uripporul:
      "Iruttal (இருத்தல்) — Patient waiting for the absent lover's return",
    sutraCitation: "Akattiṇaiyiyal 5 (மாயோன் மேய காடுறை உலகமும்...)",
    sampleQueryText:
      "வேந்தன் மேய தீம்புனல் உலகமும் மருதத் திணையின் ஊடல் ஒழுக்கமும் எவ்வாறு தொல்காப்பியத்தில் விளக்கப்படுகிறது?",
  },
  {
    id: "neythal",
    name: "Neythal",
    tamilName: "நெய்தல்",
    landscape: "Coastal And Seashore Land",
    tamilLandscape: "கடலும் கடல் சார்ந்த நிலமும்",
    image: "/lands/island.png",
    icon: Waves,
    color: "cyan",
    badgeColor: "blue",
    cardBorder: "border-cyan-300",
    selectedBg: "bg-cyan-50 text-cyan-900 border-cyan-500",
    deity: "Varuṇaṉ (வருணன் / Ocean Deity)",
    timeAndSeason: "Sunset (எற்பாடு) • All seasons (எல்லாக் காலமும்)",
    mutalporul:
      "Vast sea, breaking surf, sandy shores, sea breeze, and the setting sun",
    karupporul:
      "Neytal Water Lily, Seabirds, Fish, Pearl Oysters, Fisherfolk (Paratavar), Salt-making",
    uripporul:
      "Iraṅkal (இரங்கல்) — Lamentation, anxiety, and pining during separation",
    sutraCitation: "Akattiṇaiyiyal 5 (வருணன் மேய பெருமணல் உலகமும்...)",
    sampleQueryText:
      "வருணன் மேய பெருமணல் உலகமும் நெய்தல் திணையின் இரங்கல் ஒழுக்கமும் உணர்த்தும் விழுப்பொருள் யாது?",
  },
  {
    id: "paalai",
    name: "Pāalai",
    tamilName: "பாலை",
    landscape: "Arid And Parched Land",
    tamilLandscape: "வறண்ட மற்றும் வெப்பமான நிலம்",
    image: "/lands/desert.png",
    icon: SunMedium,
    color: "amber",
    badgeColor: "orange",
    cardBorder: "border-amber-300",
    selectedBg: "bg-amber-50 text-amber-900 border-amber-500",
    deity: "Koṟtṟavai (கொற்றவை / Goddess of Victory)",
    timeAndSeason:
      "High Noon (நண்பகல்) • Scorching Summer & Early Dew (வேனில் & பின்பனி)",
    mutalporul:
      "Heat-scorched, water-scarce terrain formed when hill or forest country becomes parched",
    karupporul:
      "Kalli and hardy plants, Vultures, Tigers and Wolves, Wayfarers, Hunters and Warriors (Eyinar / Maravar)",
    uripporul:
      "Pirital (பிரிதல்) — Separation and the hardships of a dangerous journey",
    sutraCitation: "Akattiṇaiyiyal 2 (நடுவண் ஐந்திணை நடுவண தொழியப்...)",
    sampleQueryText:
      "பாலைத் திணையில் காதலின் பிரிவும் கொற்றவை வழிபாடும் எவ்வாறு நெறிப்படுத்தப்பட்டுள்ளது?",
  },
];

export default function OverviewTinaiLandscapeExplorer() {
  const navigate = useNavigate();
  const { setQueryText } = useReasoner();
  const [selectedTinaiId, setSelectedTinaiId] = useState("kurinchi");

  const activeTinai = TINAIS.find((t) => t.id === selectedTinaiId) || TINAIS[0];

  const handleTestTinaiInReasoner = (tinai) => {
    setQueryText(tinai.sampleQueryText);
    navigate("/query-center");
  };

  return (
    <Card
      title="Classical Tamil Tiṇai Eco-Poetic System (ஐந்திணை நிலவியல்)"
      subtitle="The Tripartite Semiotic Triangulation: Mutalporuḷ (Space-Time) → Karupporuḷ (Biota) → Uripporuḷ (Affect)"
      icon={Compass}
      accent="purple"
    >
      <div className="space-y-4">
        {/* 5 Tiṇai Selector Tabs with Land Images */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
          {TINAIS.map((tinai) => {
            const IconComp = tinai.icon;
            const isSelected = selectedTinaiId === tinai.id;

            return (
              <button
                key={tinai.id}
                type="button"
                onClick={() => setSelectedTinaiId(tinai.id)}
                className={`group relative flex flex-col p-2.5 rounded-2xl border text-left transition-all cursor-pointer overflow-hidden ${
                  isSelected
                    ? `${tinai.selectedBg} ring-2 ring-purple-500/40 shadow-sm font-semibold`
                    : "bg-white border-slate-200/90 text-slate-700 hover:bg-slate-50 hover:border-slate-300 shadow-2xs"
                }`}
              >
                {/* Land Image Preview */}
                <div className="relative w-full h-26 sm:h-30 rounded-xl mb-2 bg-linear-to-b from-white to-slate-100/90 border border-slate-200/80 flex items-center justify-center p-3 shadow-sm group-hover:border-purple-300 transition-colors">
                  <img
                    src={tinai.image}
                    alt={`${tinai.name} landscape`}
                    className="w-19.5 h-19.5 object-cover transition-transform duration-300 drop-shadow-xs"
                    loading="lazy"
                  />

                  {/* Active Indicator Badge */}
                  {isSelected && (
                    <span className="absolute top-1.5 right-1.5 flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-purple-600 text-[10px] font-bold text-white shadow-xs">
                      <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                      Active
                    </span>
                  )}

                  {/* Icon & Tamil Pill on Bottom of Image */}
                  <div className="absolute bottom-1.5 left-2 right-2 flex items-center justify-between text-slate-700 text-[10px] font-semibold">
                    <span className="truncate">{tinai.tamilName}</span>
                    <IconComp className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                  </div>
                </div>

                {/* Typography Metadata */}
                <div className="px-0.5">
                  <div className="text-xs sm:text-sm font-bold text-slate-900 group-hover:text-purple-700 transition-colors truncate">
                    {tinai.name}
                  </div>
                  <div className="text-[11px] font-serif text-slate-600 truncate">
                    {tinai.tamilName}
                  </div>
                  <div className="text-[10px] text-slate-400 truncate mt-0.5">
                    {tinai.landscape ? tinai.landscape.split("&")[0] : ""}
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {/* Detailed Tripartite Semiotic Breakdown for Selected Tiṇai */}
        <div className="p-4 sm:p-5 rounded-2xl bg-slate-50/80 border border-slate-200 space-y-4">
          {/* Header row with Featured Land Image, Title, Deity, and Action Button */}
          <div className="flex flex-col md:flex-row items-stretch gap-4 pb-4 border-b border-slate-200/80">
            {/* Featured Active Land Hero Visual */}
            <div className="relative w-full md:w-52 h-40 md:h-auto rounded-2xl border border-slate-200/90 bg-linear-to-br from-white via-slate-50 to-slate-100 shadow-xs flex flex-col items-center justify-center p-4 shrink-0">
              <img
                src={activeTinai.image}
                alt={`${activeTinai.name} terrain`}
                className="w-20 h-20 sm:w-24 sm:h-24 object-contain drop-shadow-sm transition-transform duration-300 hover:scale-105"
              />
              <div className="mt-2.5 text-center">
                <span className="inline-block text-[10px] font-bold tracking-wider uppercase px-2.5 py-0.5 rounded-full bg-slate-900 text-white shadow-2xs">
                  {activeTinai.tamilLandscape}
                </span>
              </div>
            </div>

            {/* Title, Deity, Season & Query Action Button */}
            <div className="flex-1 flex flex-col justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="text-base sm:text-lg font-bold text-slate-900 font-serif">
                    {activeTinai.name} ({activeTinai.tamilName}) —{" "}
                    {activeTinai.landscape}
                  </h3>
                  <Badge variant={activeTinai.badgeColor} size="xs">
                    {activeTinai.tamilLandscape}
                  </Badge>
                </div>
                <div className="flex flex-wrap items-center gap-3 mt-1.5 text-xs text-slate-600">
                  <span className="flex items-center gap-1">
                    <Church className="h-4 w-4 text-yellow-600" />
                    <strong className="text-slate-700">
                      Tutelary Deity:
                    </strong>{" "}
                    {activeTinai.deity}
                  </span>

                  <span className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5 text-purple-600" />
                    <span>
                      <strong className="text-slate-700">Time & Season:</strong>{" "}
                      {activeTinai.timeAndSeason}
                    </span>
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-1 line-clamp-2 leading-relaxed">
                  Classical landscape poetics in Tolkāppiyam Akattiṇaiyiyal:
                  physical terrain and climate deterministically ground human
                  emotional interiority.
                </p>
              </div>

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <button
                  type="button"
                  onClick={() => handleTestTinaiInReasoner(activeTinai)}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-purple-700 hover:bg-purple-600 text-white text-xs font-semibold shadow-xs transition-colors shrink-0 cursor-pointer self-start sm:self-auto"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Load in Query Center</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            </div>
          </div>

          {/* The Tripartite Core Grid: Mutal, Karu, Uri */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5 text-xs">
            {/* 1. Mutalporuḷ */}
            <div className="p-3.5 rounded-xl bg-white border border-slate-200 space-y-1.5 shadow-2xs">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-900 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-blue-600" />
                  1. Mutalporuḷ (முதற்பொருள்)
                </span>
                <Badge variant="blue" size="xs">
                  Space & Time
                </Badge>
              </div>
              <p className="text-slate-600 leading-relaxed">
                {activeTinai.mutalporul}
              </p>
            </div>

            {/* 2. Karupporuḷ */}
            <div className="p-3.5 rounded-xl bg-white border border-slate-200 space-y-1.5 shadow-2xs">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-900 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-600" />
                  2. Karupporuḷ (கருப்பொருள்)
                </span>
                <Badge variant="green" size="xs">
                  Biota & Deities
                </Badge>
              </div>
              <p className="text-slate-600 leading-relaxed">
                {activeTinai.karupporul}
              </p>
            </div>

            {/* 3. Uripporuḷ */}
            <div className="p-3.5 rounded-xl bg-white border border-slate-200 space-y-1.5 shadow-2xs">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-900 flex items-center gap-1.5">
                  <Heart className="w-3.5 h-3.5 text-rose-500" />
                  3. Uripporuḷ (உரிப்பொருள்)
                </span>
                <Badge variant="orange" size="xs">
                  Affective Mood
                </Badge>
              </div>
              <p className="leading-relaxed font-medium text-purple-950">
                {activeTinai.uripporul}
              </p>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}
