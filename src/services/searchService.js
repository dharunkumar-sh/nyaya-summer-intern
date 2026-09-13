/**
 * Centralized Search API Service for Classical Tamil Literary Knowledge.
 * Provides unified interface to Flask /api/search endpoint with request cancellation,
 * search modes, pagination, and error normalization.
 */

import { buildApiUrl, searchQuery, API_BASE_URL, searchApi } from './apiClient';

export { searchQuery, API_BASE_URL, buildApiUrl, searchApi };

export const SEARCH_MODES = [
  {
    id: 'hybrid',
    label: 'Hybrid',
    fullLabel: 'Hybrid (BM25 + Semantic)',
    desc: 'Dual-channel BM25 lexical + dense multilingual vector embeddings with re-ranking',
    badgeVariant: 'purple',
  },
  {
    id: 'keyword',
    label: 'Keyword',
    fullLabel: 'Keyword (BM25Plus)',
    desc: 'Lexical exact & multi-term matching over literary text',
    badgeVariant: 'blue',
  },
  {
    id: 'semantic',
    label: 'Semantic',
    fullLabel: 'Semantic (Dense Vector)',
    desc: 'Multilingual conceptual embeddings with cosine similarity',
    badgeVariant: 'emerald',
  },
];

/**
 * Executes a search request against /api/search.
 *
 * @param {Object} options
 * @param {string} options.query - User search text
 * @param {string} [options.mode='hybrid'] - 'hybrid' | 'keyword' | 'semantic'
 * @param {number} [options.topK=10] - Desired number of top results
 * @param {number} [options.page=1] - 1-indexed page number
 * @param {number} [options.pageSize=10] - Number of items per page
 * @param {string} [options.work] - Optional work filter
 * @param {string} [options.section] - Optional section filter
 * @param {string} [options.chapter] - Optional chapter filter
 * @param {string} [options.source] - Optional source ID filter
 * @param {Object} [options.filters] - Nested filter dictionary
 * @param {boolean} [options.includeGraph=true] - Attach knowledge graph context
 * @param {AbortSignal} [options.signal] - AbortController signal for cancellation
 * @returns {Promise<Object>} Formatted search response payload
 */
export async function searchPassages({
  query,
  mode = 'hybrid',
  topK = 10,
  page = 1,
  pageSize = 10,
  work,
  section,
  chapter,
  source,
  filters = {},
  includeGraph = true,
  signal,
} = {}) {
  const cleanQuery = (query || '').trim();

  // If query is empty, return empty success response immediately without network overhead
  if (!cleanQuery) {
    return {
      success: true,
      data: {
        original_query: '',
        normalized_query: '',
        mode,
        result_count: 0,
        total_results: 0,
        page: 1,
        page_size: pageSize,
        total_pages: 1,
        filters_applied: {},
        ranked_results: [],
      },
      message: 'No query provided',
    };
  }

  return searchApi.searchPassages({
    query: cleanQuery,
    mode,
    topK,
    page,
    pageSize,
    includeGraph,
    filters,
    work,
    section,
    chapter,
    source,
    signal,
  });
}

/**
 * Returns canonical search mode definition by ID.
 */
export function getSearchModeConfig(modeId) {
  return SEARCH_MODES.find((m) => m.id === modeId) || SEARCH_MODES[0];
}
