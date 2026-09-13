import { useMemo } from "react";
import {
  LayoutGrid,
  Sparkles,
  Network,
  Cpu,
  BookOpen,
  ShieldCheck,
  Library,
  BarChart3,
  Activity,
  ChevronRight,
  Database,
  RefreshCw,
} from "lucide-react";
import Badge from "../common/Badge";
import { NavLink } from "react-router-dom";
import { useReasoner } from "../../context/ReasonerContext";

// Categorized navigation structure for academic hierarchy
const ROUTE_GROUPS = [
  {
    groupTitle: "Reasoning & Workspace",
    routes: [
      {
        id: "dashboard",
        path: "/",
        label: "Overview Dashboard",
        tamilLabel: "முதன்மைப் பார்வை",
        icon: LayoutGrid,
        defaultBadge: "Full View",
      },
      {
        id: "query-center",
        path: "/query-center",
        label: "Query Center",
        tamilLabel: "வினா அரங்கம்",
        icon: Sparkles,
        defaultBadge: "Interactive",
      },
      {
        id: "reasoning",
        path: "/reasoning",
        label: "Nyāya Reasoning Trace",
        tamilLabel: "பஞ்சாவயவ அனுமானம்",
        icon: Cpu,
        defaultBadge: "5-Stage Proof",
      },
      {
        id: "knowledge-graph",
        path: "/knowledge-graph",
        label: "Knowledge Graph",
        tamilLabel: "அறிவு வரைபடம்",
        icon: Network,
        defaultBadge: "SVG Graph",
      },
    ],
  },
  {
    groupTitle: "Corpus & Evidence",
    routes: [
      {
        id: "evidence",
        path: "/evidence",
        label: "Retrieved Evidence",
        tamilLabel: "சான்றுத் திரட்டு",
        icon: BookOpen,
      },
      {
        id: "sutras",
        path: "/sutras",
        label: "Literature & Corpus",
        tamilLabel: "இலக்கியமும் நூற்பாவும்",
        icon: Library,
      },
    ],
  },
  {
    groupTitle: "Formal Verification",
    routes: [
      {
        id: "fallacies",
        path: "/fallacies",
        label: "Hetvābhāsa Checker",
        tamilLabel: "ஏதுவாபாச ஆய்வு",
        icon: ShieldCheck,
      },
      {
        id: "analytics",
        path: "/analytics",
        label: "Epistemic Analytics",
        tamilLabel: "புள்ளிவிவரம் & நலம்",
        icon: BarChart3,
      },
    ],
  },
];

