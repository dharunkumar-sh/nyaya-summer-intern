import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Sparkles,
  ArrowRight,
  BookOpen,
  ChevronDown,
  X,
  HelpCircle,
  Layers,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Clock,
  RefreshCw,
  Search,
} from "lucide-react";
import Badge from "../common/Badge";
import Button from "../common/Button";
import { useReasoner } from "../../context/ReasonerContext";

export default function QueryInputCard() {
  const navigate = useNavigate();
  const {
    queryText,
    setQueryText,
    queryType,
    setQueryType,
    depth,
    setDepth,
    searchMode,
    setSearchMode,
    researchExamples,
    handleSelectExample,
    isAnalyzing,
    currentWorkflowStage,
    runAnalyze,
    corpus,
    queryStatus,
    queryError,
    queryStats,
    clearQueryStatus,
  } = useReasoner();

  const [examplesOpen, setExamplesOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Close examples dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setExamplesOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const onSelectExampleClick = (ex) => {
    handleSelectExample(ex);
    setExamplesOpen(false);
  };

  const handleKeyDown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      if (!isAnalyzing && queryText.trim()) {
        runAnalyze();
      }
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-xs border-t-4 border-t-purple-600 transition-all overflow-visible h-full flex flex-col justify-between">
      {/* Header bar */}
      <div className="flex items-center justify-between px-5 sm:px-6 py-4 border-b border-slate-100 bg-slate-50/50">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-purple-100 text-purple-700 border border-purple-200/70 shadow-2xs">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm sm:text-base font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <span>QUERY INPUT</span>
              <Badge variant="purple" size="xs">
                Nyāya Formulation
              </Badge>
            </h2>
            <p className="text-xs text-slate-500 font-normal">
              Formulate or select natural-language inquiry over {corpus.name} (
              {corpus.formattedCount})
            </p>
          </div>
        </div>

        {/* Action Controls: Examples Dropdown */}
        <div className="flex items-center gap-2">
          {/* Examples Button with Dropdown */}
          <div className="relative" ref={dropdownRef}>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setExamplesOpen(!examplesOpen)}
              icon={BookOpen}
              iconRight={ChevronDown}
              className="text-xs font-semibold text-purple-900 border-purple-200 bg-purple-50/50 hover:bg-purple-100/70 hover:border-purple-300"
            >
              Examples
            </Button>

            {/* Examples Dropdown Menu */}
            {examplesOpen && (
              <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl bg-white/95 backdrop-blur-md border border-purple-200/90 shadow-2xl p-2.5 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
                <div className="flex items-center justify-between px-2.5 py-1.5 border-b border-purple-100 bg-purple-50/50 rounded-xl mb-1.5">
                  <span className="text-[11px] font-bold text-purple-900 uppercase tracking-wider flex items-center gap-1.5">
                    <BookOpen className="w-3.5 h-3.5 text-purple-600" />
                    Canonical Research Inquiries
                  </span>
                  <button
                    type="button"
                    onClick={() => setExamplesOpen(false)}
                    className="text-purple-400 hover:text-purple-700 p-1 rounded-md cursor-pointer"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="max-h-72 overflow-y-auto space-y-1.5 pr-1">
                  {(researchExamples || []).map((ex) => {
                    const corpusLabel = (
                      ex?.corpusName ||
                      corpus?.name ||
                      "Tolkāppiyam"
                    ).split(" ")[0];
                    const subtitle =
                      ex?.translation || ex?.description || ex?.title || "";
                    return (
                      <button
                        key={ex.id}
                        type="button"
                        onClick={() => onSelectExampleClick(ex)}
                        className="w-full text-left p-2.5 rounded-xl border border-purple-50 hover:border-purple-300 hover:bg-purple-50/70 transition-all text-xs group cursor-pointer"
                      >
                        <div className="flex items-center justify-between gap-1 mb-1">
                          <span className="text-[10px] font-mono text-purple-700 font-semibold bg-purple-100/70 px-1.5 py-0.5 rounded">
                            {corpusLabel}
                          </span>
                          <span className="text-[10px] text-purple-500 font-medium">
                            {ex?.queryType || "Nyāya"}
                          </span>
                        </div>
                        <p className="tamil-font font-semibold text-slate-800 group-hover:text-purple-950 text-xs sm:text-sm leading-snug">
                          {ex?.query}
                        </p>
                        {subtitle && (
                          <p className="text-[11px] text-slate-500 italic mt-0.5 line-clamp-1">
                            {subtitle}
                          </p>
                        )}
                      </button>
                    );
                  })}
                </div>

                {/* Direct link to Query Library */}
                <div className="pt-2 mt-1.5 border-t border-purple-100">
                  <button
                    type="button"
                    onClick={() => {
                      setExamplesOpen(false);
                      navigate("/query-library");
                    }}
                    className="w-full py-2 px-3 rounded-xl bg-linear-to-r from-purple-600 to-indigo-600 text-white font-semibold text-xs flex items-center justify-between hover:from-purple-700 hover:to-indigo-700 transition-all shadow-xs cursor-pointer"
                  >
                    <span className="flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-yellow-300" />
                      <span>Browse Bilingual Query Library</span>
                    </span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Card Body */}
      <div className="p-4 sm:p-5 space-y-3.5 flex-1 flex flex-col justify-between">
        {/* Live API Feedback Banners: Success, Empty, Timeout, Error */}
        {queryStatus === "success" && !isAnalyzing && (
          <div className="p-3 sm:p-3.5 rounded-xl bg-emerald-50 border border-emerald-200/90 text-emerald-900 flex items-start justify-between gap-3 animate-in fade-in duration-200">
            <div className="flex items-start gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
              <div className="space-y-1">
                <div className="text-xs font-bold flex items-center gap-2 flex-wrap">
                  <span>
                    Retrieved {queryStats?.totalResults || 0} Grounded Verses
                  </span>
                  <Badge variant="green" size="xs">
                    {queryStats?.latencyMs
                      ? `${queryStats.latencyMs}ms`
                      : "Live RAG"}
                  </Badge>
                  <span className="text-[11px] text-emerald-700 font-mono bg-emerald-100/70 px-1.5 py-0.5 rounded border border-emerald-200">
                    Mode: {searchMode.toUpperCase()}
                  </span>
                  <span className="text-[11px] text-emerald-700 font-mono">
                    Pipeline v{queryStats?.pipelineVersion || "1.0.0"}
                  </span>
                </div>
                <p className="text-[11px] text-emerald-800 leading-snug">
                  Corpus passages retrieved across 3 channels: Semantic Vector,
                  BM25 Lexical, and Multi-Hop Knowledge Graph Traversal.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={clearQueryStatus}
              className="text-emerald-500 hover:text-emerald-800 p-0.5 rounded cursor-pointer"
              title="Dismiss"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {queryStatus === "empty" && !isAnalyzing && (
          <div className="p-3 sm:p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 flex items-start justify-between gap-3 animate-in fade-in duration-200">
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
              <div className="space-y-1">
                <div className="text-xs font-bold flex items-center gap-2">
                  <span>No Grounded Evidence Found</span>
                  <Badge variant="orange" size="xs">
                    0 Results
                  </Badge>
                </div>
                <p className="text-[11px] text-amber-800 leading-relaxed">
                  No canonical Tolkāppiyam passages matched the confidence
                  threshold for this query. Try broadening keywords, adjusting
                  the depth, or choosing a canonical research question from
                  Examples.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={clearQueryStatus}
              className="text-amber-500 hover:text-amber-800 p-0.5 rounded cursor-pointer"
              title="Dismiss"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {queryStatus === "timeout" && !isAnalyzing && (
          <div className="p-3 sm:p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 flex items-start justify-between gap-3 animate-in fade-in duration-200">
            <div className="flex items-start gap-2.5">
              <Clock className="w-4 h-4 text-rose-600 mt-0.5 shrink-0" />
              <div className="space-y-1">
                <div className="text-xs font-bold flex items-center gap-2">
                  <span>Search Request Timed Out</span>
                  <Badge variant="red" size="xs">
                    Timeout (20s)
                  </Badge>
                </div>
                <p className="text-[11px] text-rose-800 leading-relaxed">
                  {queryError?.message ||
                    "The Hybrid RAG backend took longer than 20 seconds to respond. The Neo4j graph or FAISS vector index may be initializing."}
                </p>
                <div className="pt-1">
                  <button
                    type="button"
                    onClick={runAnalyze}
                    className="inline-flex items-center gap-1.5 text-xs font-bold text-rose-700 hover:text-rose-900 underline cursor-pointer"
                  >
                    <RefreshCw className="w-3 h-3" />
                    Retry Search
                  </button>
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={clearQueryStatus}
              className="text-rose-500 hover:text-rose-800 p-0.5 rounded cursor-pointer"
              title="Dismiss"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {queryStatus === "error" && !isAnalyzing && (
          <div className="p-3 sm:p-3.5 rounded-xl bg-red-50 border border-red-200 text-red-900 flex items-start justify-between gap-3 animate-in fade-in duration-200">
            <div className="flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 shrink-0" />
              <div className="space-y-1">
                <div className="text-xs font-bold flex items-center gap-2 flex-wrap">
                  <span>API Error: Retrieval Failed</span>
                  {queryError?.code && (
                    <span className="font-mono text-[10px] bg-red-100 text-red-800 px-1.5 py-0.5 rounded border border-red-200">
                      {queryError.code}
                    </span>
                  )}
                  {queryError?.status && (
                    <Badge variant="red" size="xs">
                      HTTP {queryError.status}
                    </Badge>
                  )}
                </div>
                <p className="text-[11px] text-red-800 leading-relaxed">
                  {queryError?.message ||
                    "The backend service encountered an error while processing the Hybrid RAG query."}
                </p>
                <div className="pt-1">
                  <button
                    type="button"
                    onClick={runAnalyze}
                    className="inline-flex items-center gap-1.5 text-xs font-bold text-red-700 hover:text-red-900 underline cursor-pointer"
                  >
                    <RefreshCw className="w-3 h-3" />
                    Retry Request
                  </button>
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={clearQueryStatus}
              className="text-red-500 hover:text-red-800 p-0.5 rounded cursor-pointer"
              title="Dismiss"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Large Tamil Text Area */}
        <div className="relative">
          <div className="flex items-center justify-between mb-1.5">
            <label className="text-xs font-semibold text-slate-700 uppercase tracking-wider flex items-center gap-1.5 flex-wrap">
              <span>Classical Tamil or English Research Question</span>
              <span className="text-[11px] text-purple-700 font-serif font-normal">
                (தமிழ் அல்லது ஆங்கில வினா)
              </span>
            </label>
          </div>

          <div className="relative">
            <textarea
              rows={4}
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Enter question in Classical Tamil or English (e.g., 'How does the primary ground (Mutalporuḷ) in Kuṟiñci govern emotional union?' or 'குறிஞ்சி நிலத்தின் முதற்பொருள், கருப்பொருள், உரிப்பொருள் தொடர்பு எவ்வாறு அக ஒழுக்கத்தை உணர்த்துகிறது?')..."
              className="w-full bg-slate-50/70 border border-slate-200 rounded-xl p-3.5 text-sm sm:text-base text-slate-900 placeholder:text-slate-400 leading-relaxed font-serif shadow-inner outline-none focus:bg-white focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all resize-none"
            />
          </div>
        </div>

        {/* Retrieval & Epistemic Configuration Controls */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1">
          {/* Row 1: Hybrid Search Configuration */}
          <div className="contents">
            {/* 1. Search Mode */}
            <div className="bg-purple-50/30 hover:bg-purple-50/60 p-3 rounded-2xl border border-purple-100 shadow-2xs transition-colors">
              <label className="text-[11px] font-bold text-purple-900 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                <Search className="w-3.5 h-3.5 text-purple-600" />
                Search Mode
              </label>
              <div className="relative">
                <select
                  value={searchMode}
                  onChange={(e) => setSearchMode(e.target.value)}
                  className="w-full bg-white border border-purple-200/90 hover:border-purple-400 rounded-xl px-3 py-2 text-xs font-semibold text-purple-950 shadow-2xs outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 cursor-pointer appearance-none pr-8 transition-all"
                >
                  <option
                    value="hybrid"
                    className="bg-white text-slate-800 py-1 font-medium"
                  >
                    Hybrid (Vector + BM25 + KG)
                  </option>
                  <option
                    value="semantic"
                    className="bg-white text-slate-800 py-1 font-medium"
                  >
                    Semantic (Dense Vector)
                  </option>
                  <option
                    value="keyword"
                    className="bg-white text-slate-800 py-1 font-medium"
                  >
                    Keyword (BM25 Lexical)
                  </option>
                </select>
                <ChevronDown className="w-4 h-4 text-purple-500 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>
            </div>
          </div>

          {/* Row 2: Epistemic Nyāya Configuration */}
          <div className="contents">
            {/* 1. Query Type */}
            <div className="bg-purple-50/30 hover:bg-purple-50/60 p-3 rounded-2xl border border-purple-100 shadow-2xs transition-colors">
              <label className="text-[11px] font-bold text-purple-900 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                <HelpCircle className="w-3.5 h-3.5 text-purple-600" />
                Query Type
              </label>
              <div className="relative">
                <select
                  value={queryType}
                  onChange={(e) => setQueryType(e.target.value)}
                  className="w-full bg-white border border-purple-200/90 hover:border-purple-400 rounded-xl px-3 py-2 text-xs font-semibold text-purple-950 shadow-2xs outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 cursor-pointer appearance-none pr-8 transition-all"
                >
                  <option
                    value="Why / Justification"
                    className="bg-white text-slate-800 py-1 font-medium"
                  >
                    Why / Justification (ஏது / காரணம்)
                  </option>
                  <option
                    value="What / Fact"
                    className="bg-white text-slate-800 py-1 font-medium"
                  >
                    What / Fact (பொருள் / உண்மை)
                  </option>
                  <option
                    value="How / Process"
                    className="bg-white text-slate-800 py-1 font-medium"
                  >
                    How / Process (செய்கை / முறைமை)
                  </option>
                  <option
                    value="Who / Entity"
                    className="bg-white text-slate-800 py-1 font-medium"
                  >
                    Who / Entity (பாத்திரம் / மாந்தர்)
                  </option>
                </select>
                <ChevronDown className="w-4 h-4 text-purple-500 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>
            </div>

            {/* 2. Depth (Hops) */}
            <div className="bg-purple-50/30 hover:bg-purple-50/60 p-3 rounded-2xl border border-purple-100 shadow-2xs transition-colors">
              <label className="text-[11px] font-bold text-purple-900 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-purple-600" />
                Depth (Hops)
              </label>
              <div className="relative">
                <select
                  value={depth}
                  onChange={(e) => setDepth(Number(e.target.value))}
                  className="w-full bg-white border border-purple-200/90 hover:border-purple-400 rounded-xl px-3 py-2 text-xs font-semibold text-purple-950 shadow-2xs outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 cursor-pointer appearance-none pr-8 transition-all"
                >
                  <option
                    value={1}
                    className="bg-white text-slate-800 py-1 font-medium"
                  >
                    1 Hop (Direct Textual Grounding)
                  </option>
                  <option
                    value={2}
                    className="bg-white text-slate-800 py-1 font-medium"
                  >
                    2 Hops (Relational Triples)
                  </option>
                  <option
                    value={3}
                    className="bg-white text-slate-800 py-1 font-medium"
                  >
                    3 Hops (Full Pañcāvayava Deduction)
                  </option>
                  <option
                    value={4}
                    className="bg-white text-slate-800 py-1 font-medium"
                  >
                    4 Hops (Tiṇai Ecological Chain)
                  </option>
                  <option
                    value={5}
                    className="bg-white text-slate-800 py-1 font-medium"
                  >
                    5 Hops (Deep Epistemic Synthesis)
                  </option>
                </select>
                <ChevronDown className="w-4 h-4 text-purple-500 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>
            </div>
          </div>
        </div>

        {/* Action Button & Execution Bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-slate-100">
          <div className="flex items-center gap-2 text-xs text-slate-500 flex-wrap">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>Target:</span>
            <span className="font-semibold text-purple-900 bg-purple-50 px-2 py-0.5 rounded border border-purple-200">
              {corpus.name} ({corpus.formattedCount})
            </span>
            <span className="font-mono text-[11px] text-purple-700 bg-purple-100/60 px-2 py-0.5 rounded border border-purple-200/80">
              {searchMode.toUpperCase()}
            </span>
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            {/* Prominent Purple Analyze Button */}
            <button
              type="button"
              onClick={runAnalyze}
              disabled={isAnalyzing || !queryText.trim()}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2.5 px-6 py-3 rounded-xl bg-gradient-to-r from-purple-700 via-purple-600 to-indigo-700 hover:from-purple-800 hover:via-purple-700 hover:to-indigo-800 text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all duration-200 focus:outline-none focus:ring-3 focus:ring-purple-500/30 disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
            >
              {isAnalyzing ? (
                <>
                  <svg
                    className="animate-spin h-4 w-4 text-white"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                  <span>{currentWorkflowStage.name}...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 text-purple-200" />
                  <span>Analyze</span>
                  <ArrowRight className="w-4 h-4 text-purple-200" />
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
