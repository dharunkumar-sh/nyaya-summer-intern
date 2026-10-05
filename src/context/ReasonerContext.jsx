/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  generateGroundedAnswer,
  searchPassages,
  getGraphStatistics,
  getGraphHealth,
  getCorpusInfo,
  validateFallacies,
  getProofTrace,
  deduceReasoning,
  getDashboardSummary,
  getSystemStatus,
  graphApi,
  clearCache,
} from '../services/apiClient';
import { normalizeGraphData } from '../services/graphNormalization';
import {
  findNodeByStableId,
  findAssociatedEvidenceForNode,
  getInducedSubgraphNeighborhood,
} from '../services/nodeSyncService';
import { detectQueryLanguage } from '../services/languageService';
import {
  calculateClientConfidence,
  CONFIDENCE_LEVELS,
} from '../services/confidenceService';

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

// Genuine Research Prompts for interactive evaluation in Query Center (Tamil & English)
export const BENCHMARK_RESEARCH_PROMPTS = [
  {
    id: 'prompt-tinai-en',
    title: 'Kurinji Eco-Semiotics (English)',
    query: 'How does the primary ground (Mutalporuḷ) in Kuṟiñci govern emotional union?',
    queryType: 'How / Process',
    depth: 2,
    focus: 'Relationship',
    corpusName: 'Tolkāppiyam (தொல்காப்பியம்)',
    translation: 'Invariable concomitance between mountainous ecology and emotional interiority (Puṇartal).',
    description: 'Bilingual inquiry into Mutal-Karu-Uri causality in Kuṟiñci montane landscape',
  },
  {
    id: 'prompt-tinai-ta',
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
    id: 'prompt-neytal-en',
    title: 'Neytal Littoral & Varuna (English)',
    query: 'What is the role of Varunan in coastal seashore Neytal poetics?',
    queryType: 'Who / Entity',
    depth: 2,
    focus: 'Character',
    corpusName: 'Tolkāppiyam (தொல்காப்பியம்)',
    translation: 'The coastal deity Varunan presiding over littoral maritime space and pining mood (Iraṅkal).',
    description: 'Deity and aesthetic landscape mapping in ancient littoral poetics',
  },
  {
    id: 'prompt-mullai-ta',
    title: 'Mullai Pastoral & Mayon (முல்லை நில ஒழுக்கம்)',
    query: 'முல்லை நிலத்தின் தெய்வம் மாயோன் மற்றும் அதன் உரிப்பொருள் ஒழுக்கம் யாது?',
    queryType: 'Who / Entity',
    depth: 2,
    focus: 'Relationship',
    corpusName: 'Tolkāppiyam (தொல்காப்பியம்)',
    translation: 'What is the pastoral deity Mayon and its corresponding aesthetic mood (Iruttal)?',
    description: 'Dark-hued deity presiding over pastoral forest ecology and patient waiting',
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
  const [activeGraphContext, setActiveGraphContext] = useState(null);
  const [syncSource, setSyncSource] = useState(null);
  const [activeCategoryFilter, setActiveCategoryFilter] = useState(null);
  const [graphZoom, setGraphZoom] = useState(1);
  const [graphPan, setGraphPan] = useState({ x: 0, y: 0 });
  const [isLoadingGraph, setIsLoadingGraph] = useState(false);
  const [graphError, setGraphError] = useState(null);
  const [isMutatingGraph, setIsMutatingGraph] = useState(false);
  const [mutationError, setMutationError] = useState(null);

  // 4a. Query-Specific Knowledge Graph Subgraph & Full Backend Response State
  const [querySubgraph, setQuerySubgraph] = useState(null);
  const [isQueryGraphActive, setIsQueryGraphActive] = useState(false);
  const [graphVersion, setGraphVersion] = useState(0);
  const [rawBackendResponse, setRawBackendResponse] = useState(null);
  const queryExecutionTokenRef = useRef(0);

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

  // Knowledge Graph Proof Trace Focus State & Insufficient Evidence State
  const [isShowingProofTrace, setIsShowingProofTrace] = useState(false);
  const [insufficientEvidence, setInsufficientEvidence] = useState(false);

  // 8. Final Answer & Justification State (Starts null in clean idle state)
  const [finalAnswer, setFinalAnswer] = useState(null);

  // 8a. Real-Time Dynamic Confidence Score Validation State
  const [serverConfidenceOverride, setServerConfidenceOverride] = useState(null);

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

  // Live Initialization: Fetch corpus info, statistics, health, dashboard summary, and unified system status
  const loadLiveInitialData = useCallback(async (externalSignal = null) => {
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
      const [statsResult, healthResult, corpusResult, dashboardResult, statusResult] = await Promise.allSettled([
        getGraphStatistics({ signal: externalSignal }),
        getGraphHealth({ signal: externalSignal }),
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

      if (statusResult.status === 'fulfilled' && statusResult.value?.data) {
        setSystemStatus(statusResult.value.data);
      } else if (statusResult.status === 'rejected') {
        setSystemStatusError(statusResult.reason?.message || 'Unified system status probe failed');
      }
    } catch (err) {
      if (err.name === 'AbortError') return;
      setStatsError(err.message || 'Initialization error');
    } finally {
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

  // 8b. Dynamically calculated confidence score derived reactively via useMemo
  const dynamicCalculatedConfidence = useMemo(() => {
    return calculateClientConfidence({
      query: queryText,
      evidenceRecords,
      selectedEvidenceId,
      graphNodes,
      selectedGraphNodeId,
      reasoningStages,
      validationResults,
      finalAnswer,
      tinai: filterTinai !== 'all' ? filterTinai : null,
      insufficientEvidence,
    });
  }, [
    queryText,
    evidenceRecords,
    selectedEvidenceId,
    graphNodes,
    selectedGraphNodeId,
    reasoningStages,
    validationResults,
    finalAnswer,
    filterTinai,
    insufficientEvidence,
  ]);

  const confidenceEvaluation = serverConfidenceOverride || dynamicCalculatedConfidence;
  const setConfidenceEvaluation = setServerConfidenceOverride;

  // Compute dynamic currentQuery context object derived purely from active inquiry & real results
  const currentQuery = useMemo(() => {
    const topSource = finalAnswer?.keySources?.[0];

    // Compute ontological triples directly from the query-relevant knowledge graph links
    const triples = (graphEdges || []).slice(0, 10).map((edge) => {
      const srcId = typeof edge.source === 'object' ? (edge.source?.id || edge.source?.label) : edge.source;
      const tgtId = typeof edge.target === 'object' ? (edge.target?.id || edge.target?.label) : edge.target;
      const srcNode = graphNodes.find((n) => n.id === srcId);
      const tgtNode = graphNodes.find((n) => n.id === tgtId);
      return {
        subject: srcNode?.label || srcNode?.tamilLabel || srcId || 'Entity',
        predicate: edge.type || edge.relation || edge.label || 'RELATED_TO',
        object: tgtNode?.label || tgtNode?.tamilLabel || tgtId || 'Entity',
      };
    });

    const langInfo = detectQueryLanguage(queryText);

    return {
      id: 'active-session-query',
      verseId: topSource?.sutra || topSource?.id || 'Tolkāppiyam',
      corpus: 'Tolkāppiyam (Poruḷatikāram)',
      tamilText: queryText,
      detectedLanguage: langInfo,
      domain: focus || 'Tiṇai Eco-Psychology & Ontological Semiotics',
      hypothesis: queryText ? `Inquiry into canonical Tamil poetics: "${queryText.slice(0, 70)}..."` : '',
      hetu: 'Grounding via Classical Tamil morpho-semantic rules and multi-channel Hybrid RAG evidence',
      vyapti: 'Universal concomitance between spatio-temporal signifiers and emotional interiority',
      upanaya: 'Case subsumption evaluated against canonical Tolkāppiyam verses',
      nigamana: finalAnswer?.englishAnswer || 'Awaiting evidence-grounded inference execution',
      confidenceEvaluation,
      confidenceScore: confidenceEvaluation?.confidenceScore ?? (typeof finalAnswer?.confidenceScore === 'number' ? finalAnswer.confidenceScore : 0.0),
      confidencePercentage: confidenceEvaluation?.confidencePercentage ?? 0,
      confidenceStars: confidenceEvaluation?.confidenceStars ?? (typeof finalAnswer?.starsCount === 'number' ? finalAnswer.starsCount : 0.0),
      confidenceLevel: confidenceEvaluation?.confidenceLevel ?? 'INSUFFICIENT',
      neuralConfidence: confidenceEvaluation?.confidenceScore ?? (typeof finalAnswer?.confidenceScore === 'number' ? finalAnswer.confidenceScore : 0.0),
      symbolicValidity: validationResults?.symbolicValidity || 'Awaiting Epistemic Verification',
      pramana: validationResults?.pramana || 'Pratyakṣa + Śabda + Anumāna',
      hetvabhasaCheck: validationResults?.hetvabhasaCheck || 'Not Evaluated',
      reasoningStages: reasoningStages,
      triples: triples,
    };
  }, [queryText, focus, finalAnswer, validationResults, reasoningStages, graphEdges, graphNodes, confidenceEvaluation]);

  /**
   * Recalculates dynamic confidence across evidence relevance, source provenance,
   * retrieval strength, premise support, reasoning consistency, and validation status.
   */
  const recalculateConfidence = useCallback(
    (overrides = null) => {
      if (overrides) {
        const activeEvidence = overrides.evidenceRecords || evidenceRecords;
        const res = calculateClientConfidence({
          query: overrides.queryText || queryText,
          evidenceRecords: activeEvidence,
          selectedEvidenceId: overrides.selectedEvidenceId !== undefined ? overrides.selectedEvidenceId : selectedEvidenceId,
          graphNodes: overrides.graphNodes || graphNodes,
          selectedGraphNodeId: overrides.selectedGraphNodeId !== undefined ? overrides.selectedGraphNodeId : selectedGraphNodeId,
          reasoningStages: overrides.reasoningStages || reasoningStages,
          validationResults: overrides.validationResults || validationResults,
          finalAnswer: overrides.finalAnswer || finalAnswer,
          tinai: overrides.tinai || (filterTinai !== 'all' ? filterTinai : null),
          insufficientEvidence: overrides.insufficientEvidence ?? (insufficientEvidence || activeEvidence.length === 0 || finalAnswer?.status === 'insufficient_evidence'),
        });
        setServerConfidenceOverride(res);
        return res;
      }
      setServerConfidenceOverride(null);
      return dynamicCalculatedConfidence;
    },
    [
      queryText,
      evidenceRecords,
      selectedEvidenceId,
      graphNodes,
      selectedGraphNodeId,
      reasoningStages,
      validationResults,
      finalAnswer,
      filterTinai,
      insufficientEvidence,
      dynamicCalculatedConfidence,
    ]
  );

  /**
   * Strictly synchronizes mutations with Neo4j Aura before updating frontend state.
   * Pattern:
   * Neo4j mutation -> confirmed DB response -> fresh Neo4j query -> updated graph response -> React state -> D3.js.
   * Never updates visualization optimistically before Neo4j confirms the operation.
   */
  const mutateKnowledgeGraph = useCallback(
    async ({
      action,
      entity = null,
      relationship = null,
      concept = null,
      evidence = null,
      query = null,
      hops = null,
    } = {}) => {
      setIsMutatingGraph(true);
      setMutationError(null);

      try {
        const activeQ = query !== null ? query : (queryText || '');
        const res = await graphApi.mutateGraph({
          action,
          entity,
          relationship,
          concept,
          evidence,
          query: activeQ,
          hops: hops || depth || 2,
        });

        const resData = res?.data || res;
        const freshNodes = resData?.nodes || [];
        const freshRels = resData?.relationships || resData?.edges || [];

        // Atomically normalize and commit the fresh Neo4j subgraph
        if (freshNodes.length > 0) {
          const normalizedGraph = normalizeGraphData({
            nodes: freshNodes,
            relationships: freshRels,
          });
          setGraphNodes(normalizedGraph.nodes);
          setGraphEdges(normalizedGraph.links);
          setQuerySubgraph({
            nodes: normalizedGraph.nodes,
            links: normalizedGraph.links,
            stats: normalizedGraph.stats,
            query: activeQ,
            timestamp: Date.now(),
          });
          if (normalizedGraph.nodes.length > 0) {
            setSelectedGraphNodeId(normalizedGraph.nodes[0].id);
          }
        }
        setGraphVersion(Date.now());
        return res;
      } catch (err) {
        console.error('Knowledge Graph mutation failed in Neo4j Aura:', err);
        const errMsg = err?.message || 'Failed to apply mutation to Neo4j Aura';
        setMutationError(errMsg);
        throw err;
      } finally {
        setIsMutatingGraph(false);
      }
    },
    [queryText, depth]
  );

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

    // Track execution generation to eliminate race conditions between rapid queries
    const currentToken = ++queryExecutionTokenRef.current;

    // ATOMICALLY CLEAR prior query-specific graph and reasoning state immediately
    // so users never see a mixture of previous and current query results
    setIsQueryGraphActive(true);
    setGraphNodes([]);
    setGraphEdges([]);
    setSelectedGraphNodeId(null);
    setSelectedProofNodeId(null);
    setProofNodes([]);
    setProofEdges([]);
    setProofSteps([]);
    setProofTraceData(null);
    setEvidenceRecords([]);
    setSelectedEvidenceId(null);
    setQuerySubgraph(null);
    setRawBackendResponse(null);
    setGraphVersion(Date.now());
    setIsLoadingGraph(true);

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
    };

    const detectedLang = detectQueryLanguage(cleanQuery);

    try {
      // 1. Execute retrieval pipeline (Hybrid Search & Grounded Answer Generation)
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
          originalQuery: cleanQuery,
          detectedLanguage: detectedLang,
          topK,
          depth: depth || 2,
          filters: activeFilters,
          signal: controller.signal,
          timeoutMs: 35000,
        }),
      ]);

      if (queryExecutionTokenRef.current !== currentToken) {
        // Query was superseded by a newer submission; ignore stale payload
        return;
      }

      // Check if both primary retrieval calls failed
      if (searchResult.status === 'rejected' && answerResult.status === 'rejected') {
        const primaryErr = searchResult.reason || answerResult.reason || new Error('Search request failed');
        throw primaryErr;
      }

      // 2. Determine relevant entities and evidence returned by retrieval pipeline
      const searchData = searchResult.status === 'fulfilled'
        ? (searchResult.value?.data || searchResult.value || {})
        : {};
      const answerData = answerResult.status === 'fulfilled'
        ? (answerResult.value?.data || answerResult.value || {})
        : {};

      const searchItems = searchData.ranked_results || searchData.results || searchData.passages || [];
      const answerItems = answerData.retrieved_evidence || answerData.evidence || answerData.passages || [];
      const items = Array.isArray(answerItems) && answerItems.length > 0
        ? answerItems
        : (Array.isArray(searchItems) ? searchItems : []);

      // Extract unique entities, concepts, passages, and literary sources directly from retrieved evidence
      const relevantEntities = Array.from(new Set(
        items.flatMap((p) => p.entities || p.entity_names || []).filter(Boolean)
      ));
      const relevantConcepts = Array.from(new Set(
        items.flatMap((p) => p.concepts || []).filter(Boolean)
      ));
      const relevantPassages = Array.from(new Set(
        items.map((p) => p.passage_id || p.id).filter(Boolean)
      ));
      const relevantSources = Array.from(new Set(
        items.map((p) => p.source || p.reference || p.work).filter(Boolean)
      ));
      const evidenceCount = items.length;

      // 3. Directly retrieve the corresponding Neo4j subgraph using the determined entities & evidence
      // First check if answerData from the Adaptive Graph-RAG pipeline already contains the authoritative attributed graph
      const pipelineGraph = answerData?.knowledge_graph || answerData?.knowledgeGraph || answerData?.neo4j_graph;
      let rawGraphNodes = [];
      let rawGraphEdges = [];
      let epistemicContext = null;
      let graphMeta = {
        query: cleanQuery,
        node_count: 0,
        relationship_count: 0,
        literary_sources: relevantSources.length > 0 ? relevantSources : ['Tolkāppiyam (தொல்காப்பியம்)'],
        evidence_count: evidenceCount,
      };

      if (pipelineGraph && Array.isArray(pipelineGraph.nodes) && pipelineGraph.nodes.length > 0) {
        rawGraphNodes = pipelineGraph.nodes;
        rawGraphEdges = Array.isArray(pipelineGraph.relationships)
          ? pipelineGraph.relationships
          : (Array.isArray(pipelineGraph.edges) ? pipelineGraph.edges : []);
        epistemicContext = pipelineGraph.epistemic_context || null;
        if (pipelineGraph.metadata) {
          graphMeta = { ...graphMeta, ...pipelineGraph.metadata };
        }
      } else {
        try {
          const graphRes = await graphApi.queryGraph({
            query: cleanQuery,
            entities: relevantEntities,
            concepts: relevantConcepts,
            passages: relevantPassages,
            evidence: items.map((p) => ({
              id: p.passage_id || p.id,
              entities: p.entities || [],
              concepts: p.concepts || [],
              source: p.source || p.reference || p.work,
              tinai: p.tinai,
            })),
            seed_ids: Array.from(new Set([...relevantEntities, ...relevantConcepts, ...relevantPassages])),
            depth: depth || 2,
            limit: 150,
            signal: controller.signal,
            timeoutMs: 25000,
          });

          if (queryExecutionTokenRef.current === currentToken && graphRes) {
            const gData = graphRes?.data || graphRes;
            epistemicContext = gData.epistemic_context || null;
            if (Array.isArray(gData.nodes)) {
              rawGraphNodes = gData.nodes;
            }
            const gRels = Array.isArray(gData.relationships)
              ? gData.relationships
              : (Array.isArray(gData.edges) ? gData.edges : []);
            rawGraphEdges = gRels;
            if (gData.metadata) {
              graphMeta = { ...graphMeta, ...gData.metadata };
            }
          }
        } catch (graphErr) {
          console.warn('Query-driven Neo4j subgraph retrieval failed:', graphErr);
        }
      }

      if (queryExecutionTokenRef.current !== currentToken) {
        return;
      }

      const elapsedMs = Math.round(performance.now() - startTime);
      clearWorkflowTimers();
      setCurrentWorkflowStageIndex(4);
      setWorkflowProgressPercent(100);

      // 4. Atomically commit the query-specific graph state (or clean empty state)
      // Never keeps unrelated nodes from previous queries unless also returned by new Neo4j query
      let normalizedGraph = {
        nodes: [],
        links: [],
        stats: { nodeCount: 0, edgeCount: 0 },
      };

      if (rawGraphNodes.length > 0) {
        normalizedGraph = normalizeGraphData({
          nodes: rawGraphNodes,
          relationships: rawGraphEdges,
        });

        setGraphNodes(normalizedGraph.nodes);
        setGraphEdges(normalizedGraph.links);
        setQuerySubgraph({
          nodes: normalizedGraph.nodes,
          links: normalizedGraph.links,
          stats: normalizedGraph.stats,
          query: cleanQuery,
          metadata: {
            ...graphMeta,
            node_count: normalizedGraph.nodes.length,
            relationship_count: normalizedGraph.links.length,
            literary_sources: graphMeta.literary_sources || relevantSources,
            evidence_count: evidenceCount,
          },
          literarySources: graphMeta.literary_sources || relevantSources,
          evidenceCount: evidenceCount,
          timestamp: Date.now(),
        });
        setSelectedGraphNodeId(null);
      } else {
        // Complete clean replacement: Query B shows 0 nodes if not matched, never keeps Query A's nodes
        setGraphNodes([]);
        setGraphEdges([]);
        setQuerySubgraph({
          nodes: [],
          links: [],
          stats: { nodeCount: 0, edgeCount: 0 },
          query: cleanQuery,
          metadata: {
            ...graphMeta,
            node_count: 0,
            relationship_count: 0,
            literary_sources: relevantSources,
            evidence_count: evidenceCount,
          },
          literarySources: relevantSources,
          evidenceCount: evidenceCount,
          timestamp: Date.now(),
        });
        setSelectedGraphNodeId(null);
      }
      setGraphVersion(Date.now());
      setIsLoadingGraph(false);

      const isInsufficient = Boolean(
        answerData.insufficient_evidence ||
        answerData.insufficientEvidence ||
        (answerData.reasoning_metadata?.is_sufficient === false) ||
        (answerData.reasoningMetadata?.is_sufficient === false) ||
        (items.length === 0)
      );
      const generatedFinalAnswer = answerData.final_answer || answerData.finalAnswer || {};
      const reasoningMetadata = answerData.reasoning_metadata || answerData.reasoningMetadata || {};
      const retrievalStats = answerData.retrieval_stats || searchData.retrieval_stats || answerData.retrievalStats || searchData.retrievalStats || {};
      const targetTinai = filterTinai !== 'all' ? filterTinai : (reasoningMetadata.tinai || 'Kuṟiñci');

      // Preserve complete backend response in application state
      let proofResultData = null;
      let fallacyResultData = null;
      let deduceResultData = null;

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
          pipelineVersion: reasoningMetadata.pipeline_version || reasoningMetadata.pipelineVersion || '1.0.0',
          provider: reasoningMetadata.provider || 'openrouter',
          model: reasoningMetadata.model || 'unknown',
          mode: searchMode,
          topK,
          retrievalStats,
        });

        setFinalAnswer({
          status: 'insufficient_evidence',
          tamilAnswer: generatedFinalAnswer.tamilAnswer || generatedFinalAnswer.tamil_answer || 'தீர்மானிக்கப் போதுமான தொல்காப்பியச் சான்றுகள் கிடைக்கவில்லை.',
          englishAnswer: generatedFinalAnswer.englishAnswer || generatedFinalAnswer.english_answer || 'Insufficient canonical evidence retrieved to answer query without speculation.',
          subtitle: generatedFinalAnswer.subtitle || (reasoningMetadata.insufficient_reason || reasoningMetadata.insufficientReason ? `Evidence threshold unmet: ${reasoningMetadata.insufficient_reason || reasoningMetadata.insufficientReason}` : 'Epistemic validation requires additional primary sources.'),
          confidenceScore: 0.0,
          starsCount: 0.0,
          verdictStatus: generatedFinalAnswer.verdictStatus || generatedFinalAnswer.verdict_status || 'Insufficient Canonical Evidence (போதிய சான்றுகள் இல்லை)',
          justificationTamil: generatedFinalAnswer.justificationTamil || generatedFinalAnswer.justification_tamil || 'தொல்காப்பிய மூல நூல்களில் வினவப்பட்ட கருதுகோளுக்குப் போதிய சான்றுகள் இல்லை.',
          justificationEnglish: generatedFinalAnswer.justificationEnglish || generatedFinalAnswer.justification_english || 'Retrieved canonical evidence did not meet the required relevance or count criteria. Speculative answer generation was blocked.',
          keySources: generatedFinalAnswer.keySources || generatedFinalAnswer.key_sources || [],
        });

        const insConf = calculateClientConfidence({
          query: cleanQuery,
          evidenceRecords: mappedRecords,
          selectedEvidenceId: mappedRecords[0]?.id || null,
          graphNodes: rawGraphNodes,
          insufficientEvidence: true,
          tinai: targetTinai,
        });
        setConfidenceEvaluation(insConf);

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
        const insProofData = {
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
        };
        setProofTraceData(insProofData);
        proofResultData = insProofData;

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
            fallacyResultData = valRes.data;
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
          tamilAnswer: generatedFinalAnswer.tamilAnswer || generatedFinalAnswer.tamil_answer || (topItem ? topItem.tamilText : ''),
          englishAnswer: generatedFinalAnswer.englishAnswer || generatedFinalAnswer.english_answer || (topItem ? topItem.translation : ''),
          subtitle: generatedFinalAnswer.subtitle || `Retrieved via ${searchMode.toUpperCase()} mode: Grounded on ${items.length} canonical verses.`,
          confidenceScore: typeof generatedFinalAnswer.confidenceScore === 'number'
            ? generatedFinalAnswer.confidenceScore
            : (typeof generatedFinalAnswer.confidence_score === 'number'
              ? generatedFinalAnswer.confidence_score
              : (typeof answerData.confidence_info?.confidenceScore === 'number'
                ? answerData.confidence_info.confidenceScore
                : (typeof answerData.confidence_info?.confidence_score === 'number'
                  ? answerData.confidence_info.confidence_score
                  : (topItem?.confidence ?? 0.95)))),
          starsCount: typeof generatedFinalAnswer.starsCount === 'number'
            ? generatedFinalAnswer.starsCount
            : (typeof generatedFinalAnswer.stars_count === 'number'
              ? generatedFinalAnswer.stars_count
              : Number(((topItem?.confidence ?? 0.95) * 5).toFixed(1))),
          justificationTamil: generatedFinalAnswer.justificationTamil || generatedFinalAnswer.justification_tamil || generatedFinalAnswer.tamilJustification || generatedFinalAnswer.tamil_justification || '',
          justificationEnglish: generatedFinalAnswer.justificationEnglish || generatedFinalAnswer.justification_english || generatedFinalAnswer.englishJustification || generatedFinalAnswer.english_justification || '',
          keySources: (generatedFinalAnswer.keySources && generatedFinalAnswer.keySources.length > 0)
            ? generatedFinalAnswer.keySources
            : ((generatedFinalAnswer.key_sources && generatedFinalAnswer.key_sources.length > 0)
              ? generatedFinalAnswer.key_sources
              : (answerData.sources || mappedRecords.map((m) => ({
                  id: m.id,
                  label: m.code,
                  sutra: m.reference,
                  section: m.section,
                  topic: m.badges[0]?.label || 'Evidence',
                  score: m.confidenceFormatted,
                })))),
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

          if (queryExecutionTokenRef.current !== currentToken) {
            return;
          }

          if (proofResult.status === 'fulfilled' && proofResult.value?.data) {
            const ptData = proofResult.value.data;
            setProofTraceData(ptData);
            proofResultData = ptData;
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
            const insData = {
              status: 'INSUFFICIENT_EVIDENCE',
              insufficient_evidence: true,
              is_valid: false,
              reason: 'Proof trace generation failed or evidence is insufficient to complete the deduction chain.',
              missing_requirements: ['Grounded canonical sūtras with verifiable Vyāpti'],
              steps: [],
              nodes: [],
              edges: [],
              traceable_paths: [],
            };
            setProofTraceData(insData);
            proofResultData = insData;
          }

          if (fallacyResult.status === 'fulfilled' && (fallacyResult.value?.data || fallacyResult.value)) {
            const fData = fallacyResult.value?.data || fallacyResult.value;
            setValidationResults(fData);
            fallacyResultData = fData;
          }

          if (deduceResult.status === 'fulfilled' && (deduceResult.value?.data?.reasoningStages || deduceResult.value?.data?.stages || deduceResult.value?.reasoningStages)) {
            const dData = deduceResult.value?.data || deduceResult.value;
            const stages = dData.reasoningStages || dData.stages || [];
            setReasoningStages(stages);
            setReasoningStatus(stages.length > 0 ? 'success' : 'empty');
            setReasoningError(null);
            setSelectedStageIndex(0);
            deduceResultData = dData;
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

        const serverConfidence =
          deduceResultData?.confidenceEvaluation ||
          fallacyResultData?.confidenceEvaluation ||
          answerData.confidence_info?.confidenceEvaluation ||
          answerData.reasoning_metadata?.confidence_evaluation;

        if (serverConfidence) {
          setConfidenceEvaluation(serverConfidence);
        } else {
          recalculateConfidence({
            queryText: cleanQuery,
            evidenceRecords: mappedRecords,
            selectedEvidenceId: mappedRecords[0]?.id || null,
            graphNodes: rawGraphNodes,
            selectedGraphNodeId: epistemicContext?.primary_entity_id || (rawGraphNodes[0]?.id || null),
            reasoningStages: deduceResultData?.reasoningStages || [],
            validationResults: fallacyResultData || null,
            tinai: targetTinai,
          });
        }
      }

      // PRESERVE COMPLETE BACKEND RESPONSE IN APPLICATION STATE
      const fullResponsePayload = {
        query: cleanQuery,
        timestamp: new Date().toISOString(),
        executionDurationMs: elapsedMs,
        searchData,
        answerData,
        groundedGraph: {
          nodes: rawGraphNodes,
          relationships: rawGraphEdges,
          normalized: normalizedGraph,
          epistemicContext,
        },
        proofTrace: proofResultData,
        fallacyValidation: fallacyResultData,
        deduceReasoning: deduceResultData,
        retrievalStats,
        reasoningMetadata,
        isInsufficient,
      };
      setRawBackendResponse(fullResponsePayload);

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
      // Proactively ensure runtime cache is cleared after every response generated
      clearCache().catch((err) => {
        console.debug('Runtime cache clearance background warning:', err);
      });
    }
  }, [queryText, depth, queryType, searchMode, topK, filterTinai, filterSection, recalculateConfidence, setConfidenceEvaluation]);

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
    setConfidenceEvaluation(calculateClientConfidence({ evidenceRecords: [] }));

    // Reset Graph View
    setSelectedGraphNodeId(null);
    setActiveCategoryFilter(null);
    setGraphZoom(1);
    setGraphPan({ x: 0, y: 0 });
    setIsShowingProofTrace(false);
    setQuerySubgraph(null);
    setIsQueryGraphActive(false);
    setRawBackendResponse(null);
    setGraphVersion(Date.now());
  }, [setConfidenceEvaluation]);

  // Explicit Cache Clearance Handler
  const clearAllCaches = useCallback(async () => {
    try {
      await clearCache();
    } catch (e) {
      console.warn('Backend cache clearance warning:', e);
    }
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

  /**
   * Universal bidirectional synchronization handler.
   * Atomically connects Query Center results (retrieved passages, entities, concepts,
   * events, evidence nodes, premises, rules, conclusions) and D3 Knowledge Graph nodes.
   * Guarantees zero duplicate API calls and synchronized React/D3 state.
   */
  const selectSynchronizedItem = useCallback((target, source = 'query_center') => {
    setSyncSource(source);
    if (!target) {
      setSelectedGraphNodeId(null);
      setSelectedEvidenceId(null);
      setSelectedProofNodeId(null);
      setActiveGraphContext(null);
      return;
    }

    // Build pooled candidate nodes from all active stores
    const candidateNodes = [
      ...(graphNodes || []),
      ...(proofNodes || []),
      ...(evidenceRecords || []).map((ev, i) => ({
        id: ev.passageId || ev.id,
        code: ev.code || `E${i + 1}`,
        label: ev.reference || ev.passageId || ev.id,
        name: ev.work || ev.reference || ev.id,
        tamilLabel: ev.tamilText || ev.text || ev.reference,
        type: 'Evidence',
        category: 'Evidence',
        passageId: ev.passageId || ev.id,
        isEvidenceRecord: true,
        source: ev.source || 'Tolkāppiyam',
        properties: { ...ev },
      })),
    ];

    const matchedNode = findNodeByStableId(candidateNodes, target);
    const resolvedGraphId = matchedNode
      ? matchedNode.id
      : (typeof target === 'string' ? target : (target.id || target.code || target.passageId));

    // 1. Synchronize Graph Node ID
    setSelectedGraphNodeId(resolvedGraphId);

    // 2. Resolve Associated Evidence
    const associatedEvList = matchedNode
      ? findAssociatedEvidenceForNode(matchedNode, evidenceRecords)
      : (typeof target === 'object' && target.id ? [target] : []);

    let targetEvidenceId = null;
    if (associatedEvList.length > 0) {
      targetEvidenceId = associatedEvList[0].id;
      setSelectedEvidenceId(associatedEvList[0].id);
    } else if (typeof target === 'string') {
      const directEv = evidenceRecords.find(
        (e) => e.id === target || e.code === target || e.passageId === target
      );
      if (directEv) {
        targetEvidenceId = directEv.id;
        setSelectedEvidenceId(directEv.id);
      }
    }

    // 3. Resolve Proof Step / Node ID (E1, P1, R1, I1, C1)
    let targetProofId = null;
    const testCode = String(matchedNode?.code || target?.code || target || '').toUpperCase();
    if (['E1', 'E2', 'E3', 'P1', 'P2', 'R1', 'I1', 'C1'].includes(testCode)) {
      targetProofId = testCode;
    } else if (matchedNode?.id && ['E1', 'E2', 'E3', 'P1', 'P2', 'R1', 'I1', 'C1'].includes(String(matchedNode.id).toUpperCase())) {
      targetProofId = String(matchedNode.id).toUpperCase();
    }
    if (targetProofId) {
      setSelectedProofNodeId(targetProofId);
    } else if (matchedNode) {
      setSelectedProofNodeId(matchedNode.id);
    }

    // 4. Synchronize Reasoning Stage (only from external sources like Query Center or Graph, not when user deliberately selects a reasoning stage)
    if (source !== 'reasoning' && (targetEvidenceId || targetProofId)) {
      const mIdx = reasoningStages.findIndex((s) => {
        const link = s.linkedEvidenceId || (Array.isArray(s.linkedEvidenceIds) && s.linkedEvidenceIds[0]);
        return link === targetEvidenceId || link === targetProofId || link === resolvedGraphId;
      });
      if (mIdx !== -1) {
        setSelectedStageIndex(mIdx);
      }
    }

    // 5. Build and commit rich active graph context for Query Center
    if (matchedNode) {
      const neighborInfo = getInducedSubgraphNeighborhood(matchedNode.id, graphEdges || [], 1);
      const connectedNeighbors = candidateNodes.filter((n) => neighborInfo.directNeighborIds.has(String(n.id)));

      setActiveGraphContext({
        node: matchedNode,
        id: matchedNode.id,
        label: matchedNode.label || matchedNode.id,
        tamilLabel: matchedNode.tamilLabel || matchedNode.tamil_label || matchedNode.label,
        transliteration: matchedNode.transliteration || '',
        type: matchedNode.type || matchedNode.category || 'Entity',
        category: matchedNode.category || matchedNode.type || 'Entity',
        hierarchyLevel: matchedNode.hierarchyLevel || matchedNode.hierarchy_level || 'L5',
        source: matchedNode.source || matchedNode.citation || 'Tolkāppiyam',
        citation: matchedNode.citation || matchedNode.source || '',
        description: matchedNode.description || matchedNode.text || matchedNode.english || '',
        associatedEvidence: associatedEvList,
        connectedEdgesCount: neighborInfo.inducedEdgeIds.size,
        connectedNeighbors: connectedNeighbors.map((n) => ({
          id: n.id,
          label: n.label || n.id,
          type: n.type || 'Entity',
          transliteration: n.transliteration || '',
        })),
        sourceOrigin: source,
        timestamp: Date.now(),
      });
    } else if (typeof target === 'object') {
      setActiveGraphContext({
        node: target,
        id: target.id || target.code || 'custom_node',
        label: target.label || target.name || target.code || target.id,
        tamilLabel: target.tamilLabel || target.tamilText || target.tamil_label || target.label,
        transliteration: target.transliteration || '',
        type: target.type || target.category || 'Item',
        category: target.category || target.type || 'Item',
        source: target.source || target.reference || 'Tolkāppiyam',
        citation: target.citation || target.reference || '',
        description: target.description || target.text || target.translation || '',
        associatedEvidence: associatedEvList,
        connectedEdgesCount: 0,
        connectedNeighbors: [],
        sourceOrigin: source,
        timestamp: Date.now(),
      });
    } else {
      setActiveGraphContext(null);
    }
  }, [graphNodes, proofNodes, evidenceRecords, graphEdges, reasoningStages]);

  const clearActiveGraphContext = useCallback(() => {
    selectSynchronizedItem(null, 'reset');
  }, [selectSynchronizedItem]);

  // Cross-highlighting handlers linking Evidence, Graph, Proof DAG, and Reasoning Stages
  const handleSetSelectedEvidenceId = useCallback((evidenceId) => {
    selectSynchronizedItem(evidenceId, 'query_center');
  }, [selectSynchronizedItem]);

  const handleSetSelectedProofNodeId = useCallback((nodeId) => {
    selectSynchronizedItem(nodeId, 'proof_trace');
  }, [selectSynchronizedItem]);

  const handleSetSelectedStageIndex = useCallback((index) => {
    setSelectedStageIndex(index);
    const stage = reasoningStages[index];
    const linkedEvId = stage?.linkedEvidenceId || (Array.isArray(stage?.linkedEvidenceIds) && stage.linkedEvidenceIds[0]) || null;
    if (linkedEvId) {
      selectSynchronizedItem(linkedEvId, 'reasoning');
    }
  }, [reasoningStages, selectSynchronizedItem]);

  const handleSetSelectedGraphNodeId = useCallback((nodeId) => {
    selectSynchronizedItem(nodeId, 'graph');
  }, [selectSynchronizedItem]);

  const showProofTrace = useCallback(() => {
    setIsShowingProofTrace(true);
  }, []);

  const resetGraph = useCallback(() => {
    setIsShowingProofTrace(false);
    selectSynchronizedItem(null, 'reset');
  }, [selectSynchronizedItem]);

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
    detectedLanguage: currentQuery.detectedLanguage,
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
    selectSynchronizedItem,
    activeGraphContext,
    clearActiveGraphContext,
    syncSource,
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
    // 4b. Dedicated Query Subgraph & Full Backend Response
    querySubgraph,
    isQueryGraphActive,
    graphVersion,
    rawBackendResponse,
    lastBackendResponse: rawBackendResponse,
    // 4c. Authoritative Neo4j Strict Mutation & Synchronization
    isMutatingGraph,
    mutationError,
    mutateKnowledgeGraph,
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
    // 7. Proof Trace DAG & Knowledge Graph Highlighting
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
    // 8a. Real-Time Dynamic Confidence Score Validation
    confidenceEvaluation,
    setConfidenceEvaluation,
    recalculateConfidence,
    CONFIDENCE_LEVELS,
    // 9. Workflow & Live Query State
    isAnalyzing,
    currentWorkflowStageIndex,
    workflowProgressPercent,
    currentWorkflowStage: REASONING_WORKFLOW_STAGES[currentWorkflowStageIndex],
    workflowStages: REASONING_WORKFLOW_STAGES,
    runAnalyze,
    resetToDefault,
    clearAllCaches,
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
