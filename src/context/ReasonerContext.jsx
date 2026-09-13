/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  generateGroundedAnswer,
  searchPassages,
  getGraphStatistics,
  getGraphHealth,
  getGraphElements,
  getCorpusInfo,
  validateFallacies,
  getProofTrace,
  deduceReasoning,
  getDashboardSummary,
  getSystemStatus,
} from '../services/apiClient';

/**
 * Normalizes an EvidenceItem returned from backend /api/search, /api/retrieval/hybrid-rag,
 * or /api/retrieval/answer into the standardized UI evidence format expected across the application.
 */
function mapBackendEvidenceToUI(item, index) {
  const code = `E${index + 1}`;
  const src = (item.source && typeof item.source === 'object') ? item.source : {};
  const meta = (item.source_metadata && typeof item.source_metadata === 'object')
    ? item.source_metadata
    : (src.metadata || {});

  const passageId = item.passage_id || item.passageId || (item.id && !item.id.startsWith('E') ? item.id : null);
  const work = item.work || meta.work || src.work_name || src.work || (typeof item.source === 'string' ? item.source : null);
  const section = item.section || meta.section || src.section_name || src.section || meta.atikaram || null;
  const chapter = item.chapter || meta.chapter || src.chapter_name || src.chapter || meta.iyal || null;
  const sutraNumber = item.sutra_number ?? meta.sutra_number ?? src.sutra_number ?? null;
  const tinai = item.tinai || meta.tinai || src.tinai || null;

  // Evidence type: check evidence_type, pramana, category, or nyaya_mapping
  const evidenceType =
    item.evidence_type ||
    meta.evidence_type ||
    src.evidence_type ||
    meta.category ||
    src.category ||
    item.category ||
    meta.nyaya_mapping?.pramana ||
    src.nyaya_mapping?.pramana ||
    item.nyaya_mapping?.pramana ||
    null;

  const entities = Array.isArray(item.entities) ? item.entities : (Array.isArray(meta.entities) ? meta.entities : []);
  const concepts = Array.isArray(item.concepts) ? item.concepts : (Array.isArray(meta.concepts) ? meta.concepts : []);

  // Formulate dynamic badges based on retrieval channels and tinai
  const badges = [];
  const methods = Array.isArray(item.retrieval_methods)
    ? item.retrieval_methods
    : (item.retrieval_method ? [item.retrieval_method] : []);

  if (methods.some((m) => String(m).toLowerCase().includes('semantic') || String(m).toLowerCase().includes('vector'))) {
    badges.push({ label: 'Semantic Vector', variant: 'purple' });
  }
  if (methods.some((m) => String(m).toLowerCase().includes('keyword') || String(m).toLowerCase().includes('bm25') || String(m).toLowerCase().includes('lexical'))) {
    badges.push({ label: 'BM25 Lexical', variant: 'blue' });
  }
  if (methods.some((m) => String(m).toLowerCase().includes('graph'))) {
    badges.push({ label: 'Graph Traversal', variant: 'emerald' });
  }
  if (tinai && tinai !== 'General' && tinai !== 'all' && tinai !== 'All') {
    badges.push({ label: tinai, variant: 'emerald' });
  }
  if (badges.length === 0 && methods.length > 0) {
    badges.push({ label: methods[0], variant: 'purple' });
  }

  const sutraText = sutraNumber ? `Sūtra ${sutraNumber}` : '';
  const reference = [sutraText, chapter || section].filter(Boolean).join(' • ') || passageId || code;

  // Scores resolution
  const relScores = item.relevance_scores || null;
  const score = typeof relScores?.combined_score === 'number'
    ? relScores.combined_score
    : (typeof relScores?.relevance_score === 'number'
      ? relScores.relevance_score
      : (typeof item.relevance_score === 'number'
        ? item.relevance_score
        : (typeof item.confidence === 'number' ? item.confidence : null)));

  const confidenceFormatted = score !== null ? Number(score).toFixed(2) : null;

  const scoreComponents = item.score_components || (relScores ? {
    semantic_similarity: relScores.semantic_score ?? item.semantic_score ?? score,
    bm25_score: relScores.lexical_score ?? item.lexical_score ?? 0.0,
    graph_centrality: relScores.graph_score ?? item.graph_score ?? 0.0,
    source_reliability: 1.0,
  } : null);

  const graphContext = item.graph_context || (entities.length > 0 || concepts.length > 0 ? {
    associated_entities: entities,
    concepts: concepts,
  } : null);

  const translation =
    item.translation ||
    src.translation ||
    meta.translation ||
    (typeof item.explanation === 'string' ? item.explanation : item.explanation?.summary) ||
    null;

  const rawText = item.text || item.passage_text || meta.original_text || meta.tamil_text || src.text || null;
  const sourceRef = src.source_reference || src.citation || meta.citation || (typeof item.source === 'string' ? item.source : null);
  const provenance = (Array.isArray(item.graph_path) && item.graph_path.length > 0)
    ? item.graph_path
    : (item.provenance || null);

  return {
    id: passageId || item.id || code,
    code,
    passageId,
    source: sourceRef || work || null,
    work,
    section: section ? `${section}${chapter ? ` (${chapter})` : ''}` : (chapter || null),
    rawSection: section,
    chapter,
    sutraNumber,
    tinai,
    evidenceType,
    reference,
    tamilText: rawText,
    text: rawText,
    transliteration: meta.transliteration || item.transliteration || null,
    translation,
    confidence: score,
    relevanceScore: score,
    confidenceFormatted,
    badges,
    entities,
    concepts,
    relevanceScores: relScores,
    scoreComponents,
    retrievalMethod: item.retrieval_method || methods[0] || null,
    retrievalMethods: methods,
    provenance,
    graph_path: item.graph_path || null,
    graphContext,
    reasoningStepTarget: `Rank #${item.rank || index + 1}: ${badges.map((b) => b.label).join(' + ') || 'Canonical'} Grounding`,
    pramanaType: evidenceType || (scoreComponents?.source_reliability
      ? `Pramāṇa Reliability (${Math.round(scoreComponents.source_reliability * 100)}%)`
      : null),
    attentionWeight: score !== null ? +(score * 0.35).toFixed(3) : null,
    rawItem: item,
  };
}

const ReasonerContext = createContext(null);

// Canonical 5-Stage Workflow Definition
export const REASONING_WORKFLOW_STAGES = [
  { id: 'retrieving', name: 'Retrieving Evidence', percent: 20, desc: 'Neural semantic indexing over 1,610 sūtras' },
  { id: 'building_kg', name: 'Building Knowledge Graph', percent: 45, desc: 'Extracting Tiṇai entities, deities & ecological relations' },
  { id: 'applying_rules', name: 'Applying Nyāya Rules', percent: 70, desc: 'Synthesizing 5-stage Pañcāvayava deduction & Vyāpti' },
  { id: 'validating', name: 'Validating Reasoning', percent: 90, desc: 'Executing Hetvābhāsa fallacy checks (5 tests)' },
  { id: 'generating', name: 'Generating Conclusion', percent: 100, desc: 'Producing defeasible epistemic resolution & report' },
];

