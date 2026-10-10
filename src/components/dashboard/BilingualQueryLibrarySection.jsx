import { useState, useMemo, useRef, useCallback, useEffect } from "react";
import {
  Sparkles,
  Search,
  BookOpen,
  Copy,
  Check,
  Play,
  RotateCcw,
  Download,
  ChevronDown,
  ChevronUp,
  LayoutGrid,
  List,
  Compass,
  ArrowUp,
  ChevronLeft,
  ChevronRight,
  Info,
} from "lucide-react";
import Badge from "../common/Badge";
import Button from "../common/Button";
import { useNavigate, useLocation } from "react-router-dom";
import { useReasoner } from "../../context/ReasonerContext";
import canonicalQueriesData from "../../data/canonical_1000_queries.json";

// Stable reference to the canonical queries dataset
const ALL_QUERIES = Array.isArray(canonicalQueriesData) ? canonicalQueriesData : [];

export default function BilingualQueryLibrarySection() {
  const navigate = useNavigate();
  const location = useLocation();

  const {
    setQueryText,
    setQueryType,
    setDepth,
    setFocus,
    runAnalyze,
    handleSelectExample,
  } = useReasoner();

  // Data & View States
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedTheme, setSelectedTheme] = useState("all");
  const [selectedType, setSelectedType] = useState("all");
  const [selectedDifficulty, setSelectedDifficulty] = useState("all");
  const [selectedThinai, setSelectedThinai] = useState("all");
  const [viewMode, setViewMode] = useState("grid"); // 'grid' | 'table'
  const [isExpanded, setIsExpanded] = useState(true);

  // Pagination States
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(24);

  // Interactivity feedback states
  const [copiedId, setCopiedId] = useState(null);
  const [highlightedId, setHighlightedId] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);
  const [expandedDetailsId, setExpandedDetailsId] = useState(null);

  const sectionRef = useRef(null);
  const toastTimerRef = useRef(null);
  const highlightTimerRef = useRef(null);
  const copyTimerRef = useRef(null);

  // Clean up any pending timers on unmount
  useEffect(() => {
    const toastRef = toastTimerRef;
    const highlightRef = highlightTimerRef;
    const copyRef = copyTimerRef;
    return () => {
      if (toastRef.current) clearTimeout(toastRef.current);
      if (highlightRef.current) clearTimeout(highlightRef.current);
      if (copyRef.current) clearTimeout(copyRef.current);
    };
  }, []);

  // Show brief feedback toast with timer management
  const showToast = useCallback((msg) => {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    setToastMessage(msg);
    toastTimerRef.current = setTimeout(() => {
      setToastMessage(null);
    }, 3200);
  }, []);

  // Theme lists with counts
  const themeList = useMemo(() => {
    const counts = {};
    for (const q of ALL_QUERIES) {
      counts[q.theme] = (counts[q.theme] || 0) + 1;
    }
    return [
      { id: "all", label: "All Inquiries (அனைத்தும்)", count: ALL_QUERIES.length },
      { id: "Grammar", label: "Grammar (இலக்கணம்)", count: counts["Grammar"] || 0 },
      { id: "Akam", label: "Akam Love (அகத்திணை)", count: counts["Akam"] || 0 },
      { id: "Puram", label: "Puram Heroics (புறத்திணை)", count: counts["Puram"] || 0 },
      { id: "Culture", label: "Culture & Ethics (அறம்)", count: counts["Culture"] || 0 },
      { id: "Literature", label: "Literature (இலக்கியம்)", count: counts["Literature"] || 0 },
      { id: "Commentary", label: "Commentary (உரை மரபு)", count: counts["Commentary"] || 0 },
      { id: "Meta", label: "Meta & Poetics (மெய்யியல்)", count: (counts["Meta"] || 0) + (counts["Porul"] || 0) },
    ];
  }, []);

  // Unique landscapes / thinai list
  const thinaiList = useMemo(() => {
    const s = new Set();
    for (const q of ALL_QUERIES) {
      if (q.thinai) s.add(q.thinai);
    }
    return Array.from(s).sort();
  }, []);

  // Client-side filtering with memoization
  const filteredQueries = useMemo(() => {
    const searchLower = searchTerm.trim().toLowerCase();
    return ALL_QUERIES.filter((q) => {
      // Theme filter
      if (selectedTheme !== "all") {
        if (selectedTheme === "Meta") {
          if (q.theme !== "Meta" && q.theme !== "Porul") return false;
        } else if (q.theme !== selectedTheme) {
          return false;
        }
      }

      // Query Type filter
      if (selectedType !== "all" && !q.queryType.toLowerCase().includes(selectedType.toLowerCase())) {
        return false;
      }

      // Difficulty filter
      if (selectedDifficulty !== "all" && q.difficulty !== selectedDifficulty) {
        return false;
      }

      // Thinai filter
      if (selectedThinai !== "all" && q.thinai !== selectedThinai) {
        return false;
      }

      // Search term filter
      if (searchLower) {
        const inQuery = q.query?.toLowerCase().includes(searchLower);
        const inTamil = q.tamilQuery?.toLowerCase().includes(searchLower);
        const inTitle = q.title?.toLowerCase().includes(searchLower);
        const inConcept =
          q.tamilConcept?.toLowerCase().includes(searchLower) ||
          q.englishConcept?.toLowerCase().includes(searchLower);
        const inDesc = q.description?.toLowerCase().includes(searchLower);
        const inKeywords = (q.keywords || []).some((k) =>
          k.toLowerCase().includes(searchLower)
        );
        const inId = q.id?.toLowerCase().includes(searchLower);
        if (!inQuery && !inTamil && !inTitle && !inConcept && !inDesc && !inKeywords && !inId) {
          return false;
        }
      }

      return true;
    });
  }, [searchTerm, selectedTheme, selectedType, selectedDifficulty, selectedThinai]);

  // Pagination calculation
  const totalPages = Math.ceil(filteredQueries.length / pageSize) || 1;
  const safeCurrentPage = Math.min(Math.max(currentPage, 1), totalPages);
  const paginatedQueries = useMemo(() => {
    const start = (safeCurrentPage - 1) * pageSize;
    return filteredQueries.slice(start, start + pageSize);
  }, [filteredQueries, safeCurrentPage, pageSize]);

  // Reset pagination when filters change
  const handleThemeChange = (themeId) => {
    setSelectedTheme(themeId);
    setCurrentPage(1);
  };

  const handleSearchChange = (val) => {
    setSearchTerm(val);
    setCurrentPage(1);
  };

  const resetAllFilters = () => {
    setSearchTerm("");
    setSelectedTheme("all");
    setSelectedType("all");
    setSelectedDifficulty("all");
    setSelectedThinai("all");
    setCurrentPage(1);
  };

  // Actions
  const handleLoadQuery = (q, shouldExecute = false) => {
    if (!q) return;

    if (handleSelectExample) {
      handleSelectExample({
        id: q.id,
        query: q.query,
        queryType: q.queryType || "Why / Justification",
        depth: q.depth || 2,
        focus: q.theme === "Culture" ? "Judgment / Justice" : "Relationship",
        corpusName: "Tolkāppiyam (தொல்காப்பியம்)",
        translation: q.description || q.tamilQuery,
        description: q.description,
      });
    } else {
      setQueryText(q.query);
      if (q.queryType) setQueryType(q.queryType);
      if (q.depth) setDepth(q.depth);
      setFocus(q.theme === "Culture" ? "Judgment / Justice" : "Relationship");
    }

    setHighlightedId(q.id);
    if (highlightTimerRef.current) clearTimeout(highlightTimerRef.current);
    highlightTimerRef.current = setTimeout(() => setHighlightedId(null), 3000);

    if (shouldExecute) {
      showToast(`Loaded "${q.id}" and executing epistemic analysis...`);
    } else {
      showToast(`Inquiry "${q.id}" loaded into Query Center.`);
    }

    if (location.pathname !== "/query-center") {
      navigate("/query-center");
      if (shouldExecute) {
        setTimeout(() => {
          if (runAnalyze) runAnalyze();
        }, 300);
      }
    } else {
      if (shouldExecute) {
        setTimeout(() => {
          if (runAnalyze) runAnalyze();
        }, 150);
      }

      // Smooth scroll back to Query Input textarea
      const queryInputEl = document.querySelector('textarea[placeholder*="Classical Tamil"]');
      if (queryInputEl) {
        queryInputEl.scrollIntoView({ behavior: "smooth", block: "center" });
        setTimeout(() => {
          queryInputEl.focus();
        }, 400);
      } else {
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    }
  };

  const handleCopyQuery = (q) => {
    if (!q) return;
    const textToCopy = `${q.query}\n[Canonical: ${q.canonicalForm || q.id}]`;
    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(textToCopy);
      setCopiedId(q.id);
      showToast(`Copied inquiry "${q.id}" to clipboard.`);
      if (copyTimerRef.current) clearTimeout(copyTimerRef.current);
      copyTimerRef.current = setTimeout(() => setCopiedId(null), 2500);
    }
  };

  const handlePickRandom = () => {
    if (ALL_QUERIES.length === 0) return;
    const randomIndex = Math.floor(Math.random() * ALL_QUERIES.length);
    const randomQ = ALL_QUERIES[randomIndex];
    handleLoadQuery(randomQ, false);
  };

  const handleDownloadDataset = (format = "json") => {
    if (format === "json") {
      const blob = new Blob([JSON.stringify(ALL_QUERIES, null, 2)], {
        type: "application/json;charset=utf-8",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `tolkappiyam_bilingual_queries.json`;
      link.click();
      URL.revokeObjectURL(url);
      showToast("Downloaded queries dataset as JSON file.");
    } else if (format === "csv") {
      const headers = [
        "id",
        "title",
        "query",
        "tamilQuery",
        "category",
        "theme",
        "thinai",
        "tamilConcept",
        "englishConcept",
        "queryType",
        "difficulty",
        "relation",
        "canonicalForm",
      ];
      const rows = ALL_QUERIES.map((q) =>
        headers
          .map((h) => {
            const val = q[h] || "";
            return `"${String(val).replace(/"/g, '""')}"`;
          })
          .join(",")
      );
      const csvContent = "\uFEFF" + [headers.join(","), ...rows].join("\n");
      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `tolkappiyam_bilingual_queries.csv`;
      link.click();
      URL.revokeObjectURL(url);
      showToast("Downloaded queries dataset as CSV file.");
    }
  };

  // Helper for difficulty badge
  const getDifficultyBadge = (diff) => {
    switch (diff) {
      case "Beginner":
        return <Badge variant="green" size="xs">Beginner</Badge>;
      case "Intermediate":
        return <Badge variant="blue" size="xs">Intermediate</Badge>;
      case "Advanced":
      default:
        return <Badge variant="purple" size="xs">Advanced</Badge>;
    }
  };

  // Helper for queryType badge
  const getQueryTypeBadge = (qt) => {
    if (qt.includes("Why")) {
      return (
        <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-amber-50 text-amber-800 border border-amber-200 font-semibold">
          Why / Justification
        </span>
      );
    }
    if (qt.includes("How")) {
      return (
        <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-sky-50 text-sky-800 border border-sky-200 font-semibold">
          How / Process
        </span>
      );
    }
    if (qt.includes("What")) {
      return (
        <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-800 border border-emerald-200 font-semibold">
          What / Fact
        </span>
      );
    }
    return (
      <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-purple-50 text-purple-800 border border-purple-200 font-semibold">
        Who / Entity
      </span>
    );
  };

  return (
    <section
      id="bilingual-query-catalog"
      ref={sectionRef}
      className="bg-white rounded-2xl border border-slate-200 shadow-sm border-t-4 border-t-indigo-600 transition-all overflow-hidden scroll-mt-6"
      aria-label="Canonical Mixed Tamil and English Inquiries Library"
    >
      {/* Toast Notification Banner */}
      {toastMessage && (
        <div className="bg-indigo-600 text-white px-4 py-2.5 text-xs sm:text-sm font-semibold flex items-center justify-between shadow-md animate-in fade-in slide-in-from-top-1 duration-200">
          <div className="flex items-center gap-2">
            <Check className="w-4 h-4 text-emerald-300" />
            <span>{toastMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => setToastMessage(null)}
            className="text-white/80 hover:text-white cursor-pointer text-xs"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Header */}
      <div className="px-5 sm:px-6 py-5 border-b border-slate-100 bg-gradient-to-r from-slate-50 via-indigo-50/20 to-purple-50/30 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex items-start gap-3.5">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-indigo-600 to-purple-700 text-white shadow-md mt-0.5">
            <BookOpen className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h2 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight flex items-center gap-2">
                <span>BILINGUAL RESEARCH QUERIES LIBRARY</span>
              </h2>
              <Badge variant="purple" size="xs">
                Curated Inquiries
              </Badge>
              <span className="text-xs font-semibold text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded-full">
                இருமொழி வினா களஞ்சியம்
              </span>
            </div>
            <p className="text-xs sm:text-sm text-slate-600 mt-1 leading-relaxed">
              Curated canonical repository of mixed Classical Tamil and English research inquiries across Tolkāppiyam Grammar, Akam & Puram poetics, Tiṇai eco-semiotics, and epistemic logic. Readily loadable and executable in Query Center.
            </p>
          </div>
        </div>

        {/* Top Controls Toolbar */}
        <div className="flex items-center gap-2 sm:gap-2.5 flex-wrap self-start lg:self-auto">
          {/* Pick Random Query */}
          <Button
            variant="outline"
            size="sm"
            onClick={handlePickRandom}
            icon={Sparkles}
            className="text-xs font-bold text-indigo-700 border-indigo-200 bg-indigo-50/50 hover:bg-indigo-100 hover:border-indigo-300"
            title="Pick a random inquiry and load it"
          >
            Inspire Me (ஏதேனும் ஒன்று)
          </Button>

          {/* Export Dropdown */}
          <div className="relative group">
            <Button
              variant="outline"
              size="sm"
              icon={Download}
              className="text-xs font-semibold text-slate-700 border-slate-200 hover:bg-slate-100"
            >
              Export
            </Button>
            <div className="hidden group-hover:block absolute right-0 mt-1 w-44 bg-white border border-slate-200 rounded-xl shadow-xl py-1.5 z-30 text-xs">
              <button
                type="button"
                onClick={() => handleDownloadDataset("json")}
                className="w-full text-left px-3.5 py-2 hover:bg-indigo-50 text-slate-700 hover:text-indigo-900 flex items-center justify-between cursor-pointer"
              >
                <span>Download as JSON</span>
                <span className="text-[10px] font-mono text-slate-400">1.6 MB</span>
              </button>
              <button
                type="button"
                onClick={() => handleDownloadDataset("csv")}
                className="w-full text-left px-3.5 py-2 hover:bg-indigo-50 text-slate-700 hover:text-indigo-900 flex items-center justify-between cursor-pointer"
              >
                <span>Download as CSV</span>
                <span className="text-[10px] font-mono text-slate-400">Sheet</span>
              </button>
            </div>
          </div>

          {/* View Toggle */}
          <div className="flex items-center rounded-lg border border-slate-200 bg-slate-100 p-0.5">
            <button
              type="button"
              onClick={() => setViewMode("grid")}
              className={`p-1.5 rounded-md text-xs font-medium cursor-pointer transition-colors ${
                viewMode === "grid"
                  ? "bg-white text-indigo-700 shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
              title="Grid View"
            >
              <LayoutGrid className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setViewMode("table")}
              className={`p-1.5 rounded-md text-xs font-medium cursor-pointer transition-colors ${
                viewMode === "table"
                  ? "bg-white text-indigo-700 shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
              title="Table View"
            >
              <List className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Collapse / Expand Toggle */}
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-600 cursor-pointer"
            title={isExpanded ? "Collapse Section" : "Expand Section"}
          >
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="p-4 sm:p-6 space-y-5">
          {/* Filter & Search Bar */}
          <div className="space-y-3.5 bg-slate-50/80 p-4 rounded-xl border border-slate-200/90">
            {/* Search Input Row */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
              <div className="relative flex-1">
                <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => handleSearchChange(e.target.value)}
                  placeholder="Search queries by English keyword, Tamil term (எழுத்து, திணை), sutra ID, or concept..."
                  className="w-full bg-white border border-slate-200 hover:border-slate-300 rounded-xl pl-9 pr-9 py-2.5 text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 shadow-xs outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all font-sans"
                />
                {searchTerm && (
                  <button
                    type="button"
                    onClick={() => handleSearchChange("")}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 p-0.5 rounded cursor-pointer"
                    title="Clear search"
                  >
                    ×
                  </button>
                )}
              </div>

              {/* Secondary Select Dropdowns */}
              <div className="flex items-center gap-2 flex-wrap sm:flex-nowrap">
                {/* Query Type Select */}
                <select
                  value={selectedType}
                  onChange={(e) => {
                    setSelectedType(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 shadow-2xs outline-none focus:border-indigo-500 cursor-pointer"
                >
                  <option value="all">All Query Types</option>
                  <option value="Why">Why / Justification</option>
                  <option value="How">How / Process</option>
                  <option value="What">What / Fact</option>
                  <option value="Who">Who / Entity</option>
                </select>

                {/* Difficulty Select */}
                <select
                  value={selectedDifficulty}
                  onChange={(e) => {
                    setSelectedDifficulty(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 shadow-2xs outline-none focus:border-indigo-500 cursor-pointer"
                >
                  <option value="all">All Difficulties</option>
                  <option value="Beginner">Beginner</option>
                  <option value="Intermediate">Intermediate</option>
                  <option value="Advanced">Advanced</option>
                </select>

                {/* Landscape / Thinai Select */}
                <select
                  value={selectedThinai}
                  onChange={(e) => {
                    setSelectedThinai(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs font-medium text-slate-800 shadow-2xs outline-none focus:border-indigo-500 cursor-pointer max-w-[150px] truncate"
                >
                  <option value="all">All Landscapes (திணை)</option>
                  {thinaiList.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Category / Theme Horizontal Filter Tabs */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-thin">
              {themeList.map((item) => {
                const isActive = selectedTheme === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => handleThemeChange(item.id)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-1.5 cursor-pointer shrink-0 ${
                      isActive
                        ? "bg-indigo-600 text-white shadow-xs"
                        : "bg-white text-slate-600 hover:text-indigo-900 hover:bg-indigo-50/70 border border-slate-200/80"
                    }`}
                  >
                    <span>{item.label}</span>
                    <span
                      className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                        isActive
                          ? "bg-indigo-500 text-white"
                          : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {item.count}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Active Filters / Results Status Bar */}
            <div className="flex items-center justify-between text-xs text-slate-600 pt-1 border-t border-slate-200/60 flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-800">
                  Showing {filteredQueries.length === 0 ? 0 : (safeCurrentPage - 1) * pageSize + 1}–
                  {Math.min(safeCurrentPage * pageSize, filteredQueries.length)} of{" "}
                  <strong className="text-indigo-700">{filteredQueries.length}</strong> matching inquiries
                </span>
                {filteredQueries.length !== ALL_QUERIES.length && (
                  <Badge variant="blue" size="xs">
                    Filtered
                  </Badge>
                )}
              </div>

              {(searchTerm ||
                selectedTheme !== "all" ||
                selectedType !== "all" ||
                selectedDifficulty !== "all" ||
                selectedThinai !== "all") && (
                <button
                  type="button"
                  onClick={resetAllFilters}
                  className="text-xs font-semibold text-rose-600 hover:text-rose-800 inline-flex items-center gap-1 cursor-pointer"
                >
                  <RotateCcw className="w-3 h-3" />
                  Reset all filters
                </button>
              )}
            </div>
          </div>

          {/* Empty State */}
          {filteredQueries.length === 0 && (
            <div className="text-center py-12 px-4 bg-slate-50 rounded-2xl border border-dashed border-slate-200">
              <Compass className="w-10 h-10 text-slate-300 mx-auto mb-3" />
              <h3 className="text-sm font-bold text-slate-800">No matching inquiries found</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                No inquiries matched your current filter criteria &quot;{searchTerm}&quot;. Try broadening keywords or clearing filters.
              </p>
              <div className="mt-4">
                <Button variant="outline" size="sm" onClick={resetAllFilters}>
                  Clear all filters
                </Button>
              </div>
            </div>
          )}

          {/* GRID VIEW */}
          {viewMode === "grid" && filteredQueries.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {paginatedQueries.map((q) => {
                const isSelected = highlightedId === q.id;
                const isCopied = copiedId === q.id;
                const isExpandedDetails = expandedDetailsId === q.id;

                return (
                  <div
                    key={q.id}
                    className={`bg-white rounded-xl border transition-all duration-150 flex flex-col justify-between hover:shadow-md hover:border-indigo-300 group p-4 relative ${
                      isSelected
                        ? "border-indigo-600 ring-2 ring-indigo-500/20 bg-indigo-50/20"
                        : "border-slate-200"
                    }`}
                  >
                    {/* Top Meta Header */}
                    <div>
                      <div className="flex items-center justify-between gap-1.5 mb-2.5">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="font-mono text-[10px] font-bold text-indigo-700 bg-indigo-50 border border-indigo-200/80 px-1.5 py-0.5 rounded">
                            {q.id}
                          </span>
                          <span className="text-[10px] font-medium text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded">
                            {q.theme}
                          </span>
                        </div>
                        <div className="flex items-center gap-1">
                          {getDifficultyBadge(q.difficulty)}
                          {getQueryTypeBadge(q.queryType)}
                        </div>
                      </div>

                      {/* Title */}
                      <h3 className="text-xs font-bold text-slate-900 tracking-tight flex items-center justify-between gap-2">
                        <span>{q.title}</span>
                      </h3>

                      {/* Primary Mixed Tamil + English Query */}
                      <p className="mt-2 text-xs sm:text-sm font-semibold text-slate-800 leading-snug font-serif group-hover:text-indigo-950 transition-colors">
                        {q.query}
                      </p>

                      {/* Classical Tamil formulation */}
                      {q.tamilQuery && (
                        <p className="tamil-font text-[11px] text-slate-500 italic mt-1.5 border-l-2 border-indigo-300 pl-2 leading-relaxed">
                          {q.tamilQuery}
                        </p>
                      )}

                      {/* Concept mapping tag */}
                      <div className="mt-2.5 pt-2 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-500 font-mono">
                        <span className="truncate pr-1">
                          {q.relation ? `rel: ${q.relation}` : `thinai: ${q.thinai}`}
                        </span>
                        <span className="text-indigo-600 font-semibold shrink-0">
                          Depth: {q.depth || 2}
                        </span>
                      </div>

                      {/* Expandable Details Drawer */}
                      {isExpandedDetails && (
                        <div className="mt-2.5 p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-[11px] space-y-1.5 animate-in fade-in duration-150">
                          <div>
                            <span className="font-bold text-slate-700">Canonical: </span>
                            <span className="font-mono text-slate-600">{q.canonicalForm}</span>
                          </div>
                          <div>
                            <span className="font-bold text-slate-700">Epistemic Note: </span>
                            <span className="text-slate-600">{q.description}</span>
                          </div>
                          {q.keywords && (
                            <div className="flex items-center gap-1 flex-wrap pt-1">
                              <span className="font-bold text-slate-700">Keywords:</span>
                              {q.keywords.map((k) => (
                                <span
                                  key={k}
                                  className="text-[9px] bg-white border border-slate-200 px-1 py-0.5 rounded text-slate-600"
                                >
                                  {k}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Bottom Action Controls */}
                    <div className="mt-3.5 pt-2.5 border-t border-slate-100 flex items-center justify-between gap-1.5">
                      <div className="flex items-center gap-1">
                        {/* Copy Query Button */}
                        <button
                          type="button"
                          onClick={() => handleCopyQuery(q)}
                          className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-600 hover:text-slate-900 cursor-pointer transition-colors"
                          title="Copy query text"
                        >
                          {isCopied ? (
                            <Check className="w-3.5 h-3.5 text-emerald-600" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>

                        {/* Details Toggle */}
                        <button
                          type="button"
                          onClick={() =>
                            setExpandedDetailsId(isExpandedDetails ? null : q.id)
                          }
                          className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-600 hover:text-slate-900 cursor-pointer transition-colors"
                          title="View canonical details"
                        >
                          <Info className="w-3.5 h-3.5" />
                        </button>
                      </div>

                      <div className="flex items-center gap-1.5">
                        {/* Load in Query Center */}
                        <button
                          type="button"
                          onClick={() => handleLoadQuery(q, false)}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-indigo-50 text-indigo-700 hover:bg-indigo-100 hover:text-indigo-900 border border-indigo-200 cursor-pointer transition-colors"
                          title="Load this query into the Query Input above"
                        >
                          <span>Load</span>
                          <ArrowUp className="w-3 h-3" />
                        </button>

                        {/* Load & Execute */}
                        <button
                          type="button"
                          onClick={() => handleLoadQuery(q, true)}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-bold bg-indigo-600 text-white hover:bg-indigo-700 shadow-2xs cursor-pointer transition-all"
                          title="Load and immediately execute research inquiry"
                        >
                          <span>Inquire</span>
                          <Play className="w-3 h-3 fill-current" />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* TABLE VIEW */}
          {viewMode === "table" && filteredQueries.length > 0 && (
            <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-bold uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="px-3.5 py-3">ID</th>
                    <th className="px-3.5 py-3">Theme & Concept</th>
                    <th className="px-3.5 py-3">Bilingual Research Inquiry (தமிழ் & English)</th>
                    <th className="px-3.5 py-3">Type</th>
                    <th className="px-3.5 py-3">Difficulty</th>
                    <th className="px-3.5 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-800">
                  {paginatedQueries.map((q) => {
                    const isCopied = copiedId === q.id;
                    return (
                      <tr
                        key={q.id}
                        className="hover:bg-indigo-50/40 transition-colors group"
                      >
                        <td className="px-3.5 py-3 font-mono font-bold text-indigo-700 whitespace-nowrap">
                          {q.id}
                        </td>
                        <td className="px-3.5 py-3 whitespace-nowrap">
                          <div className="font-semibold text-slate-900">{q.title}</div>
                          <div className="text-[10px] text-slate-500 font-mono">{q.theme}</div>
                        </td>
                        <td className="px-3.5 py-3 max-w-md">
                          <div className="font-medium text-slate-900 line-clamp-2">
                            {q.query}
                          </div>
                          {q.tamilQuery && (
                            <div className="tamil-font text-[11px] text-slate-500 italic line-clamp-1 mt-0.5">
                              {q.tamilQuery}
                            </div>
                          )}
                        </td>
                        <td className="px-3.5 py-3 whitespace-nowrap">
                          {getQueryTypeBadge(q.queryType)}
                        </td>
                        <td className="px-3.5 py-3 whitespace-nowrap">
                          {getDifficultyBadge(q.difficulty)}
                        </td>
                        <td className="px-3.5 py-3 text-right whitespace-nowrap">
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              type="button"
                              onClick={() => handleCopyQuery(q)}
                              className="p-1 rounded border border-slate-200 hover:bg-slate-100 text-slate-500 cursor-pointer"
                              title="Copy"
                            >
                              {isCopied ? (
                                <Check className="w-3 h-3 text-emerald-600" />
                              ) : (
                                <Copy className="w-3 h-3" />
                              )}
                            </button>
                            <button
                              type="button"
                              onClick={() => handleLoadQuery(q, false)}
                              className="px-2 py-1 rounded text-[11px] font-semibold bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 cursor-pointer"
                            >
                              Load
                            </button>
                            <button
                              type="button"
                              onClick={() => handleLoadQuery(q, true)}
                              className="px-2 py-1 rounded text-[11px] font-bold bg-indigo-600 text-white hover:bg-indigo-700 cursor-pointer"
                            >
                              Inquire
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination Toolbar */}
          {filteredQueries.length > 0 && (
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-slate-200">
              {/* Page size selector */}
              <div className="flex items-center gap-2 text-xs text-slate-600">
                <span>Per page:</span>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="bg-white border border-slate-200 rounded-lg px-2 py-1 text-xs font-semibold text-slate-800 outline-none focus:border-indigo-500 cursor-pointer"
                >
                  <option value={12}>12</option>
                  <option value={24}>24</option>
                  <option value={48}>48</option>
                  <option value={96}>96</option>
                </select>
                <span className="text-slate-400">|</span>
                <span>
                  Page <strong>{safeCurrentPage}</strong> of <strong>{totalPages}</strong>
                </span>
              </div>

              {/* Page Buttons */}
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                  disabled={safeCurrentPage <= 1}
                  className="px-2.5 py-1.5 rounded-lg border border-slate-200 text-xs font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer inline-flex items-center gap-1"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  <span>Prev</span>
                </button>

                {/* Numbered Jump Buttons */}
                <div className="flex items-center gap-1 px-1">
                  {Array.from({ length: Math.min(totalPages, 7) }, (_, idx) => {
                    let pageNum;
                    if (totalPages <= 7) {
                      pageNum = idx + 1;
                    } else if (safeCurrentPage <= 4) {
                      pageNum = idx + 1;
                    } else if (safeCurrentPage >= totalPages - 3) {
                      pageNum = totalPages - 6 + idx;
                    } else {
                      pageNum = safeCurrentPage - 3 + idx;
                    }

                    const isCurrent = pageNum === safeCurrentPage;
                    return (
                      <button
                        key={pageNum}
                        type="button"
                        onClick={() => setCurrentPage(pageNum)}
                        className={`w-7 h-7 rounded-lg text-xs font-semibold flex items-center justify-center cursor-pointer transition-colors ${
                          isCurrent
                            ? "bg-indigo-600 text-white shadow-2xs"
                            : "hover:bg-slate-100 text-slate-700"
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  })}
                </div>

                <button
                  type="button"
                  onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                  disabled={safeCurrentPage >= totalPages}
                  className="px-2.5 py-1.5 rounded-lg border border-slate-200 text-xs font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer inline-flex items-center gap-1"
                >
                  <span>Next</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