export default function Sidebar({ sidebarOpen, setSidebarOpen }) {
  const {
    corpus,
    isLoadingCorpus,
    graphStatistics,
    graphHealth,
    isLoadingStats,
    statsError,
    refreshStats,
    systemStatus,
    isLoadingSystemStatus,
    systemStatusError,
    refetchSystemStatus,
    isBackendOnline,
    isNeo4jOnline,
    isRetrievalOnline,
    isSystemDegraded,
  } = useReasoner();

  const currentCorpus = corpus || {
    name: "Tolkāppiyam",
    tamilName: "தொல்காப்பியம்",
    total_sutras_canonical: 1610,
    indexed_sutras_active: 6,
    formattedCount: "1,610 Sūtras",
  };

  // Derive dynamic canonical book counts and distribution percentages from live corpus
  const books = currentCorpus.books || currentCorpus.sections || [];
  const eluttuBook = books.find(
    (b) =>
      b.id === "eluttu" ||
      (b.name && b.name.toLowerCase().includes("eluttu")) ||
      (b.english && b.english.toLowerCase().includes("orthography")),
  );
  const colBook = books.find(
    (b) =>
      b.id === "col" ||
      (b.name && b.name.toLowerCase().includes("col")) ||
      (b.english && b.english.toLowerCase().includes("morphology")),
  );
  const porulBook = books.find(
    (b) =>
      b.id === "porul" ||
      (b.name && b.name.toLowerCase().includes("porul")) ||
      (b.english && b.english.toLowerCase().includes("poetics")),
  );

  const eluttuCount = eluttuBook
    ? (eluttuBook.canonical_sutras_count ??
      eluttuBook.sutra_count ??
      eluttuBook.sutrasCount ??
      483)
    : 483;
  const colCount = colBook
    ? (colBook.canonical_sutras_count ??
      colBook.sutra_count ??
      colBook.sutrasCount ??
      463)
    : 463;
  const porulCount = porulBook
    ? (porulBook.canonical_sutras_count ??
      porulBook.sutra_count ??
      porulBook.sutrasCount ??
      664)
    : 664;

  const totalSutras =
    currentCorpus.total_sutras_canonical ||
    currentCorpus.totalSutras ||
    eluttuCount + colCount + porulCount ||
    1610;

  // Canonical distribution percentage in dataset: Eḻuttu (30.0%), Col (28.8%), Poruḷ (41.2%)
  const eluttuPct =
    totalSutras > 0 ? ((eluttuCount / totalSutras) * 100).toFixed(1) : "30.0";
  const colPct =
    totalSutras > 0 ? ((colCount / totalSutras) * 100).toFixed(1) : "28.8";
  const porulPct =
    totalSutras > 0
      ? (100 - parseFloat(eluttuPct) - parseFloat(colPct)).toFixed(1)
      : "41.2";

  // SVG Circular Gauge calculations for live KG Health
  const radius = 32;
  const circumference = 2 * Math.PI * radius;

  const validPercentage = useMemo(() => {
    if (isLoadingStats) return 0;
    if (statsError || !graphHealth) return 0;
    if (typeof graphHealth.percentageValid === "number") {
      return graphHealth.percentageValid;
    }
    if (graphHealth.valid) {
      return graphHealth.is_connected ? 100 : 92;
    }
    const totalN = graphHealth.node_count || 1;
    const isoCount = Array.isArray(graphHealth.isolated_nodes)
      ? graphHealth.isolated_nodes.length
      : typeof graphHealth.isolated_nodes === "number"
        ? graphHealth.isolated_nodes
        : 0;
    const invEdges = graphHealth.invalid_edges_count || 0;
    return Math.max(
      0,
      Math.round(100 - (isoCount / totalN) * 50 - invEdges * 10),
    );
  }, [isLoadingStats, statsError, graphHealth]);

  const strokeDashoffset =
    isLoadingStats || statsError || !graphHealth
      ? circumference
      : circumference - (validPercentage / 100) * circumference;

  // Live KG structural health metrics derived from real backend data
  const totalNodes =
    graphHealth?.node_count ?? graphStatistics?.total_nodes ?? 0;
  const hierarchy =
    graphHealth?.hierarchy_distribution ??
    graphStatistics?.hierarchy_distribution ??
    {};
  const canonicalNodesCount =
    (hierarchy.L0 || 0) +
    (hierarchy.L1 || 0) +
    (hierarchy.L2 || 0) +
    (hierarchy.L3 || 0) +
    (hierarchy.L4 || 0);
  const verifiedTriplesPct =
    totalNodes > 0 ? Math.round((canonicalNodesCount / totalNodes) * 100) : 0;

  const inferredCount =
    hierarchy.L5 ||
    0 ||
    graphStatistics?.layer_distribution?.["Reasoning Layer"] ||
    0;
  const inferredAxiomsPct =
    totalNodes > 0 ? Math.round((inferredCount / totalNodes) * 100) : 0;

  const isolatedNodesCount = Array.isArray(graphHealth?.isolated_nodes)
    ? graphHealth.isolated_nodes.length
    : typeof graphHealth?.isolated_nodes === "number"
      ? graphHealth.isolated_nodes
      : 0;
  const isolatedPct =
    totalNodes > 0 ? Math.round((isolatedNodesCount / totalNodes) * 100) : 0;

  // Derive dynamic route badges based on real active state and counts

  return (
    <>
      {/* Mobile Backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-950/70 backdrop-blur-xs lg:hidden transition-opacity"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar Container — Fixed on the left */}
      <aside
        className={`fixed top-16 bottom-0 left-0 z-40 w-80 max-w-[85vw] bg-[#090f1d] border-r border-slate-800/90 flex flex-col transition-transform duration-300 ease-in-out lg:translate-x-0 select-none shadow-lg ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Scrollable Main Area with Sleek Custom Scrollbar */}
        <div className="flex-1 overflow-y-auto px-3.5 py-4 space-y-5 text-slate-300 text-xs">
          {/* SECTION 1: Dedicated Corpus Card — Tolkāppiyam */}
          <div className="rounded-xl bg-slate-900/80 border border-slate-800 p-3.5 shadow-2xs">
            {/* Header row */}
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-purple-300/90 flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5 text-purple-400" />
                Active Corpus
              </span>
              {isLoadingCorpus && (
                <span className="text-[9px] font-mono text-purple-400 animate-pulse">
                  Syncing...
                </span>
              )}
            </div>

            {/* Corpus Title & Subtitle */}
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <div className="font-bold text-sm text-slate-100 font-serif leading-tight truncate">
                  {currentCorpus.name}
                </div>
                <div className="text-[11px] text-purple-300/80 font-serif mt-0.5 truncate">
                  {currentCorpus.tamilName}
                </div>
              </div>
              <Badge variant="purpleDark" size="xs">
                {isLoadingCorpus
                  ? "..."
                  : `${totalSutras.toLocaleString()} Sūtras`}
              </Badge>
            </div>

            {/* Atikāram Segmented Distribution Bar */}
            <div className="mt-3 pt-2.5 border-t border-slate-800/80">
              <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1.5 font-mono">
                <span className="whitespace-nowrap">Book Distribution</span>
                <span className="text-slate-300 whitespace-nowrap">
                  {books.length || currentCorpus.books_count || 3} Atikārams
                </span>
              </div>

              {/* Stacked Progress Bar in Canonical Sequence: Eḻuttu (30.0%), Col (28.8%), Poruḷ (41.2%) */}
              <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden flex shadow-inner">
                {/* Eḻuttu */}
                <div
                  className="bg-blue-500 h-full transition-all duration-500"
                  style={{ width: `${eluttuPct}%` }}
                  title={`Eḻuttatikāram (எழுத்து): ${eluttuCount.toLocaleString()} Sūtras (${eluttuPct}%)`}
                />
                {/* Col */}
                <div
                  className="bg-indigo-500 h-full transition-all duration-500"
                  style={{ width: `${colPct}%` }}
                  title={`Collatikāram (சொல்): ${colCount.toLocaleString()} Sūtras (${colPct}%)`}
                />
                {/* Poruḷ */}
                <div
                  className="bg-purple-500 h-full transition-all duration-500"
                  style={{ width: `${porulPct}%` }}
                  title={`Poruḷatikāram (பொருள்): ${porulCount.toLocaleString()} Sūtras (${porulPct}%)`}
                />
              </div>

              {/* 3-Part Micro Grid in Canonical Sequence */}
              <div className="grid grid-cols-3 gap-1.5 mt-2 text-[10px] text-center font-mono">
                <div className="bg-slate-950/70 py-1.5 px-1 rounded border border-slate-800/90 flex flex-col items-center justify-center">
                  <span className="text-slate-400 block text-[10px] font-medium leading-tight">
                    எழுத்து
                  </span>
                  <span className="font-bold text-xs text-blue-300 mt-0.5">
                    {isLoadingCorpus ? "..." : eluttuCount.toLocaleString()}
                  </span>
                </div>
                <div className="bg-slate-950/70 py-1.5 px-1 rounded border border-slate-800/90 flex flex-col items-center justify-center">
                  <span className="text-slate-400 block text-[10px] font-medium leading-tight">
                    சொல்
                  </span>
                  <span className="font-bold text-xs text-indigo-300 mt-0.5">
                    {isLoadingCorpus ? "..." : colCount.toLocaleString()}
                  </span>
                </div>
                <div className="bg-slate-950/70 py-1.5 px-1 rounded border border-slate-800/90 flex flex-col items-center justify-center">
                  <span className="text-slate-400 block text-[10px] font-medium leading-tight">
                    பொருள்
                  </span>
                  <span className="font-bold text-xs text-purple-300 mt-0.5">
                    {isLoadingCorpus ? "..." : porulCount.toLocaleString()}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* SECTION 2: Categorized Navigation Routes */}
          <nav className="space-y-4">
            {ROUTE_GROUPS.map((group) => (
              <div key={group.groupTitle} className="space-y-1.5">
                {/* Group Heading */}
                <div className="px-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  {group.groupTitle}
                </div>

                {/* Group Routes List */}
                <div className="space-y-1">
                  {group.routes.map((route) => {
                    const IconComp = route.icon;

                    return (
                      <NavLink
                        key={route.id}
                        to={route.path}
                        end={route.path === "/"}
                        onClick={() => {
                          if (setSidebarOpen) setSidebarOpen(false);
                        }}
                        className={({ isActive }) =>
                          `w-full text-left px-3 py-2 rounded-xl border transition-all duration-150 flex items-center justify-between gap-2 cursor-pointer group ${
                            isActive
                              ? "bg-purple-900/50 border-purple-500/70 text-white shadow-xs font-semibold ring-1 ring-purple-500/30"
                              : "bg-slate-900/40 border-slate-800/60 text-slate-300 hover:bg-slate-850 hover:border-slate-700 hover:text-white"
                          }`
                        }
                      >
                        {({ isActive }) => (
                          <>
                            <div className="flex items-center gap-2.5 min-w-0">
                              <span
                                className={`p-1 rounded-lg transition-colors ${
                                  isActive
                                    ? "bg-purple-800/80 text-purple-200"
                                    : "bg-slate-800/60 text-slate-400 group-hover:text-slate-200 group-hover:bg-slate-800"
                                }`}
                              >
                                <IconComp className="w-3.5 h-3.5 shrink-0" />
                              </span>

                              <div className="min-w-0">
                                <span className="text-xs tracking-tight block truncate leading-snug">
                                  {route.label}
                                </span>
                                <span className="text-[10px] text-slate-400 font-serif block truncate">
                                  {route.tamilLabel}
                                </span>
                              </div>
                            </div>

                            <div className="flex items-center gap-1.5 shrink-0">
                              <ChevronRight
                                className={`w-3 h-3 transition-transform ${
                                  isActive
                                    ? "text-purple-300 translate-x-0.5"
                                    : "text-slate-500 opacity-0 group-hover:opacity-100"
                                }`}
                              />
                            </div>
                          </>
                        )}
                      </NavLink>
                    );
                  })}
                </div>
              </div>
            ))}
          </nav>

          {/* SECTION 3: Unified Knowledge Graph & Epistemic Health Card */}
          <div className="rounded-xl bg-slate-900/80 border border-slate-800 p-3.5 shadow-2xs space-y-3">
            {/* Title */}
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5 text-emerald-400" />
                Knowledge Graph Health
              </span>
              <span
                className={`text-[10px] font-mono px-1.5 py-0.5 rounded border transition-colors ${
                  isLoadingStats
                    ? "text-purple-400 bg-purple-950/70 border-purple-800/50"
                    : statsError || !graphHealth
                      ? "text-rose-400 bg-rose-950/70 border-rose-800/50"
                      : graphHealth.valid
                        ? "text-emerald-400 bg-emerald-950/70 border-emerald-800/50"
                        : "text-amber-400 bg-amber-950/70 border-amber-800/50"
                }`}
              >
                {isLoadingStats
                  ? "SYNCING"
                  : statsError || !graphHealth
                    ? "OFFLINE"
                    : graphHealth.valid
                      ? "OPTIMAL"
                      : "DEGRADED"}
              </span>
            </div>

            {/* Circular Gauge and Legend in neat horizontal layout */}
            <div className="flex items-center gap-3">
              {/* Circular Gauge */}
              <div className="relative flex items-center justify-center shrink-0 w-18 h-18">
                <svg className="w-full h-full -rotate-90" viewBox="0 0 80 80">
                  <circle
                    cx="40"
                    cy="40"
                    r={radius}
                    className="stroke-slate-800"
                    strokeWidth="6.5"
                    fill="transparent"
                  />
                  <circle
                    cx="40"
                    cy="40"
                    r={radius}
                    stroke="url(#sidebarKgGradient)"
                    strokeWidth="6.5"
                    fill="transparent"
                    strokeDasharray={circumference}
                    strokeDashoffset={strokeDashoffset}
                    strokeLinecap="round"
                    className="transition-all duration-700 ease-out"
                  />
                  <defs>
                    <linearGradient
                      id="sidebarKgGradient"
                      x1="0%"
                      y1="0%"
                      x2="100%"
                      y2="100%"
                    >
                      <stop offset="0%" stopColor="#10b981" />
                      <stop offset="70%" stopColor="#059669" />
                      <stop offset="100%" stopColor="#8b5cf6" />
                    </linearGradient>
                  </defs>
                </svg>

                {/* Center Value */}
                <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                  <span className="text-sm font-extrabold text-slate-100 font-mono leading-none">
                    {isLoadingStats
                      ? "..."
                      : statsError || !graphHealth
                        ? "ERR"
                        : `${validPercentage}%`}
                  </span>
                  <span
                    className={`text-[9px] font-semibold uppercase mt-0.5 ${
                      statsError || !graphHealth
                        ? "text-rose-400"
                        : graphHealth?.valid
                          ? "text-emerald-400"
                          : "text-amber-400"
                    }`}
                  >
                    {isLoadingStats
                      ? "Syncing"
                      : statsError || !graphHealth
                        ? "Offline"
                        : graphHealth.valid
                          ? "Valid"
                          : "Degraded"}
                  </span>
                </div>
              </div>

              {/* Dynamic Legend */}
              <div className="flex-1 space-y-1 text-[11px]">
                {[
                  {
                    label: "Verified Triples",
                    percentage: verifiedTriplesPct,
                    bgDot: "bg-emerald-400",
                    textColor: "text-emerald-400",
                  },
                  {
                    label: "Inferred Axioms",
                    percentage: inferredAxiomsPct,
                    bgDot: "bg-purple-400",
                    textColor: "text-purple-400",
                  },
                  {
                    label: "Isolated Nodes",
                    percentage: isolatedPct,
                    bgDot:
                      isolatedNodesCount > 0 ? "bg-amber-400" : "bg-slate-400",
                    textColor:
                      isolatedNodesCount > 0
                        ? "text-amber-400"
                        : "text-slate-400",
                  },
                ].map((item) => (
                  <div
                    key={item.label}
                    className="flex items-center justify-between"
                  >
                    <div className="flex items-center gap-1.5">
                      <span
                        className={`w-1.5 h-1.5 rounded-full shrink-0 ${item.bgDot}`}
                      />
                      <span className="text-slate-400 text-[10px]">
                        {item.label}
                      </span>
                    </div>
                    <span
                      className={`font-mono text-[10px] font-semibold ${item.textColor}`}
                    >
                      {isLoadingStats ? "..." : `${item.percentage}%`}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Error / Re-sync Banner */}
            {statsError && (
              <div className="flex items-center justify-between text-[10px] text-amber-400 bg-amber-950/40 border border-amber-800/40 px-2 py-1 rounded">
                <span className="truncate max-w-42.5">Data Sync Offline</span>
                {refreshStats && (
                  <button
                    type="button"
                    onClick={() => refreshStats()}
                    className="text-amber-300 hover:text-white flex items-center gap-1 text-[9px] cursor-pointer"
                  >
                    <RefreshCw className="w-2.5 h-2.5" />
                    Retry
                  </button>
                )}
              </div>
            )}

            {/* Quick Stats 4-Chip Grid from live backend statistics */}
            <div className="pt-2 border-t border-slate-800/80 grid grid-cols-2 gap-1.5 text-center font-mono">
              <div className="bg-slate-950/60 p-1.5 rounded border border-slate-800/80">
                <span className="text-slate-400 block text-[9px]">
                  Relations
                </span>
                <span className="font-bold text-xs text-slate-200">
                  {isLoadingStats
                    ? "..."
                    : (graphStatistics?.total_edges ??
                      graphStatistics?.relation_count ??
                      0)}
                </span>
              </div>
              <div className="bg-slate-950/60 p-1.5 rounded border border-slate-800/80">
                <span className="text-slate-400 block text-[9px]">
                  Entities
                </span>
                <span className="font-bold text-xs text-slate-200">
                  {isLoadingStats
                    ? "..."
                    : (graphStatistics?.total_nodes ??
                      graphStatistics?.entity_count ??
                      0)}
                </span>
              </div>
              <div className="bg-slate-950/60 p-1.5 rounded border border-slate-800/80">
                <span className="text-slate-400 block text-[9px]">
                  Concepts
                </span>
                <span className="font-bold text-xs text-slate-200">
                  {isLoadingStats
                    ? "..."
                    : (graphStatistics?.layer_distribution?.["Concept Layer"] ??
                      graphStatistics?.hierarchy_distribution?.L4 ??
                      graphStatistics?.layer_distribution
                        ?.Ontological_Concepts ??
                      0)}
                </span>
              </div>
              <div className="bg-slate-950/60 p-1.5 rounded border border-slate-800/80">
                <span className="text-slate-400 block text-[9px]">Rules</span>
                <span className="font-bold text-xs text-purple-300">
                  {isLoadingStats
                    ? "..."
                    : (graphStatistics?.layer_distribution?.[
                        "Reasoning Layer"
                      ] ??
                      (graphStatistics?.hierarchy_distribution?.L4 != null ||
                      graphStatistics?.hierarchy_distribution?.L5 != null
                        ? (graphStatistics.hierarchy_distribution.L4 || 0) +
                          (graphStatistics.hierarchy_distribution.L5 || 0)
                        : (graphStatistics?.hierarchy_distribution
                            ?.Axiom_Rules ?? 0)))}
                </span>
              </div>
            </div>
          </div>

          {/* SECTION 4: Live Subsystems & Real-Time Service Health Monitoring */}
          <div className="rounded-xl bg-slate-900/80 border border-slate-800/90 p-3 shadow-sm text-[10px] text-slate-400 space-y-2.5">
            {/* Header with overall status badge and ping action */}
            <div className="flex items-center justify-between pb-1.5 border-b border-slate-800/60">
              <span className="font-semibold text-slate-200 text-[11px] flex items-center gap-1.5">
                <span
                  className={`w-2 h-2 rounded-full ${
                    isLoadingSystemStatus
                      ? "bg-purple-400 animate-pulse"
                      : !isBackendOnline || systemStatusError
                        ? "bg-rose-500 animate-ping"
                        : isSystemDegraded
                          ? "bg-amber-400"
                          : "bg-emerald-400"
                  }`}
                />
                Service Connectivity
              </span>
              <div className="flex items-center gap-2">
                <span
                  className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-bold uppercase ${
                    !isBackendOnline || systemStatusError
                      ? "bg-rose-900/50 text-rose-300 border border-rose-700/50"
                      : isSystemDegraded
                        ? "bg-amber-900/50 text-amber-300 border border-amber-700/50"
                        : "bg-emerald-900/50 text-emerald-300 border border-emerald-700/50"
                  }`}
                >
                  {isLoadingSystemStatus
                    ? "Syncing"
                    : !isBackendOnline || systemStatusError
                      ? "Offline"
                      : isSystemDegraded
                        ? "Degraded"
                        : "Healthy"}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    if (refetchSystemStatus) refetchSystemStatus();
                  }}
                  disabled={isLoadingSystemStatus}
                  className="text-[9px] text-purple-400 hover:text-purple-300 font-mono transition-colors cursor-pointer"
                  title="Ping all backend services"
                >
                  {isLoadingSystemStatus ? "..." : "↻"}
                </button>
              </div>
            </div>

            {/* Individual Sub-Service Indicators */}
            <div className="space-y-1.5 font-mono text-[9px]">
              {/* 1. Flask Core Application */}
              <div className="flex items-center justify-between">
                <span className="text-slate-400 font-sans">Flask Core API</span>
                <span className="flex items-center gap-1">
                  <span
                    className={`w-1 h-1 rounded-full ${
                      isBackendOnline ? "bg-emerald-400" : "bg-rose-500"
                    }`}
                  />
                  <span className={isBackendOnline ? "text-slate-300" : "text-rose-400"}>
                    {isBackendOnline
                      ? `${systemStatus?.services?.application?.latency_ms ?? 0} ms`
                      : "Unreachable"}
                  </span>
                </span>
              </div>

              {/* 2. Neo4j Aura Database */}
              <div className="flex items-center justify-between">
                <span className="text-slate-400 font-sans">Neo4j Aura DB</span>
                <span className="flex items-center gap-1">
                  <span
                    className={`w-1 h-1 rounded-full ${
                      isNeo4jOnline ? "bg-emerald-400" : "bg-amber-400"
                    }`}
                  />
                  <span className={isNeo4jOnline ? "text-slate-300" : "text-amber-400"}>
                    {isNeo4jOnline
                      ? `${systemStatus?.services?.database?.database || "Aura"} (${systemStatus?.services?.database?.latency_ms ?? 0}ms)`
                      : "Disconnected"}
                  </span>
                </span>
              </div>

              {/* 3. Hybrid RAG Retrieval Engine */}
              <div className="flex items-center justify-between">
                <span className="text-slate-400 font-sans">RAG Retrieval</span>
                <span className="flex items-center gap-1">
                  <span
                    className={`w-1 h-1 rounded-full ${
                      isRetrievalOnline ? "bg-emerald-400" : "bg-slate-500"
                    }`}
                  />
                  <span className="text-slate-300">
                    {isRetrievalOnline
                      ? `${systemStatus?.services?.retrieval?.faiss_indexed_chunks ?? 0} Chunks`
                      : "Not Ready"}
                  </span>
                </span>
              </div>

              {/* 4. Active Canonical Corpus */}
              <div className="flex items-center justify-between pt-1 border-t border-slate-800/40 text-slate-500">
                <span className="font-sans truncate max-w-28">{currentCorpus.name}</span>
                <span>
                  {currentCorpus.indexed_sutras_active ?? 0} Active Sūtras
                </span>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