// Canonical Tolkāppiyam Corpus Architecture
export const CANONICAL_CORPUS = {
  id: 'tolkappiyam',
  name: 'Tolkāppiyam',
  tamilName: 'தொல்காப்பியம்',
  author: 'Tolkāppiyar (தொல்காப்பியர்)',
  period: 'Classical Antiquity (~3rd c. BCE)',
  totalSutras: 1610,
  total_sutras_canonical: 1610,
  indexed_sutras_active: 6,
  formattedCount: '1,610 Sūtras',
  canonicalFormattedCount: '1,610 Canonical',
  description: 'The foundational masterwork of classical Tamil grammar, linguistic semiotics, eco-poetics (Tiṇai), and ontological epistemology.',
  sections: [
    {
      id: 'eluttu',
      name: 'Eḻuttatikāram (எழுத்ததிகாரம்)',
      shortTamil: 'எழுத்து',
      sutrasCount: 483,
      activeSutrasCount: 0,
      canonicalSutrasCount: 483,
      focus: 'Phonology, Orthography, Morphophonemics, Metrical Acoustics',
      subdivisions: ['Nūṉmarapu', 'Moḻimarapu', 'Piṟappiyal', 'Puṇariyal', 'Tokaimarapu', 'Urupuiyal', 'Uyiṟmayaṅkiyal', 'Puḷḷimayaṅkiyal', 'Kuṟṟiyalukarappuṇariyal'],
    },
    {
      id: 'col',
      name: 'Collatikāram (சொல்லதிகாரம்)',
      shortTamil: 'சொல்',
      sutrasCount: 463,
      activeSutrasCount: 0,
      canonicalSutrasCount: 463,
      focus: 'Morphology, Syntax, Semantics, Nominal/Verbal Classes, Semantic Cases',
      subdivisions: ['Kiḷaviyākkam', 'Vēṟṟumaiyiyal', 'Vēṟṟumaimayankiyal', 'Viḷimarapu', 'Peyariyal', 'Viṉaiyiyal', 'Iṭaiyiyal', 'Uriyiyal', 'Eccaviyal'],
    },
    {
      id: 'porul',
      name: 'Poruḷatikāram (பொருளதிகாரம்)',
      shortTamil: 'பொருள்',
      sutrasCount: 664,
      activeSutrasCount: 6,
      canonicalSutrasCount: 664,
      focus: 'Poetics, Semiotics, Tiṇai Ecology, Psychology, Aesthetics & Moral Sociology',
      subdivisions: ['Akattiṇaiyiyal', 'Puṟattiṇaiyiyal', 'Kaḷaviyal', 'Kaṟpiyal', 'Poruḷiyal', 'Meyppāṭṭiyal', 'Uvamaviyal', 'Ceyyuḷiyal', 'Marapiyal'],
    },
  ],
};

// Genuine Research Prompts for interactive evaluation in Query Center
export const BENCHMARK_RESEARCH_PROMPTS = [
  {
    id: 'prompt-tinai',
    title: 'Tiṇai Eco-Semiotics (குறிஞ்சி நில ஒழுக்கம்)',
    query: 'குறிஞ்சி நிலத்தின் முதற்பொருள், கருப்பொருள், உரிப்பொருள் தொடர்பு எவ்வாறு அக ஒழுக்கத்தை உணர்த்துகிறது?',
    queryType: 'How / Process',
    depth: 2,
    focus: 'Relationship',
    corpusName: 'Tolkāppiyam (தொல்காப்பியம்)',
    translation: 'How does the relationship among mutal, karu, and uri in Kurinji landscape signify inner poetics?',
    description: 'Invariable concomitance between mountainous ecology and emotional interiority',
  },
  {
    id: 'prompt-justice',
    title: 'Jurisprudential Dharma (அறநெறி முறைமை)',
    query: 'அறனும் பொருளும் இன்பமும் சிறந்த முறைமை இயற்றுக',
    queryType: 'Why / Justification',
    depth: 2,
    focus: 'Judgment / Justice',
    corpusName: 'Tolkāppiyam (தொல்காப்பியம்)',
    translation: 'Enact the superior systematic order of virtue, wealth, and love according to canonical tradition.',
    description: 'Constitutional statecraft and moral epistemology in ancient Tamil governance',
  },
  {
    id: 'prompt-affect',
    title: 'Aesthetic Psychology (மெய்ப்பாட்டியல்)',
    query: 'நகையே அழுகை இளிவரல் மருட்கை எண்வகை மெய்ப்பாடுகள்',
    queryType: 'What / Fact',
    depth: 2,
    focus: 'Character',
    corpusName: 'Tolkāppiyam (தொல்காப்பியம்)',
    translation: 'The eight primary aesthetic sentiments: laughter, grief, disparagement, wonder, etc.',
    description: 'Eight-fold canonical aesthetic sentiments and their psychological manifestations',
  },
];

