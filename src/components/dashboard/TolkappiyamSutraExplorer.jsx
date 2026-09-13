import { useState, useEffect, useCallback, useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Library,
  Search,
  Sparkles,
  ChevronRight,
  ChevronLeft,
  X,
  RotateCcw,
  Loader2,
  AlertCircle,
  Network,
  Eye,
  CheckCircle2,
  ExternalLink,
  ChevronUp,
} from 'lucide-react';
import Card from '../common/Card';
import Badge from '../common/Badge';
import Button from '../common/Button';
import { useReasoner } from '../../context/ReasonerContext';
import {
  corpusApi,
  searchPassages,
} from '../../services/apiClient';
import {
  SEARCH_MODES,
  getSearchModeConfig,
} from '../../services/searchService';

export default function TolkappiyamSutraExplorer({ onSelectSutraForQuery }) {
  const location = useLocation();
  const navigate = useNavigate();
  const {
    setSelectedGraphNodeId,
    selectPassageForEvidence,
    selectedEvidenceId,
  } = useReasoner();

  // ---------------------------------------------------------------------------
  // 1. Hierarchy State: L0 (Literature) -> L1 (Work) -> L2 (Section) -> L3 (Passage)
  // ---------------------------------------------------------------------------
  const [literature, setLiterature] = useState(null);

  const [works, setWorks] = useState([]);
  const [selectedWorkId, setSelectedWorkId] = useState('tolkappiyam');

  const [sections, setSections] = useState([]);
  const [selectedSectionId, setSelectedSectionId] = useState(
    location.state?.sectionId || 'porul'
  );
  const [selectedChapter, setSelectedChapter] = useState('all');
  const [selectedTinai, setSelectedTinai] = useState('all');

  // ---------------------------------------------------------------------------
  // 2. Query & Search Mode State
  // ---------------------------------------------------------------------------
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [searchMode, setSearchMode] = useState('hybrid');
  const [isAdvancedSearch, setIsAdvancedSearch] = useState(false);

  // ---------------------------------------------------------------------------
  // 3. Paginated Passages State (L3)
  // ---------------------------------------------------------------------------
  const [passages, setPassages] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(1);
  const [totalPassages, setTotalPassages] = useState(0);
  const [isLoadingPassages, setIsLoadingPassages] = useState(false);
  const [passageError, setPassageError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  // Expanded evidence inspection state for individual passages
  const [expandedEvidenceId, setExpandedEvidenceId] = useState(null);

  // ---------------------------------------------------------------------------
  // ---------------------------------------------------------------------------
  // 4. Initial Load: Literature (L0), Works (L1), and Sections (L2)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    let isSubscribed = true;
    const controller = new AbortController();

    Promise.allSettled([
      corpusApi.getLiterature({ signal: controller.signal }),
      corpusApi.getWorks({ signal: controller.signal }),
      corpusApi.getSections({ signal: controller.signal }),
    ]).then(([litRes, worksRes, secRes]) => {
      if (!isSubscribed) return;

      if (litRes.status === 'fulfilled' && litRes.value?.data) {
        setLiterature(litRes.value.data);
      }

      if (worksRes.status === 'fulfilled' && worksRes.value?.data) {
        const worksList = Array.isArray(worksRes.value.data)
          ? worksRes.value.data
          : [worksRes.value.data];
        setWorks(worksList);
      }

      if (secRes.status === 'fulfilled' && secRes.value?.data) {
        setSections(secRes.value.data || []);
      }
    });

    return () => {
      isSubscribed = false;
      controller.abort();
    };
  }, [reloadKey]);

  // Sync sectionId from router state if navigation triggered from overview cards
  useEffect(() => {
    if (location.state?.sectionId) {
      queueMicrotask(() => {
        setSelectedSectionId(location.state.sectionId);
        setCurrentPage(1);
      });
    }
  }, [location.state?.sectionId]);

  // Debounce search query
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedQuery(searchQuery.trim());
      setCurrentPage(1);
    }, 350);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Map selectedSectionId to backend section filter name
  const canonicalSectionFilter = useMemo(() => {
    if (!selectedSectionId || selectedSectionId === 'all') return null;
    if (selectedSectionId === 'porul' || selectedSectionId.includes('porul')) {
      return 'Poruḷatikāram';
    }
    if (selectedSectionId === 'col' || selectedSectionId.includes('col')) {
      return 'Collatikāram';
    }
    if (selectedSectionId === 'eluttu' || selectedSectionId.includes('eluttu')) {
      return 'Eḻuttatikāram';
    }
    return selectedSectionId;
  }, [selectedSectionId]);

  // Available chapters/iyals for the currently selected section
  const availableChapters = useMemo(() => {
    if (!selectedSectionId || selectedSectionId === 'all') {
      return sections;
    }
    const secLower = selectedSectionId.toLowerCase();
    return sections.filter((s) => {
      const parent = (s.parent_atikaram || s.parent_book_id || '').toLowerCase();
      return (
        parent.includes(secLower) ||
        (secLower.includes('porul') && parent.includes('poru')) ||
        (secLower.includes('col') && parent.includes('col')) ||
        (secLower.includes('eluttu') && parent.includes('eluttu'))
      );
    });
  }, [sections, selectedSectionId]);

  // ---------------------------------------------------------------------------
  // 5. Fetch Canonical Passages (Controlled Pagination & Filter)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    let isSubscribed = true;
    const controller = new AbortController();

    queueMicrotask(() => {
      if (!isSubscribed) return;
      setIsLoadingPassages(true);
      setPassageError(null);
    });

    // If debounced search query is active and user chose semantic/hybrid search
    if (debouncedQuery && isAdvancedSearch) {
      searchPassages({
        query: debouncedQuery,
        mode: searchMode,
        section: canonicalSectionFilter,
        chapter: selectedChapter !== 'all' ? selectedChapter : null,
        tinai: selectedTinai !== 'all' ? selectedTinai : null,
        topK: pageSize * currentPage,
        pageSize: pageSize,
        includeGraph: true,
        signal: controller.signal,
      })
        .then((res) => {
          if (!isSubscribed) return;
          const ranked = res?.data?.ranked_results || [];
          const total = res?.data?.total_results ?? ranked.length;
          // Normalize ranked items to standard passage format
          const mapped = ranked.map((item) => {
            const meta = item.source_metadata || {};
            return {
              id: item.passage_id || `passage-${item.rank}`,
              passage_id: item.passage_id,
              sutra_number: meta.sutra_number,
              tamil_text: item.text,
              english_translation: meta.english_translation || meta.translation || '',
              transliteration: meta.transliteration || '',
              atikaram: meta.section || 'Poruḷatikāram',
              iyal: meta.chapter || 'Akattiṇaiyiyal',
              tinai: meta.tinai || 'General',
              entities: item.graph_context?.entities || meta.entities || [],
              concepts: item.graph_context?.concepts || meta.concepts || [],
              category: meta.category || 'Semantic Search Result',
              relevance_scores: item.relevance_scores,
              rank: item.rank,
            };
          });
          setPassages(mapped);
          setTotalPassages(total);
          setTotalPages(Math.max(1, Math.ceil(total / pageSize)));
        })
        .catch((err) => {
          if (!isSubscribed || err.name === 'AbortError') return;
          console.error('[TolkappiyamSutraExplorer] Search error:', err);
          setPassageError(err.message || 'Failed to search corpus');
          setPassages([]);
        })
        .finally(() => {
          if (isSubscribed) setIsLoadingPassages(false);
        });

      return () => {
        isSubscribed = false;
        controller.abort();
      };
    }

    // Default canonical corpus passages browsing via corpusApi.getPassages
    corpusApi
      .getPassages({
        work: selectedWorkId !== 'all' ? selectedWorkId : null,
        section: canonicalSectionFilter,
        chapter: selectedChapter !== 'all' ? selectedChapter : null,
        tinai: selectedTinai !== 'all' ? selectedTinai : null,
        query: debouncedQuery || null,
        page: currentPage,
        pageSize: pageSize,
        signal: controller.signal,
      })
      .then((res) => {
        if (!isSubscribed) return;
        const items = res?.data || [];
        const meta = res?.meta || {};
        const total = meta.total ?? items.length;
        const tPages = meta.total_pages ?? meta.totalPages ?? Math.max(1, Math.ceil(total / pageSize));

        setPassages(items);
        setTotalPassages(total);
        setTotalPages(tPages);
      })
      .catch((err) => {
        if (!isSubscribed || err.name === 'AbortError') return;
        console.error('[TolkappiyamSutraExplorer] Passages fetch error:', err);
        setPassageError(err.message || 'Failed to load canonical passages from backend service');
        setPassages([]);
      })
      .finally(() => {
        if (isSubscribed) setIsLoadingPassages(false);
      });

    return () => {
      isSubscribed = false;
      controller.abort();
    };
  }, [
    selectedWorkId,
    canonicalSectionFilter,
    selectedChapter,
    selectedTinai,
    debouncedQuery,
    isAdvancedSearch,
    searchMode,
    currentPage,
    pageSize,
    reloadKey,
  ]);

  // Handlers
  const handleSectionSelect = (secId) => {
    setSelectedSectionId(secId);
    setSelectedChapter('all');
    setCurrentPage(1);
  };

  const handleChapterSelect = (chName) => {
    setSelectedChapter(chName);
    setCurrentPage(1);
  };

  const handleTinaiSelect = (tinai) => {
    setSelectedTinai(tinai);
    setCurrentPage(1);
  };

  const handleClearFilters = () => {
    setSelectedSectionId('porul');
    setSelectedChapter('all');
    setSelectedTinai('all');
    setSearchQuery('');
    setDebouncedQuery('');
    setCurrentPage(1);
    setIsAdvancedSearch(false);
  };

  // Inspect passage in evidence panel & focus graph node
  const handleInspectPassageEvidence = useCallback(
    (passage) => {
      const pid = passage.id || passage.passage_id;
      setExpandedEvidenceId((prev) => (prev === pid ? null : pid));
      if (selectPassageForEvidence) {
        selectPassageForEvidence(passage);
      } else if (setSelectedGraphNodeId) {
        setSelectedGraphNodeId(pid);
      }
    },
    [selectPassageForEvidence, setSelectedGraphNodeId]
  );

  // Focus node in Cytoscape Knowledge Graph Viewer and navigate
  const handleFocusGraphNode = useCallback(
    (passageId) => {
      if (setSelectedGraphNodeId) {
        setSelectedGraphNodeId(passageId);
      }
      navigate('/knowledge-graph');
    },
    [setSelectedGraphNodeId, navigate]
  );

  // Active work item details
  const activeWork =
    works.find((w) => w.id === selectedWorkId) ||
    works[0] || {
      name: 'Tolkāppiyam (தொல்காப்பியம்)',
      author: 'Tolkāppiyar (தொல்காப்பியர்)',
      sections_count: 3,
      canonical_sutras_count: 1610,
    };

  const activeModeConfig = getSearchModeConfig(searchMode);

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* ========================================================================= */}
      {/* 1. HIERARCHY BREADCRUMB & LEVEL 0 (LITERATURE) BANNER                     */}
      {/* ========================================================================= */}
      <div className="p-5 sm:p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-[#0d1424] to-purple-950 text-white border border-purple-500/30 shadow-md">
        {/* Breadcrumb Trail */}
        <div className="flex items-center gap-1.5 text-xs text-purple-300/80 mb-3 flex-wrap">
          <button
            type="button"
            onClick={handleClearFilters}
            className="hover:text-white font-medium transition-colors flex items-center gap-1 cursor-pointer"
          >
            <Library className="w-3.5 h-3.5 text-purple-400" />
            <span>Literature (L0)</span>
          </button>
          <ChevronRight className="w-3.5 h-3.5 text-slate-500" />

          <button
            type="button"
            onClick={() => {
              setSelectedWorkId(activeWork.id || 'tolkappiyam');
              setSelectedSectionId('all');
              setSelectedChapter('all');
            }}
            className="hover:text-white font-medium transition-colors cursor-pointer text-purple-200"
          >
            {activeWork.name || 'Tolkāppiyam'} (L1)
          </button>
          <ChevronRight className="w-3.5 h-3.5 text-slate-500" />

          <span className="font-semibold text-white">
            {selectedSectionId === 'all'
              ? 'All Sections'
              : canonicalSectionFilter || selectedSectionId}{' '}
            (L2)
          </span>

          {selectedChapter !== 'all' && (
            <>
              <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
              <span className="font-semibold text-purple-300">
                {selectedChapter}
              </span>
            </>
          )}
        </div>

        {/* L0 & L1 Header Content */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1.5 max-w-3xl">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xl sm:text-2xl font-bold font-serif tracking-wide text-purple-200">
                {literature?.title || 'Classical Tamil Literature (சங்க இலக்கியமும் தொல்காப்பியமும்)'}
              </span>
              <Badge variant="purpleDark" size="sm">
                Hierarchy L0 → L3
              </Badge>
              <Badge variant="emerald" size="sm" dot>
                Neo4j & Dataset Connected
              </Badge>
            </div>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
              {literature?.description ||
                'Canonical corpus of Classical Tamil grammar, poetics, semiotics, and prosody.'}
            </p>
            <div className="flex items-center gap-4 text-xs text-purple-300/80 pt-1 flex-wrap">
              <span>
                <strong>Language:</strong> {literature?.language || 'Classical Tamil (தமிழ்)'}
              </span>
              <span>•</span>
              <span>
                <strong>Period:</strong> {literature?.period || 'Sangam Era (கி.மு. 300 - கி.பி. 300)'}
              </span>
              <span>•</span>
              <span>
                <strong>Primary Author:</strong> {activeWork.author || 'Tolkāppiyar'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <div className="p-3 rounded-xl bg-purple-900/50 border border-purple-500/40 text-center">
              <span className="text-[11px] text-purple-300 block">Total Canonical Sūtras</span>
              <span className="font-mono text-xl font-extrabold text-white">
                {activeWork.canonical_sutras_count || 1610}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-slate-800/80 border border-slate-700 text-center">
              <span className="text-[11px] text-slate-400 block">Books (அதிகாரம்)</span>
              <span className="font-mono text-xl font-extrabold text-white">3</span>
            </div>
          </div>
        </div>

        {/* ========================================================================= */}
        {/* 2. LEVEL 2 (L2): THREE CANONICAL ATIKĀRAM CARDS (CANONICAL BOOKS)         */}
        {/* ========================================================================= */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-5 pt-4 border-t border-slate-800">
          {/* Eḻuttatikāram */}
          <button
            type="button"
            onClick={() => handleSectionSelect('eluttu')}
            className={`text-left p-4 rounded-xl border transition-all cursor-pointer ${
              selectedSectionId === 'eluttu'
                ? 'bg-purple-950/90 border-purple-400 text-white shadow-md ring-2 ring-purple-500/30'
                : 'bg-slate-900/60 border-slate-800 text-slate-300 hover:bg-slate-800/80 hover:text-white'
            }`}
          >
            <div className="flex items-center justify-between gap-2 mb-1.5">
              <span className="font-bold text-sm text-purple-200">
                Eḻuttatikāram (எழுத்து)
              </span>
              <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-purple-900/60 text-purple-300">
                483 Sūtras
              </span>
            </div>
            <p className="text-xs text-slate-400 line-clamp-2 mt-1 leading-relaxed">
              Phonetics, Orthography, Morphophonemics & Metrical Acoustics
            </p>
            <div className="mt-3 text-xs text-purple-300/90 flex items-center gap-1 font-mono">
              <span>9 Chapters (இயல்)</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </div>
          </button>

          {/* Collatikāram */}
          <button
            type="button"
            onClick={() => handleSectionSelect('col')}
            className={`text-left p-4 rounded-xl border transition-all cursor-pointer ${
              selectedSectionId === 'col'
                ? 'bg-purple-950/90 border-purple-400 text-white shadow-md ring-2 ring-purple-500/30'
                : 'bg-slate-900/60 border-slate-800 text-slate-300 hover:bg-slate-800/80 hover:text-white'
            }`}
          >
            <div className="flex items-center justify-between gap-2 mb-1.5">
              <span className="font-bold text-sm text-purple-200">
                Collatikāram (சொல்)
              </span>
              <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-purple-900/60 text-purple-300">
                463 Sūtras
              </span>
            </div>
            <p className="text-xs text-slate-400 line-clamp-2 mt-1 leading-relaxed">
              Morphology, Syntax, Semantics, Nominal/Verbal Classes & Semantic Cases
            </p>
            <div className="mt-3 text-xs text-purple-300/90 flex items-center gap-1 font-mono">
              <span>9 Chapters (இயல்)</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </div>
          </button>

          {/* Poruḷatikāram */}
          <button
            type="button"
            onClick={() => handleSectionSelect('porul')}
            className={`text-left p-4 rounded-xl border transition-all cursor-pointer ${
              selectedSectionId === 'porul'
                ? 'bg-purple-950/90 border-purple-400 text-white shadow-md ring-2 ring-purple-500/30'
                : 'bg-slate-900/60 border-slate-800 text-slate-300 hover:bg-slate-800/80 hover:text-white'
            }`}
          >
            <div className="flex items-center justify-between gap-2 mb-1.5">
              <span className="font-bold text-sm text-purple-200">
                Poruḷatikāram (பொருள்)
              </span>
              <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-purple-900/60 text-purple-300">
                664 Sūtras
              </span>
            </div>
            <p className="text-xs text-slate-400 line-clamp-2 mt-1 leading-relaxed">
              Poetics, Epistemology, Tiṇai Ecology, Affective Psychology & Semiotics
            </p>
            <div className="mt-3 text-xs text-purple-300/90 flex items-center gap-1 font-mono">
              <span>9 Chapters • Active in KG</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </div>
          </button>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 3. LEVEL 3 (L3): PASSAGE BROWSER, CONTROLS, SEARCH & PAGINATION           */}
      {/* ========================================================================= */}
      <Card
        title={
          debouncedQuery
            ? `Passages matching: "${debouncedQuery}"`
            : selectedSectionId === 'all'
            ? 'Canonical Corpus Browser (All Sections)'
            : `Canonical Sūtras: ${canonicalSectionFilter || selectedSectionId}`
        }
        subtitle={
          debouncedQuery
            ? `Retrieved ${totalPassages} passage(s) with filter constraints`
            : `Showing page ${currentPage} of ${totalPages} (${totalPassages} passages total)`
        }
        icon={Library}
        accent="purple"
        actions={
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 w-full sm:w-auto">
            {/* Search Input with Clear Button */}
            <div className="relative w-full sm:w-64 lg:w-72">
              {isLoadingPassages ? (
                <Loader2 className="w-3.5 h-3.5 text-purple-600 absolute left-2.5 top-1/2 -translate-y-1/2 animate-spin pointer-events-none" />
              ) : (
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              )}

              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search: முதல்கரு, அச்சம், mutal..."
                className="w-full text-xs pl-8 pr-8 py-1.5 rounded-lg border border-slate-300 bg-white focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 outline-none transition-all placeholder:text-slate-400 font-medium"
              />

              {searchQuery && (
                <button
                  type="button"
                  onClick={() => {
                    setSearchQuery('');
                    setDebouncedQuery('');
                  }}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 p-0.5 rounded cursor-pointer"
                  title="Clear search"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Advanced Search Toggle Pill */}
            <button
              type="button"
              onClick={() => setIsAdvancedSearch(!isAdvancedSearch)}
              className={`px-2.5 py-1.5 text-xs font-semibold rounded-lg border transition-all flex items-center gap-1.5 cursor-pointer shrink-0 ${
                isAdvancedSearch
                  ? 'bg-purple-100 text-purple-900 border-purple-300 shadow-2xs font-bold'
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5 text-purple-600" />
              <span>Multi-Mode RAG</span>
            </button>
          </div>
        }
      >
        <div className="space-y-4">
          {/* Advanced Search Options Bar (Optional mode toggle) */}
          {isAdvancedSearch && (
            <div className="p-3 rounded-xl bg-purple-50/80 border border-purple-200/80 flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-semibold text-purple-950">Search Mode:</span>
                <div className="flex items-center p-0.5 bg-white rounded-md border border-purple-200">
                  {SEARCH_MODES.map((m) => (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => setSearchMode(m.id)}
                      title={m.desc}
                      className={`px-2 py-0.5 text-xs font-semibold rounded transition-all cursor-pointer ${
                        searchMode === m.id
                          ? 'bg-purple-700 text-white font-bold'
                          : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                      }`}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>
                <span className="text-purple-700 text-[11px]">
                  • {activeModeConfig.desc}
                </span>
              </div>
            </div>
          )}

          {/* Secondary Filters Bar: Chapter (Iyal) Pills & Tiṇai Selector */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-1 border-b border-slate-200/80 pb-3">
            {/* Chapters / Iyals for selected section */}
            <div className="flex items-center gap-1.5 flex-wrap min-w-0">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider shrink-0">
                Chapter (இயல்):
              </span>
              <button
                type="button"
                onClick={() => handleChapterSelect('all')}
                className={`px-2 py-1 rounded-md text-xs font-medium cursor-pointer transition-all ${
                  selectedChapter === 'all'
                    ? 'bg-purple-800 text-white shadow-2xs font-semibold'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                All Chapters
              </button>
              {availableChapters.map((ch) => {
                const isSelected = selectedChapter === ch.name;
                return (
                  <button
                    key={ch.id || ch.name}
                    type="button"
                    onClick={() => handleChapterSelect(ch.name)}
                    className={`px-2 py-1 rounded-md text-xs font-medium cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-purple-800 text-white shadow-2xs font-semibold'
                        : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                    }`}
                  >
                    {ch.name}
                    {ch.sutras_count > 0 && (
                      <span className="ml-1 text-[10px] opacity-75 font-mono">
                        ({ch.sutras_count})
                      </span>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Tiṇai Selector Dropdown */}
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                Tiṇai:
              </span>
              <select
                value={selectedTinai}
                onChange={(e) => handleTinaiSelect(e.target.value)}
                className="text-xs py-1 px-2.5 rounded-lg border border-slate-300 bg-white text-slate-700 focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500 outline-none cursor-pointer"
              >
                <option value="all">All Tiṇais</option>
                <option value="General">General (பொது)</option>
                <option value="Kuṟiñci">Kuṟiñci (குறிஞ்சி - Mountain)</option>
                <option value="Mullai">Mullai (முல்லை - Pastoral)</option>
                <option value="Marutam">Marutam (மருதம் - Agricultural)</option>
                <option value="Neytal">Neytal (நெய்தல் - Coastal)</option>
                <option value="Pālai">Pālai (பாலை - Arid)</option>
              </select>

              {(selectedSectionId !== 'all' ||
                selectedChapter !== 'all' ||
                selectedTinai !== 'all' ||
                debouncedQuery) && (
                <Button
                  variant="outline"
                  size="xs"
                  onClick={handleClearFilters}
                  icon={RotateCcw}
                  className="text-slate-600 hover:text-slate-900"
                >
                  Reset
                </Button>
              )}
            </div>
          </div>

          {/* Error Banner */}
          {passageError && (
            <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 flex items-start justify-between gap-3 text-xs animate-in fade-in">
              <div className="flex items-start gap-2.5">
                <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold">Corpus Service Notice</div>
                  <p className="text-amber-800 mt-0.5">{passageError}</p>
                </div>
              </div>
              <Button
                variant="outline"
                size="xs"
                onClick={() => setReloadKey((k) => k + 1)}
                className="shrink-0 text-amber-900 border-amber-300 bg-white hover:bg-amber-100"
              >
                Retry
              </Button>
            </div>
          )}

          {/* Loading Skeletons */}
          {isLoadingPassages && (
            <div className="space-y-3 pt-2 animate-pulse">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="h-5 bg-slate-200 rounded w-48" />
                    <div className="h-5 bg-slate-200 rounded w-24" />
                  </div>
                  <div className="h-16 bg-slate-100 rounded-lg border border-slate-200" />
                  <div className="h-4 bg-slate-200 rounded w-2/3" />
                </div>
              ))}
            </div>
          )}

          {/* Passages List */}
          {!isLoadingPassages && passages.length > 0 && (
            <div className="space-y-3.5 pt-1">
              {passages.map((item) => {
                const passageId = item.id || item.passage_id;
                const sutraNum = item.sutra_number || item.sutraNumber;
                const atikaram = item.atikaram || item.section || 'Poruḷatikāram';
                const chapter = item.iyal || item.chapter || 'Akattiṇaiyiyal';
                const verseText = item.tamil_text || item.text || '';
                const transliteration = item.transliteration || '';
                const translation = item.english_translation || item.translation || '';
                const tinai = item.tinai || 'General';
                const entities = Array.isArray(item.entities) ? item.entities : [];
                const concepts = Array.isArray(item.concepts) ? item.concepts : [];
                const triples = Array.isArray(item.triples) ? item.triples : [];
                const nyaya = item.nyaya_mapping || null;
                const scores = item.relevance_scores || null;

                const isExpanded = expandedEvidenceId === passageId;
                const isSelectedEvidence = selectedEvidenceId === passageId;

                return (
                  <div
                    key={passageId}
                    className={`p-4 rounded-xl border transition-all space-y-3 shadow-2xs ${
                      isSelectedEvidence
                        ? 'bg-purple-50/50 border-purple-400 ring-2 ring-purple-500/20'
                        : 'bg-slate-50/80 border-slate-200/90 hover:border-purple-300 hover:bg-white'
                    }`}
                  >
                    {/* Header Row: Identifiers & Badges */}
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2 flex-wrap min-w-0">
                        {/* Stable Sūtra Number / ID */}
                        <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-purple-100 text-purple-800 border border-purple-200">
                          {sutraNum ? `Sūtra ${sutraNum}` : passageId}
                        </span>

                        <span className="font-mono text-[11px] text-slate-500 bg-white px-1.5 py-0.5 rounded border border-slate-200">
                          {passageId}
                        </span>

                        {/* Atikāram & Chapter */}
                        <span className="text-xs font-semibold text-slate-800">
                          {atikaram} • {chapter}
                        </span>

                        {/* Tiṇai Badge */}
                        {tinai && tinai !== 'General' && (
                          <Badge variant="emerald" size="xs">
                            {tinai}
                          </Badge>
                        )}

                        {/* Relevance match if from search */}
                        {scores && (
                          <span className="font-mono text-[11px] font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                            Match:{' '}
                            {Math.round(
                              (scores.combined_score ?? scores.rerank_score ?? 0.8) * 100
                            )}
                            %
                          </span>
                        )}
                      </div>

                      {/* Top Actions on Card */}
                      <div className="flex items-center gap-1.5 shrink-0 flex-wrap">
                        {/* 1. Inspect Evidence Context */}
                        <Button
                          variant={isExpanded ? 'secondary' : 'outline'}
                          size="xs"
                          onClick={() => handleInspectPassageEvidence(item)}
                          icon={isExpanded ? ChevronUp : Eye}
                          className="text-slate-700 hover:text-purple-800"
                          title="View evidence context, citations, and metadata"
                        >
                          {isExpanded ? 'Hide Evidence' : 'Inspect Evidence'}
                        </Button>

                        {/* 2. Focus in Knowledge Graph Viewer */}
                        <Button
                          variant="outline"
                          size="xs"
                          onClick={() => handleFocusGraphNode(passageId)}
                          icon={Network}
                          className="text-purple-700 hover:bg-purple-50"
                          title="Open Cytoscape Knowledge Graph and highlight node"
                        >
                          View in Graph
                        </Button>

                        {/* 3. Send to Query Center */}
                        {onSelectSutraForQuery && verseText && (
                          <Button
                            variant="primary"
                            size="xs"
                            onClick={() => onSelectSutraForQuery(verseText)}
                            icon={Sparkles}
                          >
                            Query Sūtra
                          </Button>
                        )}
                      </div>
                    </div>

                    {/* Original Tamil Verse Box */}
                    {verseText && (
                      <div className="bg-white p-3.5 rounded-lg border border-slate-200 shadow-inner">
                        <p className="tamil-font text-sm sm:text-base font-semibold text-slate-900 whitespace-pre-line leading-relaxed">
                          {verseText}
                        </p>
                      </div>
                    )}

                    {/* Transliteration (Romanized) */}
                    {transliteration && (
                      <div className="text-xs text-slate-500 font-serif italic pl-1 leading-relaxed">
                        {transliteration}
                      </div>
                    )}

                    {/* English Translation */}
                    {translation && (
                      <div className="text-xs text-slate-700 leading-relaxed bg-white/80 p-2.5 rounded-md border border-slate-200/80">
                        <span className="font-semibold text-slate-800">Translation: </span>
                        "{translation}"
                      </div>
                    )}

                    {/* Entities & Concepts Tags */}
                    {(entities.length > 0 || concepts.length > 0) && (
                      <div className="flex items-center gap-1.5 flex-wrap pt-1 text-xs">
                        <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                          KG Entities:
                        </span>
                        {entities.map((ent, idx) => (
                          <button
                            key={idx}
                            type="button"
                            onClick={() => handleFocusGraphNode(ent)}
                            className="px-2 py-0.5 rounded bg-purple-50 hover:bg-purple-100 text-purple-700 border border-purple-200 text-[11px] font-medium transition-colors cursor-pointer"
                            title={`Focus "${ent}" in Knowledge Graph`}
                          >
                            {ent}
                          </button>
                        ))}
                        {concepts.map((con, idx) => (
                          <button
                            key={idx}
                            type="button"
                            onClick={() => handleFocusGraphNode(con)}
                            className="px-2 py-0.5 rounded bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 text-[11px] font-medium transition-colors cursor-pointer"
                            title={`Focus concept "${con}" in Knowledge Graph`}
                          >
                            {con}
                          </button>
                        ))}
                      </div>
                    )}

                    {/* ========================================================================= */}
                    {/* EXPANDABLE EVIDENCE CONTEXT DRAWER                                        */}
                    {/* ========================================================================= */}
                    {isExpanded && (
                      <div className="mt-3 p-4 rounded-xl bg-purple-950/5 border border-purple-300/80 space-y-3 text-xs animate-in fade-in">
                        <div className="flex items-center justify-between pb-2 border-b border-purple-200/70">
                          <div className="flex items-center gap-2">
                            <CheckCircle2 className="w-4 h-4 text-purple-700" />
                            <span className="font-bold text-purple-950">
                              Evidence Context & Epistemic Provenance
                            </span>
                          </div>
                          <Badge variant="purple" size="xs">
                            Loaded into Evidence Pipeline
                          </Badge>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px]">
                          <div>
                            <span className="font-semibold text-slate-700 block">
                              Source Treatise & Citation:
                            </span>
                            <span className="text-slate-800 font-mono">
                              {item.work || 'Tolkāppiyam'} • {atikaram} • {chapter} (Sūtra {sutraNum || 'N/A'})
                            </span>
                          </div>
                          <div>
                            <span className="font-semibold text-slate-700 block">
                              Deterministic Passage ID:
                            </span>
                            <span className="font-mono text-purple-800 font-bold">
                              {passageId}
                            </span>
                          </div>
                        </div>

                        {/* Nyāya Inference Grounding */}
                        {nyaya && (
                          <div className="p-2.5 rounded-lg bg-white border border-purple-200 space-y-1">
                            <div className="font-bold text-purple-900 flex items-center justify-between">
                              <span>Nyāya Pramāṇa Grounding:</span>
                              <Badge variant="purple" size="xs">
                                {nyaya.pramana || 'Śabda Pramāṇa'}
                              </Badge>
                            </div>
                            {nyaya.member && (
                              <div className="text-slate-600">
                                <strong>Syllogistic Member:</strong> {nyaya.member}
                              </div>
                            )}
                            {nyaya.axiom && (
                              <div className="text-slate-600 font-mono text-[10px]">
                                <strong>Invariant Axiom:</strong> {nyaya.axiom}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Semantic Triples */}
                        {triples.length > 0 && (
                          <div className="space-y-1">
                            <span className="font-semibold text-slate-700 block">
                              Extracted Knowledge Graph Triples ({triples.length}):
                            </span>
                            <div className="space-y-1 max-h-36 overflow-y-auto pr-1">
                              {triples.map((t, tIdx) => (
                                <div
                                  key={tIdx}
                                  className="p-1.5 rounded bg-white border border-slate-200 font-mono text-[10px] flex items-center gap-1.5 text-slate-800"
                                >
                                  <span className="font-bold text-purple-700">
                                    ({t.subject})
                                  </span>
                                  <span className="text-slate-500">
                                    --[{t.predicate}]--&gt;
                                  </span>
                                  <span className="font-bold text-blue-700">
                                    ({t.object})
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        <div className="pt-2 flex items-center justify-between border-t border-purple-200/60">
                          <Button
                            variant="secondary"
                            size="xs"
                            onClick={() => navigate('/evidence')}
                            icon={ExternalLink}
                          >
                            Open Full Evidence Panel
                          </Button>
                          <span className="text-[11px] text-purple-700">
                            Synchronized with Cytoscape ID: {passageId}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Empty Passages State */}
          {!isLoadingPassages && passages.length === 0 && !passageError && (
            <div className="text-center py-12 px-4 rounded-xl bg-slate-50/70 border border-slate-200 space-y-3 animate-in fade-in">
              <div className="w-10 h-10 rounded-full bg-purple-100 text-purple-600 flex items-center justify-center mx-auto">
                <Search className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-800">
                  No canonical passages found
                </h4>
                <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                  No passages in{' '}
                  <span className="font-semibold text-slate-700">
                    {selectedSectionId === 'all'
                      ? 'the selected corpus'
                      : canonicalSectionFilter || selectedSectionId}
                  </span>{' '}
                  matched the current filter or search criteria.
                </p>
              </div>
              <div className="flex items-center justify-center gap-2 pt-2">
                <Button
                  variant="outline"
                  size="xs"
                  onClick={handleClearFilters}
                  icon={RotateCcw}
                >
                  Clear Filters & Search
                </Button>
              </div>
            </div>
          )}

          {/* ========================================================================= */}
          {/* 4. CONTROLLED PAGINATION BAR                                              */}
          {/* ========================================================================= */}
          {totalPassages > 0 && (
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-slate-200 text-xs">
              {/* Left: Summary text */}
              <div className="text-slate-600">
                Showing{' '}
                <span className="font-bold text-slate-800">
                  {Math.min((currentPage - 1) * pageSize + 1, totalPassages)}–
                  {Math.min(currentPage * pageSize, totalPassages)}
                </span>{' '}
                of <span className="font-bold text-slate-800">{totalPassages}</span>{' '}
                passages
              </div>

              {/* Center/Right: Page navigation controls */}
              <div className="flex items-center gap-2">
                {/* Page Size Selector */}
                <div className="flex items-center gap-1 mr-2">
                  <span className="text-slate-500 text-[11px]">Per page:</span>
                  <select
                    value={pageSize}
                    onChange={(e) => {
                      setPageSize(Number(e.target.value));
                      setCurrentPage(1);
                    }}
                    className="py-1 px-2 rounded-md border border-slate-300 bg-white text-slate-700 focus:ring-2 focus:ring-purple-500/20 outline-none cursor-pointer text-xs"
                  >
                    <option value={5}>5</option>
                    <option value={10}>10</option>
                    <option value={20}>20</option>
                  </select>
                </div>

                {/* Previous Page Button */}
                <Button
                  variant="outline"
                  size="xs"
                  disabled={currentPage <= 1 || isLoadingPassages}
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  icon={ChevronLeft}
                >
                  Prev
                </Button>

                {/* Page Status Indicator */}
                <span className="font-mono font-medium px-2 py-1 rounded bg-slate-100 border border-slate-200 text-slate-800">
                  {currentPage} / {totalPages}
                </span>

                {/* Next Page Button */}
                <Button
                  variant="outline"
                  size="xs"
                  disabled={currentPage >= totalPages || isLoadingPassages}
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  icon={ChevronRight}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
