/**
 * Centralized API Client & Service Layer for Classical Tamil Literary Knowledge System.
 *
 * Configured via Vite environment variable `VITE_API_BASE_URL`.
 * Provides:
 *  - Environment-driven base URL resolution (no hardcoded production URLs)
 *  - Standard request utilities with JSON parsing, HTTP error handling, and timeout protection
 *  - Structured error classes (ApiError, TimeoutError, NetworkError)
 *  - Domain-organized API namespaces:
 *      * dashboardApi (analytics, benchmark, KPI metrics)
 *      * graphApi (statistics, health, elements, subgraphs, entity details)
 *      * searchApi (multi-mode search, passages, filters)
 *      * ragApi (hybrid RAG retrieval, grounded answer generation)
 *      * evidenceApi (source-grounded evidence chunks, entity evidence)
 *      * reasoningApi (Pañcāvayava syllogism deduction, Hetvābhāsa fallacy validation, proof trace)
 *      * systemStatusApi (backend health, index status, corpus info)
 *  - Backward-compatible top-level exports for smooth incremental integration.
 */

// =============================================================================
// 1. Environment-Driven Base URL Configuration
// =============================================================================

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');

/**
 * Resolves an API endpoint path into a full or proxy-ready URL.
 *
 * @param {string} endpoint - API path (e.g., '/api/retrieval/answer')
 * @returns {string} Fully qualified or proxy-ready URL
 */