export function ReasonerProvider({ children }) {
  // 1. Corpus State
  const [corpus, setCorpus] = useState(CANONICAL_CORPUS);
  const [isLoadingCorpus, setIsLoadingCorpus] = useState(false);
  const [corpusError, setCorpusError] = useState(null);

  // 2. Query Formulation & Search Configuration State (Clean initial state; benchmark prompts selectable from dropdown)
  const [queryText, setQueryText] = useState('');
  const [queryType, setQueryType] = useState(BENCHMARK_RESEARCH_PROMPTS[0].queryType);
  const [depth, setDepth] = useState(BENCHMARK_RESEARCH_PROMPTS[0].depth);
  const [focus, setFocus] = useState(BENCHMARK_RESEARCH_PROMPTS[0].focus);
  const [searchMode, setSearchMode] = useState('hybrid'); // 'hybrid' | 'semantic' | 'keyword'
  const [topK, setTopK] = useState(5);
  const [filterTinai, setFilterTinai] = useState('all');
  const [filterSection, setFilterSection] = useState('all');

  // 3. Evidence State (Starts completely empty until search execution)
  const [evidenceRecords, setEvidenceRecords] = useState([]);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState(null);

  // 4. Knowledge Graph State (Populated live from Flask / Neo4j Aura)
  const [graphNodes, setGraphNodes] = useState([]);
  const [graphEdges, setGraphEdges] = useState([]);
  const [graphCategories, setGraphCategories] = useState(null);
  const [selectedGraphNodeId, setSelectedGraphNodeId] = useState(null);
  const [activeCategoryFilter, setActiveCategoryFilter] = useState(null);
  const [graphZoom, setGraphZoom] = useState(1);
  const [graphPan, setGraphPan] = useState({ x: 0, y: 0 });
  const [isLoadingGraph, setIsLoadingGraph] = useState(false);
  const [graphError, setGraphError] = useState(null);

  // Live Knowledge Graph Statistics & Structural Health
  const [graphStatistics, setGraphStatistics] = useState(null);
  const [graphHealth, setGraphHealth] = useState(null);
  const [isLoadingStats, setIsLoadingStats] = useState(false);
  const [statsError, setStatsError] = useState(null);

  // Live Aggregated Dashboard Summary State
  const [dashboardSummary, setDashboardSummary] = useState(null);
  const [isLoadingDashboard, setIsLoadingDashboard] = useState(false);
  const [dashboardError, setDashboardError] = useState(null);

  // 5. Reasoning Trace Stages (Synthesized dynamically per query)
  const [reasoningStages, setReasoningStages] = useState([]);
  const [selectedStageIndex, setSelectedStageIndex] = useState(0);
  const [isLoadingReasoning, setIsLoadingReasoning] = useState(false);
  const [reasoningError, setReasoningError] = useState(null);
  const [reasoningStatus, setReasoningStatus] = useState('idle'); // 'idle' | 'loading' | 'success' | 'empty' | 'insufficient' | 'error'

  // 6. Defeasible Fallacy & Validation Results (Evaluated per evidence set)
  const [validationResults, setValidationResults] = useState(null);
  const [isValidatingFallacies, setIsValidatingFallacies] = useState(false);
  const [fallacyValidationError, setFallacyValidationError] = useState(null);

  // 7. Proof Trace State (Constructed dynamically from real evidence paths)
  const [proofNodes, setProofNodes] = useState([]);
  const [proofEdges, setProofEdges] = useState([]);
  const [proofSteps, setProofSteps] = useState([]);
  const [proofTraceData, setProofTraceData] = useState(null);
  const [selectedProofNodeId, setSelectedProofNodeId] = useState(null);
  const [isLoadingProofTrace, setIsLoadingProofTrace] = useState(false);
  const [proofTraceError, setProofTraceError] = useState(null);

  // Cytoscape Proof Trace Focus State & Insufficient Evidence State
  const [isShowingProofTrace, setIsShowingProofTrace] = useState(false);
  const [insufficientEvidence, setInsufficientEvidence] = useState(false);

  // 8. Final Answer & Justification State (Starts null in clean idle state)
  const [finalAnswer, setFinalAnswer] = useState(null);

  // 9. AI Workflow & Hybrid RAG Query State
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [currentWorkflowStageIndex, setCurrentWorkflowStageIndex] = useState(0);
  const [workflowProgressPercent, setWorkflowProgressPercent] = useState(0);
  const [queryStatus, setQueryStatus] = useState('idle'); // 'idle' | 'loading' | 'success' | 'empty' | 'timeout' | 'error'
  const [queryError, setQueryError] = useState(null);
  const [queryStats, setQueryStats] = useState(null);

  // 10. Unified System Status State (Flask Core, Neo4j Aura, RAG Engine, KG Store, Corpus)
  const [systemStatus, setSystemStatus] = useState(null);
  const [isLoadingSystemStatus, setIsLoadingSystemStatus] = useState(true);
  const [systemStatusError, setSystemStatusError] = useState(null);

  // Active timers & network request cancellation refs
  const workflowTimersRef = useRef([]);
  const activeAbortControllerRef = useRef(null);

  const clearWorkflowTimers = () => {
    workflowTimersRef.current.forEach((id) => clearTimeout(id));
    workflowTimersRef.current = [];
  };

  useEffect(() => {
    return () => {
      clearWorkflowTimers();
      if (activeAbortControllerRef.current) {
        activeAbortControllerRef.current.abort();
        activeAbortControllerRef.current = null;
      }
    };
  }, []);

  // Live Initialization: Fetch real Knowledge Graph topology, statistics, health, corpus info, dashboard summary, and unified system status
  const loadLiveInitialData = useCallback(async (externalSignal = null) => {
    setIsLoadingGraph(true);
    setIsLoadingStats(true);
    setIsLoadingCorpus(true);
    setIsLoadingDashboard(true);
    setIsLoadingSystemStatus(true);
    setGraphError(null);
    setStatsError(null);
    setCorpusError(null);
    setDashboardError(null);
    setSystemStatusError(null);

    try {
      const [statsResult, healthResult, graphResult, corpusResult, dashboardResult, statusResult] = await Promise.allSettled([
        getGraphStatistics({ signal: externalSignal }),
        getGraphHealth({ signal: externalSignal }),
        getGraphElements({ limit: 250, source: 'auto', signal: externalSignal }),
        getCorpusInfo({ signal: externalSignal }),
        getDashboardSummary({ signal: externalSignal }),
        getSystemStatus({ signal: externalSignal }),
      ]);

      if (dashboardResult.status === 'fulfilled' && dashboardResult.value?.data) {
        const dData = dashboardResult.value.data;
        setDashboardSummary(dData);
        if (dData.reasoning_and_soundness?.validation_results) {
          setValidationResults(dData.reasoning_and_soundness.validation_results);
        }
      } else if (dashboardResult.status === 'rejected') {
        setDashboardError(dashboardResult.reason?.message || 'Failed to load dashboard summary');
      }

      if (corpusResult.status === 'fulfilled' && corpusResult.value?.data) {
        const backendCorpus = corpusResult.value.data;
        const activeCount = backendCorpus.indexed_sutras_active ?? 6;
        const canonicalTotal = backendCorpus.total_sutras_canonical || 1610;
        setCorpus((prev) => ({
          ...prev,
          name: 'Tolkāppiyam',
          tamilName: 'தொல்காப்பியம்',
          author: backendCorpus.author || prev.author,
          period: backendCorpus.period || prev.period,
          totalSutras: canonicalTotal,
          total_sutras_canonical: canonicalTotal,
          indexed_sutras_active: activeCount,
          books_count: backendCorpus.books_count || 3,
          formattedCount: `${canonicalTotal.toLocaleString()} Sūtras`,
          canonicalFormattedCount: `${canonicalTotal.toLocaleString()} Canonical`,
          books: (backendCorpus.books || prev.sections).map((b) => {
            const isPorul = b.id === 'porul' || (b.name && b.name.toLowerCase().includes('porul'));
            const canonicalCount = b.canonical_sutras_count ?? b.sutra_count ?? (isPorul ? 664 : b.id === 'col' ? 463 : 483);
            return {
              ...b,
              active_sutras_count: b.active_sutras_count ?? (isPorul ? activeCount : 0),
              canonical_sutras_count: canonicalCount,
              sutra_count: canonicalCount,
            };
          }),
          sections: prev.sections.map((sec) => {
            const matchedBook = backendCorpus.books?.find((b) => b.id === sec.id);
            const isPorul = sec.id === 'porul';
            const canonicalCount = matchedBook?.canonical_sutras_count ?? sec.canonicalSutrasCount ?? (isPorul ? 664 : sec.id === 'col' ? 463 : 483);
            return {
              ...sec,
              activeSutrasCount: matchedBook?.active_sutras_count ?? (isPorul ? activeCount : 0),
              canonicalSutrasCount: canonicalCount,
              sutrasCount: canonicalCount,
            };
          }),
        }));
      } else if (corpusResult.status === 'rejected') {
        setCorpusError(corpusResult.reason?.message || 'Failed to load corpus metadata');
      }

      if (statsResult.status === 'fulfilled' && statsResult.value?.data) {
        setGraphStatistics(statsResult.value.data);
        if (statsResult.value.data.categories) {
          setGraphCategories(statsResult.value.data.categories);
        }
      } else if (statsResult.status === 'rejected') {
        setStatsError(statsResult.reason?.message || 'Failed to load graph statistics');
      }

      if (healthResult.status === 'fulfilled' && healthResult.value?.data) {
        const hData = { ...healthResult.value.data };
        if (typeof hData.percentageValid !== 'number') {
          const totalN = hData.node_count || 1;
          const isoCount = Array.isArray(hData.isolated_nodes) ? hData.isolated_nodes.length : 0;
          const invEdges = hData.invalid_edges_count || 0;
          hData.percentageValid = hData.valid
            ? (hData.is_connected ? 100 : 92)
            : Math.max(10, Math.round(100 - (isoCount / totalN) * 50 - invEdges * 10));
        }
        setGraphHealth(hData);
      } else if (healthResult.status === 'rejected') {
        setStatsError((prev) => prev || healthResult.reason?.message || 'Failed to load graph health');
      }

      if (graphResult.status === 'fulfilled' && graphResult.value?.data) {
        const gData = graphResult.value.data;
        setGraphNodes(gData.nodes || []);
        setGraphEdges(gData.relationships || gData.edges || []);
        if (gData.categories) {
          setGraphCategories(gData.categories);
        }
      } else if (graphResult.status === 'rejected') {
        setGraphError(graphResult.reason?.message || 'Failed to load graph elements from backend');
      }

      if (statusResult.status === 'fulfilled' && statusResult.value?.data) {
        setSystemStatus(statusResult.value.data);
      } else if (statusResult.status === 'rejected') {
        setSystemStatusError(statusResult.reason?.message || 'Unified system status probe failed');
      }
    } catch (err) {
      if (err.name === 'AbortError') return;
      setGraphError(err.message || 'Initialization error');
    } finally {
      setIsLoadingGraph(false);
      setIsLoadingStats(false);
      setIsLoadingCorpus(false);
      setIsLoadingDashboard(false);
      setIsLoadingSystemStatus(false);
    }
  }, []);

  // Dedicated manual re-probe for live system status
  const refetchSystemStatus = useCallback(async (signal = null) => {
    setIsLoadingSystemStatus(true);
    setSystemStatusError(null);
    try {
      const res = await getSystemStatus({ signal, timeoutMs: 10000 });
      if (res?.data) {
        setSystemStatus(res.data);
        return res.data;
      }
    } catch (err) {
      if (err.name === 'AbortError') return null;
      setSystemStatusError(err.message || 'System status probe failed');
    } finally {
      setIsLoadingSystemStatus(false);
    }
    return null;
  }, []);

  useEffect(() => {
    let ignore = false;
    const controller = new AbortController();

    Promise.resolve().then(() => {
      if (!ignore) {
        loadLiveInitialData(controller.signal);
      }
    });

    return () => {
      ignore = true;
      controller.abort();
    };
  }, [loadLiveInitialData]);

  // Compute dynamic currentQuery context object derived purely from active inquiry & real results
  const currentQuery = useMemo(() => {
    const topSource = finalAnswer?.keySources?.[0];
    return {
      id: 'active-session-query',
      verseId: topSource?.sutra || topSource?.id || 'Tolkāppiyam',
      corpus: 'Tolkāppiyam (Poruḷatikāram)',
      tamilText: queryText,
      domain: focus || 'Tiṇai Eco-Psychology & Ontological Semiotics',
      hypothesis: queryText ? `Inquiry into canonical Tamil poetics: "${queryText.slice(0, 70)}..."` : '',
      hetu: 'Grounding via Classical Tamil morpho-semantic rules and multi-channel Hybrid RAG evidence',
      vyapti: 'Universal concomitance between spatio-temporal signifiers and emotional interiority',
      upanaya: 'Case subsumption evaluated against canonical Tolkāppiyam verses',
      nigamana: finalAnswer?.englishAnswer || 'Awaiting evidence-grounded inference execution',
      neuralConfidence: typeof finalAnswer?.confidenceScore === 'number' ? finalAnswer.confidenceScore : 0.0,
      symbolicValidity: validationResults?.symbolicValidity || 'Awaiting Epistemic Verification',
      pramana: validationResults?.pramana || 'Pratyakṣa + Śabda + Anumāna',
      hetvabhasaCheck: validationResults?.hetvabhasaCheck || 'Not Evaluated',
      reasoningStages: reasoningStages,
    };
  }, [queryText, focus, finalAnswer, validationResults, reasoningStages]);

  // Run AI Reasoning Workflow via real Backend Hybrid RAG & Answer endpoints
  const runAnalyze = useCallback(async () => {
    const cleanQuery = (queryText || '').trim();
    if (!cleanQuery) return;

    if (activeAbortControllerRef.current) {
      activeAbortControllerRef.current.abort();
      activeAbortControllerRef.current = null;
    }

    clearWorkflowTimers();

    const controller = new AbortController();
    activeAbortControllerRef.current = controller;

    setIsAnalyzing(true);
    setQueryStatus('loading');
    setQueryError(null);
    setCurrentWorkflowStageIndex(0);
    setWorkflowProgressPercent(20);

    const t1 = setTimeout(() => {
      setCurrentWorkflowStageIndex(1);
      setWorkflowProgressPercent(45);
    }, 350);

    const t2 = setTimeout(() => {
      setCurrentWorkflowStageIndex(2);
      setWorkflowProgressPercent(70);
    }, 850);

    const t3 = setTimeout(() => {
      setCurrentWorkflowStageIndex(3);
      setWorkflowProgressPercent(90);
    }, 1350);

    workflowTimersRef.current = [t1, t2, t3];
    const startTime = performance.now();

    const activeFilters = {
      ...(filterTinai && filterTinai !== 'all' ? { tinai: filterTinai } : {}),
      ...(filterSection && filterSection !== 'all' ? { section: filterSection } : {}),
      query_type: queryType,
      focus,
    };

    try {
      // Execute multi-channel Hybrid Search and Grounded Answer Generation concurrently
      const [searchResult, answerResult] = await Promise.allSettled([
        searchPassages({
          query: cleanQuery,
          mode: searchMode,
          topK,
          filters: activeFilters,
          tinai: filterTinai !== 'all' ? filterTinai : null,
          section: filterSection !== 'all' ? filterSection : null,
          includeGraph: true,
          rerank: true,
          signal: controller.signal,
          timeoutMs: 30000,
        }),
        generateGroundedAnswer({
          query: cleanQuery,
          topK,
          depth: depth || 2,
          filters: activeFilters,
          signal: controller.signal,
          timeoutMs: 35000,
        }),
      ]);

      const elapsedMs = Math.round(performance.now() - startTime);
      clearWorkflowTimers();
      setCurrentWorkflowStageIndex(4);
      setWorkflowProgressPercent(100);

      // Check if both calls failed
      if (searchResult.status === 'rejected' && answerResult.status === 'rejected') {
        const primaryErr = searchResult.reason || answerResult.reason || new Error('Search request failed');
        throw primaryErr;
      }

      // Extract raw items and answer details
      const searchData = searchResult.status === 'fulfilled' ? (searchResult.value?.data || {}) : {};
      const answerData = answerResult.status === 'fulfilled' ? (answerResult.value?.data || {}) : {};

      const searchItems = searchData.ranked_results || [];
      const answerItems = answerData.retrieved_evidence || [];
      const items = answerItems.length > 0 ? answerItems : searchItems;

      const isInsufficient = answerData.insufficient_evidence || (answerData.reasoning_metadata?.is_sufficient === false) || (items.length === 0);
      const generatedFinalAnswer = answerData.final_answer || {};
      const reasoningMetadata = answerData.reasoning_metadata || {};
      const retrievalStats = answerData.retrieval_stats || searchData.retrieval_stats || {};
      const targetTinai = filterTinai !== 'all' ? filterTinai : (reasoningMetadata.tinai || 'Kuṟiñci');

      if (items.length === 0 || isInsufficient) {
        const mappedRecords = items.map(mapBackendEvidenceToUI);
        setEvidenceRecords(mappedRecords);
        setSelectedEvidenceId(mappedRecords[0]?.id || null);
        setQueryStatus('empty');
        setQueryError(null);
        setInsufficientEvidence(true);
        setQueryStats({
          latencyMs: elapsedMs,
          totalResults: items.length,
          pipelineVersion: reasoningMetadata.pipeline_version || '1.0.0',
          provider: reasoningMetadata.provider || 'openrouter',
          model: reasoningMetadata.model || 'unknown',
          mode: searchMode,
          topK,
          retrievalStats,
        });

        setFinalAnswer({
          status: 'insufficient_evidence',
          tamilAnswer: generatedFinalAnswer.tamilAnswer || 'தீர்மானிக்கப் போதுமான தொல்காப்பியச் சான்றுகள் கிடைக்கவில்லை.',
          englishAnswer: generatedFinalAnswer.englishAnswer || 'Insufficient canonical evidence retrieved to answer query without speculation.',
          subtitle: generatedFinalAnswer.subtitle || (reasoningMetadata.insufficient_reason ? `Evidence threshold unmet: ${reasoningMetadata.insufficient_reason}` : 'Epistemic validation requires additional primary sources.'),
          confidenceScore: 0.0,
          starsCount: 0.0,
          verdictStatus: generatedFinalAnswer.verdictStatus || 'Insufficient Canonical Evidence (போதிய சான்றுகள் இல்லை)',
          justificationTamil: generatedFinalAnswer.justificationTamil || 'தொல்காப்பிய மூல நூல்களில் வினவப்பட்ட கருதுகோளுக்குப் போதிய சான்றுகள் இல்லை.',
          justificationEnglish: generatedFinalAnswer.justificationEnglish || 'Retrieved canonical evidence did not meet the required relevance or count criteria. Speculative answer generation was blocked.',
          keySources: generatedFinalAnswer.keySources || [],
        });

        // Insufficient evidence: clean reset of reasoning deduction and proof trace
        setReasoningStages([]);
        setReasoningStatus('insufficient');
        setReasoningError(null);
        setIsLoadingReasoning(false);

        setProofNodes([]);
        setProofEdges([]);
        setProofSteps([]);
        setSelectedProofNodeId(null);
        setIsLoadingProofTrace(false);
        setProofTraceError(null);
        setProofTraceData({
          status: 'INSUFFICIENT_EVIDENCE',
          insufficient_evidence: true,
          is_valid: false,
          reason:
            reasoningMetadata.insufficient_reason ||
            'The current query retrieved insufficient canonical sūtras to establish an unbroken Nyāya proof chain. At least 2 grounded verses are required to derive Vyāpti.',
          missing_requirements: [
            'Terrestrial habitat (Mutalporuḷ) canonical verse',
            'Corroborating biotic signifier (Karupporuḷ) canonical verse to establish Vyāpti',
          ],
          steps: [],
          nodes: [],
          edges: [],
          traceable_paths: [],
        });

        // Trigger fallacy validation on empty evidence
        try {
          const valRes = await validateFallacies({
            tinai: targetTinai,
            evidenceItems: items,
            evidenceCount: items.length,
            signal: controller.signal,
          });
          if (valRes?.success && valRes?.data) {
            setValidationResults(valRes.data);
          }
        } catch {
          // ignore background fallacy check failure
        }
      } else {
        const mappedRecords = items.map(mapBackendEvidenceToUI);
        setEvidenceRecords(mappedRecords);
        setSelectedEvidenceId(mappedRecords[0].id);
        setQueryStatus('success');
        setQueryError(null);
        setInsufficientEvidence(false);
        setQueryStats({
          latencyMs: elapsedMs,
          totalResults: items.length,
          pipelineVersion: reasoningMetadata.pipeline_version || '1.0.0',
          provider: reasoningMetadata.provider || 'openrouter',
          model: reasoningMetadata.model || 'unknown',
          mode: searchMode,
          topK,
          retrievalStats,
        });

        const topItem = mappedRecords[0];

        setFinalAnswer({
          status: 'sufficient',
          tamilAnswer: generatedFinalAnswer.tamilAnswer || '',
          englishAnswer: generatedFinalAnswer.englishAnswer || '',
          subtitle: generatedFinalAnswer.subtitle || `Retrieved via ${searchMode.toUpperCase()} mode: Grounded on ${items.length} canonical verses.`,
          confidenceScore: typeof generatedFinalAnswer.confidenceScore === 'number'
            ? generatedFinalAnswer.confidenceScore
            : (typeof answerData.confidence_info?.confidenceScore === 'number'
              ? answerData.confidence_info.confidenceScore
              : topItem.confidence),
          starsCount: typeof generatedFinalAnswer.starsCount === 'number'
            ? generatedFinalAnswer.starsCount
            : Number((topItem.confidence * 5).toFixed(1)),
          verdictStatus: generatedFinalAnswer.verdictStatus || answerData.confidence_info?.verdictStatus || `Sound Canonical Grounding (${items.length} Verses)`,
          justificationTamil: generatedFinalAnswer.justificationTamil || '',
          justificationEnglish: generatedFinalAnswer.justificationEnglish || '',
          keySources: (generatedFinalAnswer.keySources && generatedFinalAnswer.keySources.length > 0)
            ? generatedFinalAnswer.keySources
            : (answerData.sources || mappedRecords.map((m) => ({
                id: m.id,
                label: m.code,
                sutra: m.reference,
                section: m.section,
                topic: m.badges[0]?.label || 'Evidence',
                score: m.confidenceFormatted,
              }))),
        });

        // Concurrently fetch real Proof Trace DAG, Fallacy Validation, and 5-stage Nyāya deduction from backend
        setIsLoadingReasoning(true);
        setIsLoadingProofTrace(true);
        setReasoningStatus('loading');
        setReasoningError(null);
        setProofTraceError(null);

        try {
          const [proofResult, fallacyResult, deduceResult] = await Promise.allSettled([
            getProofTrace({
              query: cleanQuery,
              queryText: cleanQuery,
              evidenceItems: items,
              tinai: targetTinai,
              minEvidenceThreshold: 2,
              signal: controller.signal,
            }),
            validateFallacies({
              tinai: targetTinai,
              evidenceItems: items,
              evidenceCount: items.length,
              signal: controller.signal,
            }),
            deduceReasoning({
              query: cleanQuery,
              tinai: targetTinai,
              evidence: items,
              signal: controller.signal,
            }),
          ]);

          if (proofResult.status === 'fulfilled' && proofResult.value?.data) {
            const ptData = proofResult.value.data;
            setProofTraceData(ptData);
            if (
              ptData.insufficient_evidence ||
              ptData.status === 'INSUFFICIENT_EVIDENCE' ||
              !ptData.nodes ||
              ptData.nodes.length === 0
            ) {
              setProofNodes([]);
              setProofEdges([]);
              setProofSteps([]);
              setSelectedProofNodeId(null);
            } else {
              const nodes = ptData.nodes || ptData.proofNodes || [];
              const edges = ptData.edges || ptData.proofEdges || [];
              const steps = ptData.steps || ptData.traceSteps || [];
              setProofNodes(nodes);
              setProofEdges(edges);
              setProofSteps(steps);
              if (nodes.length > 0) {
                setSelectedProofNodeId(nodes[0].id);
              }
            }
          } else if (proofResult.status === 'rejected') {
            setProofTraceError(proofResult.reason?.message || 'Failed to generate proof trace');
            setProofNodes([]);
            setProofEdges([]);
            setProofSteps([]);
            setSelectedProofNodeId(null);
            setProofTraceData({
              status: 'INSUFFICIENT_EVIDENCE',
              insufficient_evidence: true,
              is_valid: false,
              reason: 'Proof trace generation failed or evidence is insufficient to complete the deduction chain.',
              missing_requirements: ['Grounded canonical sūtras with verifiable Vyāpti'],
              steps: [],
              nodes: [],
              edges: [],
              traceable_paths: [],
            });
          }

          if (fallacyResult.status === 'fulfilled' && fallacyResult.value?.data) {
            setValidationResults(fallacyResult.value.data);
          }

          if (deduceResult.status === 'fulfilled' && deduceResult.value?.data?.reasoningStages) {
            const stages = deduceResult.value.data.reasoningStages;
            setReasoningStages(stages);
            setReasoningStatus(stages.length > 0 ? 'success' : 'empty');
            setReasoningError(null);
            setSelectedStageIndex(0);
          } else if (deduceResult.status === 'rejected') {
            setReasoningError(deduceResult.reason?.message || 'Failed to deduce reasoning stages');
            setReasoningStatus('error');
            setReasoningStages([]);
          }
        } catch (reasoningErr) {
          setReasoningError(reasoningErr.message || 'Background reasoning deduction failed');
          setReasoningStatus('error');
          setReasoningStages([]);
        } finally {
          setIsLoadingReasoning(false);
          setIsLoadingProofTrace(false);
        }
      }
    } catch (err) {
      if (err.name === 'AbortError') return;
      clearWorkflowTimers();
      const isTimeout = err.isTimeout || err.name === 'TimeoutError';
      setQueryStatus(isTimeout ? 'timeout' : 'error');
      setQueryError({
        message: err.message || (isTimeout ? 'Search request timed out after 35s' : 'API request failed'),
        code: err.code || (isTimeout ? 'REQUEST_TIMEOUT' : 'API_ERROR'),
        status: err.status,
        isTimeout,
      });
      setReasoningStages([]);
      setReasoningStatus('error');
      setReasoningError(err.message || 'Analysis failed');
      setIsLoadingReasoning(false);
    } finally {
      setIsAnalyzing(false);
      activeAbortControllerRef.current = null;
    }
  }, [queryText, depth, focus, queryType, searchMode, topK, filterTinai, filterSection]);

  // Live Fallacy Verification directly against Flask Defeasible Validator
  const revalidateFallacies = useCallback(
    async ({ tinai = 'Kuṟiñci', evidenceCount = 5, evidenceItems = null } = {}) => {
      setIsValidatingFallacies(true);
      setFallacyValidationError(null);
      try {
        const res = await validateFallacies({
          tinai,
          evidenceCount,
          evidenceItems: evidenceItems || (evidenceRecords.length > 0 ? evidenceRecords : null),
        });
        if (res?.success && res?.data) {
          setValidationResults(res.data);
          return res.data;
        }
      } catch (err) {
        setFallacyValidationError(err.message || 'Failed to re-validate fallacies with Flask');
      } finally {
        setIsValidatingFallacies(false);
      }
    },
    [evidenceRecords]
  );

  // Dynamic On-Demand Nyāya Deductive Reasoning via Flask /api/reasoning/deduce
  const runDeduceReasoning = useCallback(
    async ({ query = null, tinai = null, evidenceItems = null } = {}) => {
      const activeQuery = (query || queryText || '').trim();
      const activeTinai = tinai || (filterTinai !== 'all' ? filterTinai : 'Kuṟiñci');
      const activeEvidence = evidenceItems || (evidenceRecords.length > 0 ? evidenceRecords.map((e) => e.rawItem || e) : []);

      if (!activeQuery) {
        setReasoningError('Please enter a query or select a benchmark prompt to deduce reasoning.');
        setReasoningStatus('empty');
        return null;
      }

      if (activeEvidence.length === 0 && !evidenceItems) {
        setReasoningStatus('insufficient');
        setReasoningStages([]);
        return null;
      }

      setIsLoadingReasoning(true);
      setReasoningError(null);
      setReasoningStatus('loading');

      try {
        const res = await deduceReasoning({
          query: activeQuery,
          tinai: activeTinai,
          evidence: activeEvidence,
        });

        if (res?.success && res?.data) {
          const data = res.data;
          const stages = data.reasoningStages || [];
          setReasoningStages(stages);
          setReasoningStatus(stages.length > 0 ? 'success' : 'empty');
          setSelectedStageIndex(0);

          if (data.proofNodes && data.proofNodes.length > 0) {
            setProofNodes(data.proofNodes);
          }
          if (data.proofEdges && data.proofEdges.length > 0) {
            setProofEdges(data.proofEdges);
          }
          return data;
        } else {
          throw new Error(res?.error?.message || 'Failed to retrieve reasoning stages from backend');
        }
      } catch (err) {
        setReasoningError(err.message || 'Reasoning deduction failed. Verify Flask backend is running.');
        setReasoningStatus('error');
        setReasoningStages([]);
        return null;
      } finally {
        setIsLoadingReasoning(false);
      }
    },
    [queryText, filterTinai, evidenceRecords]
  );

  // Reset to Clean Initial Idle State
  const resetToDefault = useCallback(() => {
    clearWorkflowTimers();
    if (activeAbortControllerRef.current) {
      activeAbortControllerRef.current.abort();
      activeAbortControllerRef.current = null;
    }
    setIsAnalyzing(false);
    setCurrentWorkflowStageIndex(0);
    setWorkflowProgressPercent(0);
    setQueryStatus('idle');
    setQueryError(null);
    setQueryStats(null);
    setInsufficientEvidence(false);

    // Reset Query & search configuration to clean initial state
    setQueryText('');
    setQueryType(BENCHMARK_RESEARCH_PROMPTS[0].queryType);
    setDepth(BENCHMARK_RESEARCH_PROMPTS[0].depth);
    setFocus(BENCHMARK_RESEARCH_PROMPTS[0].focus);
    setSearchMode('hybrid');
    setTopK(5);
    setFilterTinai('all');
    setFilterSection('all');

    // Clear Evidence & Results (Zero mock data)
    setEvidenceRecords([]);
    setSelectedEvidenceId(null);
    setFinalAnswer(null);
    setProofNodes([]);
    setProofEdges([]);
    setProofSteps([]);
    setProofTraceData(null);
    setSelectedProofNodeId(null);
    setIsLoadingProofTrace(false);
    setProofTraceError(null);

    // Reset Reasoning Deduction State
    setReasoningStages([]);
    setSelectedStageIndex(0);
    setIsLoadingReasoning(false);
    setReasoningError(null);
    setReasoningStatus('idle');
    setValidationResults(null);

    // Reset Graph View
    setSelectedGraphNodeId(null);
    setActiveCategoryFilter(null);
    setGraphZoom(1);
    setGraphPan({ x: 0, y: 0 });
    setIsShowingProofTrace(false);
  }, []);

  // Handler for selecting research example
  const handleSelectExample = useCallback((ex) => {
    if (!ex) return;
    setQueryText(ex.query);
    if (ex.queryType) setQueryType(ex.queryType);
    if (ex.depth) setDepth(ex.depth);
    if (ex.focus) setFocus(ex.focus);
    setQueryStatus('idle');
    setQueryError(null);
  }, []);

  const clearQueryStatus = useCallback(() => {
    setQueryStatus('idle');
    setQueryError(null);
  }, []);

  // Zoom handlers for graph
  const handleGraphZoomIn = useCallback(() => {
    setGraphZoom((prev) => Math.min(2.0, +(prev + 0.15).toFixed(2)));
  }, []);

  const handleGraphZoomOut = useCallback(() => {
    setGraphZoom((prev) => Math.max(0.6, +(prev - 0.15).toFixed(2)));
  }, []);

  const handleGraphReset = useCallback(() => {
    setGraphZoom(1);
    setGraphPan({ x: 0, y: 0 });
    setSelectedGraphNodeId(null);
  }, []);

  const handleGraphFitToScreen = useCallback(() => {
    setGraphZoom(0.92);
    setGraphPan({ x: 10, y: 10 });
  }, []);

  // Cross-highlighting handlers linking Evidence, Graph, Proof DAG, and Reasoning Stages
  const handleSetSelectedEvidenceId = useCallback((evidenceId) => {
    if (!evidenceId) {
      setSelectedEvidenceId(null);
      setSelectedGraphNodeId(null);
      return;
    }

    const ev = evidenceRecords.find(
      (e) => e.id === evidenceId || e.code === evidenceId || e.passageId === evidenceId
    );

    const targetId = ev ? (ev.passageId || ev.id) : evidenceId;
    const targetCode = ev ? ev.code : (evidenceId.startsWith('E') ? evidenceId : null);

    setSelectedEvidenceId(ev ? ev.id : evidenceId);
    setSelectedGraphNodeId(targetId);

    if (targetCode) {
      setSelectedProofNodeId(targetCode);
    } else {
      setSelectedProofNodeId(targetId);
    }

    const matchedStageIdx = reasoningStages.findIndex(
      (s) =>
        s.linkedEvidenceId === evidenceId ||
        s.linkedEvidenceId === targetId ||
        s.linkedEvidenceId === targetCode ||
        (Array.isArray(s.linkedEvidenceIds) &&
          (s.linkedEvidenceIds.includes(evidenceId) ||
            s.linkedEvidenceIds.includes(targetId) ||
            s.linkedEvidenceIds.includes(targetCode)))
    );
    if (matchedStageIdx !== -1) {
      setSelectedStageIndex(matchedStageIdx);
    }
  }, [evidenceRecords, reasoningStages]);

  const handleSetSelectedProofNodeId = useCallback((nodeId) => {
    setSelectedProofNodeId(nodeId);
    if (!nodeId) return;

    const matchedProofNode = proofNodes.find((n) => n.id === nodeId);
    const targetGraphId = matchedProofNode?.passageId || nodeId;

    setSelectedGraphNodeId(targetGraphId);

    if (matchedProofNode?.passageId) {
      handleSetSelectedEvidenceId(matchedProofNode.passageId);
    } else if (nodeId.startsWith('E') || evidenceRecords.some((e) => e.id === nodeId || e.passageId === nodeId)) {
      handleSetSelectedEvidenceId(nodeId);
    }
  }, [proofNodes, evidenceRecords, handleSetSelectedEvidenceId]);

  const handleSetSelectedStageIndex = useCallback((index) => {
    setSelectedStageIndex(index);
    const stage = reasoningStages[index];
    const linkedEvId = stage?.linkedEvidenceId || (Array.isArray(stage?.linkedEvidenceIds) && stage.linkedEvidenceIds[0]) || null;
    if (linkedEvId) {
      const ev = evidenceRecords.find(
        (e) => e.id === linkedEvId || e.code === linkedEvId || e.passageId === linkedEvId
      );
      const targetId = ev ? (ev.passageId || ev.id) : linkedEvId;
      setSelectedEvidenceId(ev ? ev.id : linkedEvId);
      setSelectedProofNodeId(targetId);
      setSelectedGraphNodeId(targetId);
    }
  }, [reasoningStages, evidenceRecords]);

  const handleSetSelectedGraphNodeId = useCallback((nodeId) => {
    setSelectedGraphNodeId(nodeId);
    if (!nodeId) return;

    if (nodeId.startsWith('E') || ['P1', 'P2', 'R1', 'I1', 'C1'].includes(nodeId)) {
      setSelectedProofNodeId(nodeId);
    }
    const isEvidence = evidenceRecords.some((e) => e.id === nodeId || e.passageId === nodeId || e.code === nodeId);
    if (isEvidence || nodeId.startsWith('E')) {
      handleSetSelectedEvidenceId(nodeId);
    }
  }, [evidenceRecords, handleSetSelectedEvidenceId]);

  const showProofTrace = useCallback(() => {
    setIsShowingProofTrace(true);
  }, []);

  const resetGraph = useCallback(() => {
    setIsShowingProofTrace(false);
    setSelectedGraphNodeId(null);
  }, []);

  const loadBenchmarkEvidence = useCallback((archetype = 'tinai') => {
    setInsufficientEvidence(false);
    if (archetype === 'justice') {
      handleSelectExample(BENCHMARK_RESEARCH_PROMPTS[1]);
    } else if (archetype === 'affect') {
      handleSelectExample(BENCHMARK_RESEARCH_PROMPTS[2]);
    } else {
      handleSelectExample(BENCHMARK_RESEARCH_PROMPTS[0]);
    }
  }, [handleSelectExample]);

  const selectPassageForEvidence = useCallback((passage) => {
    if (!passage) return;
    const passageId = passage.id || passage.passage_id;
    const uiItem = mapBackendEvidenceToUI({
      ...passage,
      id: passageId,
      passage_id: passageId,
      text: passage.tamil_text || passage.text,
      translation: passage.english_translation || passage.translation,
      transliteration: passage.transliteration,
      sutra_number: passage.sutra_number,
      source: passage.work || 'Tolkāppiyam',
      section: passage.atikaram || passage.section,
      chapter: passage.iyal || passage.chapter,
      tinai: passage.tinai,
      entities: passage.entities || [],
      concepts: passage.concepts || [],
      category: passage.category || passage.tinai || 'Canonical Sūtra',
    }, evidenceRecords.length);

    setEvidenceRecords((prev) => {
      const exists = prev.some((e) => e.id === uiItem.id || e.passageId === uiItem.passageId);
      if (!exists) {
        return [uiItem, ...prev];
      }
      return prev;
    });

    setSelectedEvidenceId(uiItem.id);
    setSelectedGraphNodeId(passageId);
    setInsufficientEvidence(false);
  }, [evidenceRecords.length]);

  const value = {
    // 1. Corpus
    corpus,
    isLoadingCorpus,
    corpusError,
    refreshStats: loadLiveInitialData,
    selectPassageForEvidence,
    // 2. Query Formulation & Search Configuration
    queryText,
    setQueryText,
    queryType,
    setQueryType,
    depth,
    setDepth,
    focus,
    setFocus,
    searchMode,
    setSearchMode,
    topK,
    setTopK,
    filterTinai,
    setFilterTinai,
    filterSection,
    setFilterSection,
    currentQuery,
    handleSelectExample,
    researchExamples: BENCHMARK_RESEARCH_PROMPTS,
    // 3. Evidence
    evidenceRecords,
    selectedEvidenceId,
    setSelectedEvidenceId: handleSetSelectedEvidenceId,
    // 4. Knowledge Graph
    graphNodes,
    setGraphNodes,
    graphEdges,
    setGraphEdges,
    graphCategories,
    graphStatistics,
    graphHealth,
    isLoadingGraph,
    isLoadingStats,
    graphError,
    statsError,
    // Aggregated Dashboard Summary
    dashboardSummary,
    isLoadingDashboard,
    dashboardError,
    refetchDashboard: loadLiveInitialData,
    selectedGraphNodeId,
    setSelectedGraphNodeId: handleSetSelectedGraphNodeId,
    activeCategoryFilter,
    setActiveCategoryFilter,
    graphZoom,
    setGraphZoom,
    graphPan,
    setGraphPan,
    handleGraphZoomIn,
    handleGraphZoomOut,
    handleGraphReset,
    handleGraphFitToScreen,
    // 5. Reasoning Trace
    reasoningStages,
    selectedStageIndex,
    setSelectedStageIndex: handleSetSelectedStageIndex,
    isLoadingReasoning,
    reasoningError,
    reasoningStatus,
    runDeduceReasoning,
    // 6. Fallacy & Validation
    validationResults,
    revalidateFallacies,
    isValidatingFallacies,
    fallacyValidationError,
    // 7. Proof Trace DAG & Cytoscape Highlighting
    proofNodes,
    setProofNodes,
    proofEdges,
    setProofEdges,
    proofSteps,
    proofTraceData,
    selectedProofNodeId,
    setSelectedProofNodeId: handleSetSelectedProofNodeId,
    isLoadingProofTrace,
    proofTraceError,
    isShowingProofTrace,
    setIsShowingProofTrace,
    showProofTrace,
    resetGraph,
    insufficientEvidence,
    setInsufficientEvidence,
    loadBenchmarkEvidence,
    // 8. Final Answer & Justification
    finalAnswer,
    // 9. Workflow & Live Query State
    isAnalyzing,
    currentWorkflowStageIndex,
    workflowProgressPercent,
    currentWorkflowStage: REASONING_WORKFLOW_STAGES[currentWorkflowStageIndex],
    workflowStages: REASONING_WORKFLOW_STAGES,
    runAnalyze,
    resetToDefault,
    queryStatus,
    queryError,
    queryStats,
    clearQueryStatus,
    // 10. Unified System Health & Operational Diagnostics
    systemStatus,
    isLoadingSystemStatus,
    systemStatusError,
    refetchSystemStatus,
    isBackendOnline: Boolean(systemStatus !== null && !systemStatusError),
    isNeo4jOnline: Boolean(systemStatus?.services?.database?.connected),
    isRetrievalOnline: Boolean(systemStatus?.services?.retrieval?.healthy),
    isSystemDegraded: Boolean(systemStatus?.status === 'degraded'),
    isSystemHealthy: Boolean(systemStatus?.status === 'healthy'),
  };

  return <ReasonerContext.Provider value={value}>{children}</ReasonerContext.Provider>;
}

export function useReasoner() {
  const context = useContext(ReasonerContext);
  if (!context) {
    throw new Error('useReasoner must be used within a ReasonerProvider');
  }
  return context;
}