export function buildApiUrl(endpoint) {
  if (!endpoint) return API_BASE_URL || '/';
  if (/^https?:\/\//i.test(endpoint)) return endpoint;
  const cleanPath = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return API_BASE_URL ? `${API_BASE_URL}${cleanPath}` : cleanPath;
}

// =============================================================================
// 2. Structured Error Classes
// =============================================================================

export class ApiError extends Error {
  constructor(message, { status = 500, code = 'API_ERROR', details = {} } = {}) {
    super(message || 'An API error occurred');
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
    this.isApiError = true;
  }
}

export class TimeoutError extends Error {
  constructor(message, { timeoutMs = 15000 } = {}) {
    super(message || `Request timed out after ${timeoutMs / 1000}s`);
    this.name = 'TimeoutError';
    this.timeoutMs = timeoutMs;
    this.isTimeout = true;
    this.code = 'REQUEST_TIMEOUT';
  }
}

export class NetworkError extends Error {
  constructor(message, { originalError = null } = {}) {
    super(message || 'Network connection failed');
    this.name = 'NetworkError';
    this.originalError = originalError;
    this.isNetworkError = true;
    this.code = 'NETWORK_ERROR';
  }
}

// =============================================================================
// 3. Low-level Reusable HTTP Request Utility
// =============================================================================

/**
 * Executes an HTTP request with timeout protection, abort signals, and uniform error normalization.
 *
 * @param {string} endpoint - Relative or absolute endpoint
 * @param {Object} options - Request options
 * @param {string} [options.method='GET'] - HTTP verb
 * @param {Object} [options.headers={}] - Custom headers
 * @param {any} [options.body=null] - Request payload
 * @param {Object} [options.params=null] - URL query parameters
 * @param {AbortSignal} [options.signal=null] - External AbortSignal
 * @param {number} [options.timeoutMs=15000] - Request timeout limit in ms
 * @returns {Promise<any>} Parsed JSON response
 */
export async function apiRequest(endpoint, {
  method = 'GET',
  headers = {},
  body = null,
  params = null,
  signal = null,
  timeoutMs = 15000,
  ...customOptions
} = {}) {
  let targetUrl = buildApiUrl(endpoint);

  // Append query params if provided
  if (params && typeof params === 'object') {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.set(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      targetUrl += (targetUrl.includes('?') ? '&' : '?') + queryString;
    }
  }

  const controller = new AbortController();

  let timeoutId = null;
  if (timeoutMs > 0) {
    timeoutId = setTimeout(() => {
      controller.abort(
        new TimeoutError(`Request to ${endpoint} timed out after ${timeoutMs / 1000}s`, { timeoutMs })
      );
    }, timeoutMs);
  }

  const handleExternalAbort = () => {
    controller.abort(signal?.reason || new Error('Request aborted by caller'));
  };

  if (signal) {
    if (signal.aborted) {
      handleExternalAbort();
    } else {
      signal.addEventListener('abort', handleExternalAbort, { once: true });
    }
  }

  const requestHeaders = {
    'Accept': 'application/json',
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache',
    'Expires': '0',
    ...(body && typeof body === 'object' && !(body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
    ...headers,
  };

  try {
    const response = await fetch(targetUrl, {
      method,
      headers: requestHeaders,
      cache: 'no-store',
      body: body && typeof body === 'object' && !(body instanceof FormData) ? JSON.stringify(body) : body,
      signal: controller.signal,
      ...customOptions,
    });

    const json = await response.json().catch(() => null);

    if (!response.ok || (json && json.success === false)) {
      const errorMsg =
        json?.message ||
        json?.error?.message ||
        json?.error?.details?.message ||
        json?.error ||
        `HTTP Error ${response.status}: ${response.statusText}`;

      const errorCode =
        json?.error_code ||
        json?.error?.code ||
        `HTTP_${response.status}`;

      throw new ApiError(errorMsg, {
        status: response.status,
        code: errorCode,
        details: json?.error?.details || json?.meta || json?.details || {},
      });
    }

    return json;
  } catch (err) {
    if (err instanceof ApiError || err instanceof TimeoutError) {
      throw err;
    }
    if (controller.signal.aborted) {
      const reason = controller.signal.reason;
      if (reason instanceof TimeoutError) {
        throw reason;
      }
      const abortErr = new Error(reason?.message || 'Request cancelled');
      abortErr.name = 'AbortError';
      throw abortErr;
    }
    throw new NetworkError(
      `Failed to connect to backend service at ${targetUrl}. Please verify Flask server is running.`,
      { originalError: err }
    );
  } finally {
    if (timeoutId) clearTimeout(timeoutId);
    if (signal) {
      signal.removeEventListener('abort', handleExternalAbort);
    }
  }
}

// Convenience REST request helpers
export const http = {
  get: (endpoint, options = {}) => apiRequest(endpoint, { ...options, method: 'GET' }),
  post: (endpoint, body, options = {}) => apiRequest(endpoint, { ...options, method: 'POST', body }),
  put: (endpoint, body, options = {}) => apiRequest(endpoint, { ...options, method: 'PUT', body }),
  patch: (endpoint, body, options = {}) => apiRequest(endpoint, { ...options, method: 'PATCH', body }),
  delete: (endpoint, options = {}) => apiRequest(endpoint, { ...options, method: 'DELETE' }),
};

// =============================================================================
// 4. Domain-Organized API Services
// =============================================================================

/**
 * 4.1 Dashboard & Analytics Domain
 */
export const dashboardApi = {
  /**
   * Retrieves benchmark metrics, inference latencies, and density statistics.
   * Endpoint: GET /api/analytics/benchmark
   */
  getBenchmarkMetrics: ({ signal = null, timeoutMs = 10000 } = {}) =>
    http.get('/api/analytics/benchmark', { signal, timeoutMs }),

  /**
   * Retrieves system performance metrics (alias to benchmark).
   * Endpoint: GET /api/analytics/metrics
   */
  getSystemMetrics: ({ signal = null, timeoutMs = 10000 } = {}) =>
    http.get('/api/analytics/metrics', { signal, timeoutMs }),

  /**
   * Retrieves dataset profiling and distribution statistics.
   * Endpoint: GET /api/corpus/statistics
   */
  getDatasetStatistics: ({ signal = null, timeoutMs = 10000 } = {}) =>
    http.get('/api/corpus/statistics', { signal, timeoutMs }),

  /**
   * Retrieves aggregated dashboard summary statistics from canonical Neo4j, KG, and Corpus sources.
   * Endpoint: GET /api/analytics/dashboard
   */
  getDashboardSummary: ({ signal = null, timeoutMs = 10000 } = {}) =>
    http.get('/api/analytics/dashboard', { signal, timeoutMs }),
};

/**
 * 4.2 Knowledge Graph Domain
 */
export const graphApi = {
  /**
   * Retrieves structural graph statistics and layer distributions.
   * Endpoint: GET /api/kg/statistics
   */
  getStatistics: ({ signal = null, timeoutMs = 10000 } = {}) =>
    http.get('/api/kg/statistics', { signal, timeoutMs }),

  /**
   * Retrieves graph health, connectivity, and validation report.
   * Endpoint: GET /api/kg/health
   */
  getHealth: ({ signal = null, timeoutMs = 10000 } = {}) =>
    http.get('/api/kg/health', { signal, timeoutMs }),

  /**
   * Retrieves graph elements (nodes & relationships) for Knowledge Graph visualization.
   * Endpoint: GET /api/kg/graph
   */
  getElements: ({
    centerId = null,
    hops = 2,
    limit = 250,
    source = 'auto',
    includeOntology = true,
    category = null,
    signal = null,
    timeoutMs = 15000,
  } = {}) => {
    const params = {
      source,
      limit,
      hops,
      ...(centerId ? { center_id: centerId } : {}),
      ...(includeOntology ? { include_ontology: 'true' } : {}),
      ...(category ? { category } : {}),
    };
    return http.get('/api/kg/graph', { params, signal, timeoutMs });
  },

  /**
   * Expands a multi-hop subgraph around given node IDs.
   * Endpoint: POST /api/kg/subgraph
   */
  getSubgraph: ({
    nodeIds = [],
    hops = 2,
    limit = 100,
    signal = null,
    timeoutMs = 15000,
  } = {}) =>
    http.post(
      '/api/kg/subgraph',
      { node_ids: nodeIds, hops, limit },
      { signal, timeoutMs }
    ),

  /**
   * Retrieves dynamic query-driven Knowledge Graph subgraph from Neo4j Aura.
   * Endpoint: POST /api/kg/query
   */
  queryGraph: ({
    query = '',
    depth = 2,
    hops = 2,
    limit = 150,
    signal = null,
    timeoutMs = 15000,
  } = {}) =>
    http.post(
      '/api/kg/query',
      {
        query,
        hops: depth || hops,
        limit,
      },
      { signal, timeoutMs }
    ),

  /**
   * Retrieves dynamic query-aware Knowledge Graph subgraph matching user query / hybrid retrieval evidence.
   * Endpoint: POST /api/kg/query-subgraph
   */
  getQuerySubgraph: ({
    query = '',
    seedIds = [],
    passages = [],
    entities = [],
    concepts = [],
    events = [],
    rules = [],
    hops = 2,
    relationshipTypes = null,
    limit = 150,
    includeIsolated = true,
    signal = null,
    timeoutMs = 15000,
  } = {}) =>
    http.post(
      '/api/kg/query-subgraph',
      {
        query,
        seed_ids: seedIds,
        passages,
        entities,
        concepts,
        events,
        rules,
        hops,
        relationship_types: relationshipTypes,
        limit,
        include_isolated: includeIsolated,
      },
      { signal, timeoutMs }
    ),

  /**
   * Retrieves detailed schema, attributes, and neighbors for a single entity.
   * Endpoint: GET /api/kg/entity/<id>
   */
  getEntityDetail: (entityId, { signal = null, timeoutMs = 10000 } = {}) =>
    http.get(`/api/kg/entity/${encodeURIComponent(entityId)}`, { signal, timeoutMs }),

  /**
   * Retrieves directly connected and multi-hop nodes, relationships, directions, and lineage from Neo4j Aura.
   * Endpoint: GET /api/kg/node/<id>/connected
   */
  getNodeConnected: (
    nodeId,
    {
      hops = 1,
      depth = null,
      limit = 150,
      allowedTypes = null,
      excludedTypes = null,
      relationshipTypes = null,
      direction = 'both',
      signal = null,
      timeoutMs = 15000,
    } = {}
  ) => {
    const effectiveHops = depth !== null && depth !== undefined ? depth : hops;
    const params = {
      hops: effectiveHops,
      depth: effectiveHops,
      limit,
      direction,
      ...(allowedTypes
        ? { allowed_types: Array.isArray(allowedTypes) ? allowedTypes.join(',') : allowedTypes }
        : {}),
      ...(excludedTypes
        ? { excluded_types: Array.isArray(excludedTypes) ? excludedTypes.join(',') : excludedTypes }
        : {}),
      ...(relationshipTypes
        ? { rel_types: Array.isArray(relationshipTypes) ? relationshipTypes.join(',') : relationshipTypes }
        : {}),
    };
    return http.get(`/api/kg/node/${encodeURIComponent(nodeId)}/connected`, {
      params,
      signal,
      timeoutMs,
    });
  },

  /**
   * Performs bounded multi-hop traversal with configurable depth, type filters, and parent-child paths.
   * Endpoint: POST /api/kg/node/traverse
   */
  traverseNode: (
    nodeId,
    {
      hops = 2,
      depth = null,
      limit = 150,
      allowedTypes = null,
      excludedTypes = null,
      relationshipTypes = null,
      direction = 'both',
      signal = null,
      timeoutMs = 15000,
    } = {}
  ) =>
    http.post(
      '/api/kg/node/traverse',
      {
        node_id: nodeId,
        hops: depth !== null && depth !== undefined ? depth : hops,
        depth: depth !== null && depth !== undefined ? depth : hops,
        limit,
        direction,
        allowed_types: allowedTypes,
        excluded_types: excludedTypes,
        relationship_types: relationshipTypes,
      },
      { signal, timeoutMs }
    ),

  /**
   * Expands node neighborhood with connected nodes and relationships from Neo4j Aura.
   * Endpoint: POST /api/kg/node/connected
   */
  expandNode: (
    nodeId,
    {
      hops = 1,
      depth = null,
      limit = 150,
      allowedTypes = null,
      excludedTypes = null,
      relationshipTypes = null,
      direction = 'both',
      signal = null,
      timeoutMs = 15000,
    } = {}
  ) =>
    http.post(
      '/api/kg/node/connected',
      {
        node_id: nodeId,
        hops: depth !== null && depth !== undefined ? depth : hops,
        depth: depth !== null && depth !== undefined ? depth : hops,
        limit,
        direction,
        allowed_types: allowedTypes,
        excluded_types: excludedTypes,
        relationship_types: relationshipTypes,
      },
      { signal, timeoutMs }
    ),

  /**
   * Multi-hop path search with propagated path confidence.
   * Endpoint: GET /api/kg/path
   */
  getPath: ({
    sourceId,
    targetId,
    maxHops = 3,
    signal = null,
    timeoutMs = 15000,
  } = {}) =>
    http.get('/api/kg/path', {
      params: { source: sourceId, target: targetId, max_hops: maxHops },
      signal,
      timeoutMs,
    }),

  /**
   * Executes strict mutation on Neo4j Aura and retrieves updated fresh subgraph.
   * Endpoint: POST /api/kg/mutate
   */
  mutateGraph: ({
    action,
    entity = null,
    relationship = null,
    concept = null,
    evidence = null,
    query = '',
    hops = 2,
    limit = 150,
    signal = null,
    timeoutMs = 20000,
  } = {}) =>
    http.post(
      '/api/kg/mutate',
      {
        action,
        entity,
        relationship,
        concept,
        evidence,
        query,
        hops,
        limit,
      },
      { signal, timeoutMs }
    ),

  /**
   * Idempotently upserts an entity into Neo4j Aura and retrieves fresh subgraph.
   * Endpoint: POST /api/kg/entity
   */
  upsertEntity: ({
    entity,
    query = '',
    hops = 2,
    limit = 150,
    signal = null,
    timeoutMs = 20000,
  } = {}) =>
    http.post(
      '/api/kg/entity',
      {
        entity,
        query,
        hops,
        limit,
      },
      { signal, timeoutMs }
    ),

  /**
   * Idempotently upserts a relationship into Neo4j Aura and retrieves fresh subgraph.
   * Endpoint: POST /api/kg/relationship
   */
  upsertRelationship: ({
    relationship,
    query = '',
    hops = 2,
    limit = 150,
    signal = null,
    timeoutMs = 20000,
  } = {}) =>
    http.post(
      '/api/kg/relationship',
      {
        relationship,
        query,
        hops,
        limit,
      },
      { signal, timeoutMs }
    ),
};

/**
 * 4.3 Search Domain
 */
export const searchApi = {
  /**
   * Multi-mode search (hybrid, semantic, bm25, exact) across canonical passages.
   * Endpoint: POST /api/search
   */
  searchPassages: ({
    query = '',
    mode = 'hybrid',
    topK = 5,
    page = 1,
    pageSize = 5,
    includeGraph = true,
    rerank = true,
    filters = {},
    work = null,
    section = null,
    chapter = null,
    tinai = null,
    source = null,
    signal = null,
    timeoutMs = 25000,
  } = {}) => {
    const cleanQuery = (query || '').trim();
    if (!cleanQuery) {
      throw new ApiError('Search query cannot be empty', {
        status: 400,
        code: 'EMPTY_QUERY',
      });
    }

    const mergedFilters = { ...filters };
    if (tinai && tinai !== 'all' && tinai !== 'All') {
      mergedFilters.tinai = tinai;
    }
    if (section && section !== 'all') {
      mergedFilters.section = section;
    }
    if (chapter && chapter !== 'all') {
      mergedFilters.chapter = chapter;
    }

    const payload = {
      query: cleanQuery,
      mode,
      top_k: Math.min(Math.max(parseInt(topK, 10) || 5, 1), 50),
      page: Math.max(parseInt(page, 10) || 1, 1),
      page_size: Math.min(Math.max(parseInt(pageSize, 10) || 5, 1), 50),
      include_graph: Boolean(includeGraph),
      rerank: Boolean(rerank),
      filters: mergedFilters,
      ...(work ? { work } : {}),
      ...(section && section !== 'all' ? { section } : {}),
      ...(chapter && chapter !== 'all' ? { chapter } : {}),
      ...(tinai && tinai !== 'all' && tinai !== 'All' ? { tinai } : {}),
      ...(source ? { source } : {}),
    };

    return http.post('/api/search', payload, { signal, timeoutMs });
  },

  /**
   * Retrieves canonical literary passages / sūtras with filtering and pagination.
   * Endpoint: GET /api/corpus/passages
   */
  getPassages: ({
    section = null,
    chapter = null,
    tinai = null,
    page = 1,
    pageSize = 10,
    signal = null,
    timeoutMs = 15000,
  } = {}) => {
    const params = {
      page,
      page_size: pageSize,
      ...(section ? { section } : {}),
      ...(chapter ? { chapter } : {}),
      ...(tinai && tinai !== 'All' ? { tinai } : {}),
    };
    return http.get('/api/corpus/passages', { params, signal, timeoutMs });
  },

  /**
   * Retrieves single passage details by ID.
   * Endpoint: GET /api/corpus/passages/<id>
   */
  getPassageById: (id, { signal = null, timeoutMs = 10000 } = {}) =>
    http.get(`/api/corpus/passages/${encodeURIComponent(id)}`, { signal, timeoutMs }),

  /**
   * Preprocesses a Tamil or multilingual query to extract channel payloads.
   * Endpoint: POST /api/query/preprocess
   */
  preprocessQuery: ({ query = '', focus = 'Relationship', signal = null, timeoutMs = 10000 } = {}) =>
    http.post('/api/query/preprocess', { query, focus }, { signal, timeoutMs }),
};

/**
 * 4.4 RAG (Retrieval-Augmented Generation) Domain
 */
export const ragApi = {
  /**
   * High-level grounded answer generation combining 3-channel retrieval + LLM gating.
   * Endpoint: POST /api/retrieval/answer
   */
  generateGroundedAnswer: ({
    query = '',
    queryText = '',
    originalQuery = '',
    original_query = '',
    detectedLanguage = null,
    detected_language = null,
    topK = 5,
    depth = 2,
    maxContextChars = 4000,
    maxRelationships = 8,
    minRelevanceThreshold = 0.30,
    minEvidenceCount = 1,
    filters = {},
    signal = null,
    timeoutMs = 35000,
  } = {}) => {
    const cleanQuery = (query || queryText || '').trim();
    if (!cleanQuery) {
      throw new ApiError('Query parameter cannot be empty', {
        status: 400,
        code: 'INVALID_QUERY',
      });
    }

    const payload = {
      query: cleanQuery,
      original_query: (originalQuery || original_query || cleanQuery).trim(),
      detected_language: detectedLanguage || detected_language || null,
      top_k: Math.min(Math.max(parseInt(topK, 10) || 5, 1), 20),
      max_graph_depth: Math.min(Math.max(parseInt(depth, 10) || 2, 1), 4),
      max_context_chars: Math.min(Math.max(parseInt(maxContextChars, 10) || 4000, 500), 12000),
      max_relationships: Math.min(Math.max(parseInt(maxRelationships, 10) || 8, 1), 25),
      min_relevance_threshold: Math.min(Math.max(parseFloat(minRelevanceThreshold) || 0.30, 0.0), 1.0),
      min_evidence_count: Math.min(Math.max(parseInt(minEvidenceCount, 10) || 1, 1), 10),
      filters,
    };

    return http.post('/api/retrieval/answer', payload, { signal, timeoutMs });
  },

  /**
   * Explicitly clears runtime passage graph caches and transient buffers on backend.
   * Endpoint: POST /api/retrieval/clear-cache
   */
  clearCache: ({ signal = null, timeoutMs = 10000 } = {}) => {
    return http.post('/api/retrieval/clear-cache', {}, { signal, timeoutMs });
  },

  /**
   * 3-channel Hybrid RAG retrieval without text generation.
   * Endpoint: POST /api/retrieval/hybrid-rag
   */
  searchHybridRag: ({
    query = '',
    queryText = '',
    queryType,
    depth = 1,
    focus,
    topK = 5,
    filters = {},
    signal = null,
    timeoutMs = 15000,
  } = {}) => {
    const cleanQuery = (query || queryText || '').trim();
    if (!cleanQuery) {
      throw new ApiError('Query parameter cannot be empty', {
        status: 400,
        code: 'INVALID_QUERY',
      });
    }

    const boundedTopK = Math.min(Math.max(parseInt(topK, 10) || 5, 1), 50);
    const boundedDepth = Math.min(Math.max(parseInt(depth, 10) || 1, 1), 5);

    const mergedFilters = {
      ...filters,
      ...(queryType ? { query_type: queryType } : {}),
      ...(boundedDepth ? { depth: boundedDepth } : {}),
      ...(focus ? { focus } : {}),
    };

    const payload = {
      query: cleanQuery,
      top_k: boundedTopK,
      filters: mergedFilters,
      query_type: queryType || undefined,
      depth: boundedDepth,
      focus: focus || undefined,
    };

    return http.post('/api/retrieval/hybrid-rag', payload, { signal, timeoutMs });
  },

  /**
   * Dedicated dense vector search via FAISS.
   * Endpoint: POST /api/retrieval/semantic
   */
  searchSemantic: ({ query = '', topK = 5, filters = {}, signal = null, timeoutMs = 15000 } = {}) =>
    http.post(
      '/api/retrieval/semantic',
      { query, top_k: topK, filters },
      { signal, timeoutMs }
    ),

  /**
   * Dedicated lexical search via BM25Okapi.
   * Endpoint: POST /api/retrieval/bm25
   */
  searchBM25: ({ query = '', topK = 5, filters = {}, signal = null, timeoutMs = 15000 } = {}) =>
    http.post(
      '/api/retrieval/bm25',
      { query, top_k: topK, filters },
      { signal, timeoutMs }
    ),
};

/**
 * 4.5 Evidence Domain
 */
export const evidenceApi = {
  /**
   * Retrieves source-grounded text chunk and metadata by document / sūtra ID.
   * Endpoint: GET /api/retrieval/by-source/<id>
   */
  getBySourceId: (sourceId, { signal = null, timeoutMs = 10000 } = {}) =>
    http.get(`/api/retrieval/by-source/${encodeURIComponent(sourceId)}`, { signal, timeoutMs }),

  /**
   * Retrieves evidence passages directly referencing an entity.
   * Endpoint: GET /api/retrieval/by-entity/<entityName>
   */
  getByEntityName: (entityName, { signal = null, timeoutMs = 10000 } = {}) =>
    http.get(`/api/retrieval/by-entity/${encodeURIComponent(entityName)}`, { signal, timeoutMs }),

  /**
   * Retrieves grounded Knowledge Graph subgraph for structured query grounding.
   * Endpoint: POST /api/query/graph-retrieval
   */
  getGroundedGraph: ({
    query = '',
    seedIds = [],
    passages = [],
    entities = [],
    concepts = [],
    hopDepth = 2,
    maxNodes = 50,
    maxPaths = 20,
    relationshipTypes = null,
    signal = null,
    timeoutMs = 15000,
  } = {}) =>
    http.post(
      '/api/query/graph-retrieval',
      {
        query,
        seed_ids: seedIds,
        passages,
        entities,
        concepts,
        hopDepth,
        maxNodes,
        maxPaths,
        relationship_types: relationshipTypes,
      },
      { signal, timeoutMs }
    ),
};

/**
 * 4.6 Reasoning & Verification Domain
 */
export const reasoningApi = {
  /**
   * Generates 5-stage Pañcāvayava syllogism and connected proof trace DAG.
   * Endpoint: POST /api/reasoning/deduce
   */
  deduce: ({
    queryText = '',
    query = '',
    tinai = 'Kuṟiñci',
    evidenceItems = [],
    signal = null,
    timeoutMs = 20000,
  } = {}) =>
    http.post(
      '/api/reasoning/deduce',
      { queryText: queryText || query, query: queryText || query, tinai, evidenceItems },
      { signal, timeoutMs }
    ),

  /**
   * Executes 5 Hetvābhāsa fallacy checks against real evidence items.
   * Endpoint: POST /api/reasoning/validate-fallacies
   */
  validateFallacies: ({
    tinai = 'Kuṟiñci',
    evidenceItems = [],
    evidenceCount = 5,
    signal = null,
    timeoutMs = 15000,
  } = {}) =>
    http.post(
      '/api/reasoning/validate-fallacies',
      {
        tinai,
        evidenceCount: Math.max(1, evidenceCount),
        evidence_items: evidenceItems,
      },
      { signal, timeoutMs }
    ),

  /**
   * Generates a machine-readable graphical proof trace from evidence items.
   * Endpoint: POST /api/reasoning/proof-trace
   */
  getProofTrace: ({
    query = '',
    queryText = '',
    evidenceItems = [],
    tinai = 'Kuṟiñci',
    minEvidenceThreshold = 2,
    signal = null,
    timeoutMs = 20000,
  } = {}) =>
    http.post(
      '/api/reasoning/proof-trace',
      {
        query: query || queryText,
        queryText: query || queryText,
        evidenceItems,
        evidence_items: evidenceItems,
        tinai,
        minEvidenceThreshold,
      },
      { signal, timeoutMs }
    ),

  /**
   * Executes end-to-end neuro-symbolic analysis for an input inquiry.
   * Endpoint: POST /api/query/analyze
   */
  analyzeQuery: ({
    queryText = '',
    query = '',
    depth = 1,
    focus = 'Relationship',
    signal = null,
    timeoutMs = 25000,
  } = {}) =>
    http.post(
      '/api/query/analyze',
      { queryText: queryText || query, depth, focus },
      { signal, timeoutMs }
    ),

  /**
   * Dynamically validates confidence score across evidence, graph traversal, and reasoning consistency.
   * Endpoint: POST /api/reasoning/confidence/validate
   */
  validateConfidence: ({
    query = '',
    evidenceRecords = [],
    selectedEvidenceId = null,
    graphNodes = [],
    selectedGraphNodeId = null,
    reasoningStages = [],
    premises = [],
    vyaptiRule = null,
    tinai = null,
    signal = null,
    timeoutMs = 12000,
  } = {}) =>
    http.post(
      '/api/reasoning/confidence/validate',
      {
        query,
        evidenceRecords,
        selectedEvidenceId,
        graphNodes,
        selectedGraphNodeId,
        reasoningStages,
        premises,
        vyaptiRule,
        tinai,
      },
      { signal, timeoutMs }
    ),

  /**
   * Retrieves canonical research inquiries for benchmark testing.
   * Endpoint: GET /api/query/examples
   */
  getCanonicalExamples: ({ signal = null, timeoutMs = 10000 } = {}) =>
    http.get('/api/query/examples', { signal, timeoutMs }),
};

/**
 * 4.7 System Status & Corpus Info Domain
 */
export const systemStatusApi = {
  /**
   * Retrieves unified, live diagnostics across Flask, Neo4j Aura, RAG, KG, and Corpus.
   * Endpoint: GET /api/system/status
   */
  getStatus: ({ signal = null, timeoutMs = 10000 } = {}) =>
    http.get('/api/system/status', { signal, timeoutMs }),

  /**
   * Ping probe.
   * Endpoint: GET /api/system/ping
   */
  ping: ({ signal = null, timeoutMs = 5000 } = {}) =>
    http.get('/api/system/ping', { signal, timeoutMs }),

  /**
   * Retrieves RAG indexing health, passage counts, and FAISS index status.
   * Endpoint: GET /api/retrieval/statistics
   */
  getRetrievalStatistics: ({ signal = null, timeoutMs = 10000 } = {}) =>
    http.get('/api/retrieval/statistics', { signal, timeoutMs }),
};

/**
 * 4.8 Corpus Metadata Domain
 */
export const corpusApi = {
  /**
   * Retrieves canonical corpus overview and Atikāram summary.
   * Endpoint: GET /api/corpus/info
   */
  getCorpusInfo: ({ signal = null, timeoutMs = 10000 } = {}) =>
    http.get('/api/corpus/info', { signal, timeoutMs }),

  /**
   * Retrieves dataset profiling statistics.
   * Endpoint: GET /api/corpus/statistics
   */
  getCorpusStatistics: ({ signal = null, timeoutMs = 10000 } = {}) =>
    http.get('/api/corpus/statistics', { signal, timeoutMs }),
};

// =============================================================================
// 5. Central API Client Bundle
// =============================================================================

export const apiClient = {
  dashboard: dashboardApi,
  graph: graphApi,
  search: searchApi,
  corpus: corpusApi,
  rag: ragApi,
  evidence: evidenceApi,
  reasoning: reasoningApi,
  systemStatus: systemStatusApi,
  http,
  request: apiRequest,
  buildUrl: buildApiUrl,
};

export default apiClient;

// =============================================================================
// 6. Direct Named Exports (for backwards-compatibility across codebase)
// =============================================================================

export const searchPassages = searchApi.searchPassages;
export const searchQuery = ragApi.searchHybridRag;
export const generateGroundedAnswer = ragApi.generateGroundedAnswer;
export const getGraphStatistics = graphApi.getStatistics;
export const getGraphHealth = graphApi.getHealth;
export const getGraphElements = graphApi.getElements;
export const getCorpusInfo = corpusApi.getCorpusInfo;
export const getCorpusStatistics = corpusApi.getCorpusStatistics;
export const validateFallacies = reasoningApi.validateFallacies;
export const validateConfidence = reasoningApi.validateConfidence;
export const getProofTrace = reasoningApi.getProofTrace;
export const deduceReasoning = reasoningApi.deduce;
export const getDashboardSummary = dashboardApi.getDashboardSummary;
export const getSystemStatus = systemStatusApi.getStatus;
export const pingSystem = systemStatusApi.ping;
export const queryGraph = graphApi.queryGraph;
export const getQuerySubgraph = graphApi.getQuerySubgraph;
export const mutateGraph = graphApi.mutateGraph;
export const upsertEntity = graphApi.upsertEntity;
export const upsertRelationship = graphApi.upsertRelationship;
export const clearCache = ragApi.clearCache;
