/**
 * Production Data Normalization Layer for Neo4j and Knowledge Graph API Responses.
 *
 * Converts diverse backend graph formats (Neo4j Aura Cypher results, in-memory KG stores,
 * or raw API payloads) into canonical D3-compatible nodes and links without silently dropping,
 * limiting, or ignoring valid entities or relationships.
 */
export const TAXONOMY_COLORS = {
  Literature: { fill: '#f8fafc', stroke: '#1e293b', text: '#0f172a', radius: 36, shape: 'rect' },
  Work: { fill: '#eef2ff', stroke: '#4f46e5', text: '#312e81', radius: 32, shape: 'rect' },
  Section: { fill: '#f1f5f9', stroke: '#475569', text: '#0f172a', radius: 28, shape: 'rect' },
  Verse: { fill: '#f0fdf4', stroke: '#16a34a', text: '#14532d', radius: 26, shape: 'circle' },
  Concept: { fill: '#faf5ff', stroke: '#9333ea', text: '#581c87', radius: 26, shape: 'circle' },
  Entity: { fill: '#fff7ed', stroke: '#ea580c', text: '#7c2d12', radius: 24, shape: 'circle' },
  Event: { fill: '#fffbeb', stroke: '#d97706', text: '#78350f', radius: 24, shape: 'circle' },
  Evidence: { fill: '#eff6ff', stroke: '#2563eb', text: '#1e3a8a', radius: 26, shape: 'circle' },
  Primary: { fill: '#eff6ff', stroke: '#3b82f6', text: '#1e3a8a', radius: 26, shape: 'circle' },
  Secondary: { fill: '#faf5ff', stroke: '#8b5cf6', text: '#4c1d95', radius: 26, shape: 'circle' },
  Aesthetic: { fill: '#fdf2f8', stroke: '#ec4899', text: '#831843', radius: 26, shape: 'circle' },
  Person: { fill: '#f5f3ff', stroke: '#7c3aed', text: '#4c1d95', radius: 24, shape: 'circle' },
  Object: { fill: '#f0fdf4', stroke: '#059669', text: '#064e3b', radius: 24, shape: 'circle' },
  Premise: { fill: '#faf5ff', stroke: '#7c3aed', text: '#4c1d95', radius: 30, shape: 'pill' },
  Rule: { fill: '#fffbeb', stroke: '#d97706', text: '#78350f', radius: 30, shape: 'pill' },
  Inference: { fill: '#eef2ff', stroke: '#4f46e5', text: '#312e81', radius: 30, shape: 'pill' },
  Conclusion: { fill: '#ecfdf5', stroke: '#059669', text: '#064e3b', radius: 30, shape: 'pill' },
};

/**
 * Safely extracts a string ID from any Neo4j identity structure.
 * Handles integer IDs, object IDs with { low, high }, element IDs, or raw strings/numbers.
 *
 * @param {any} rawId - The raw identifier from Neo4j or API.
 * @param {string} fallback - Fallback identifier if rawId is empty.
 * @returns {string} - Clean canonical string ID.
 */
export function extractNodeId(rawId, fallback = '') {
  if (rawId === null || rawId === undefined) return String(fallback);
  if (typeof rawId === 'string') return rawId.trim();
  if (typeof rawId === 'number') return String(rawId);
  if (typeof rawId === 'object') {
    if (rawId.id !== undefined && rawId.id !== null) return extractNodeId(rawId.id, fallback);
    if (rawId.elementId) return String(rawId.elementId);
    if (rawId.identity !== undefined) return extractNodeId(rawId.identity, fallback);
    if (typeof rawId.low === 'number') return String(rawId.low);
  }
  return String(fallback);
}

/**
 * Safely parses metadata_json or property fields if encoded as JSON strings.
 *
 * @param {any} meta - Raw metadata object or JSON string.
 * @returns {object} - Parsed JavaScript object.
 */
function parseMetadata(meta) {
  if (!meta) return {};
  if (typeof meta === 'object') return { ...meta };
  if (typeof meta === 'string') {
    try {
      const parsed = JSON.parse(meta);
      return typeof parsed === 'object' && parsed !== null ? parsed : {};
    } catch {
      return { raw: meta };
    }
  }
  return {};
}

/**
 * Normalizes a single Neo4j or API node record into canonical D3 node:
 * { id, label, type, properties, ... }
 *
 * @param {object} rawNode - The raw node dictionary.
 * @param {number} index - Index fallback for synthetic ID generation.
 * @returns {object} - Normalized node object.
 */
export function normalizeNode(rawNode, index = 0) {
  if (!rawNode || typeof rawNode !== 'object') {
    const fallbackId = `synth_node_${index}`;
    return {
      id: fallbackId,
      label: fallbackId,
      type: 'Entity',
      properties: { isMalformed: true },
    };
  }

  // 1. Resolve canonical ID
  const id = extractNodeId(
    rawNode.id || rawNode.elementId || rawNode.identity || rawNode._id,
    `node_${index}`
  );

  // 2. Resolve label / name
  const label =
    rawNode.label ||
    rawNode.name ||
    rawNode.tamil_label ||
    rawNode.tamilLabel ||
    rawNode.tamil_text ||
    rawNode.properties?.label ||
    rawNode.properties?.name ||
    id;

  // 3. Resolve category / type from properties or Neo4j labels array
  let type =
    rawNode.type ||
    rawNode.category ||
    rawNode.properties?.type ||
    rawNode.properties?.category;

  if (!type && Array.isArray(rawNode.labels) && rawNode.labels.length > 0) {
    // Pick the most specific label (exclude generic labels like KGNode)
    const specificLabel = rawNode.labels.find((l) => l !== 'KGNode' && l !== 'Node');
    type = specificLabel || rawNode.labels[0];
  }
  if (!type) {
    type = 'Concept';
  }

  // 4. Merge properties
  const parsedMeta = parseMetadata(rawNode.metadata || rawNode.metadata_json);
  const explicitProps = parseMetadata(rawNode.properties);
  const properties = {
    ...rawNode,
    ...parsedMeta,
    ...explicitProps,
    // Preserve core values
    id,
    label,
    type,
  };

  // Remove duplicate deep props
  delete properties.properties;
  delete properties.metadata;
  delete properties.metadata_json;

  return {
    id,
    label: String(label),
    type: String(type),
    properties,
    // Convenient top-level shortcuts for D3 visual bindings
    transliteration:
      properties.transliteration ||
      properties.transliterated_name ||
      rawNode.transliteration ||
      '',
    tamilLabel:
      properties.tamilLabel ||
      properties.tamil_label ||
      properties.tamil_text ||
      String(label),
    confidence:
      typeof properties.confidence === 'number'
        ? properties.confidence
        : typeof rawNode.confidence === 'number'
          ? rawNode.confidence
          : 1.0,
    hierarchyLevel:
      properties.hierarchy_level ||
      properties.hierarchyLevel ||
      rawNode.hierarchy_level ||
      'L5',
    tinai: properties.tinai || rawNode.tinai || '',
    isProofTraceNode: !!(rawNode.isProofTraceNode || properties.isProofTraceNode),
    isEvidenceRecord: !!(rawNode.isEvidenceRecord || properties.isEvidenceRecord),
    initialX: rawNode.x ?? rawNode.initialX,
    initialY: rawNode.y ?? rawNode.initialY,
  };
}

/**
 * Normalizes a single Neo4j or API relationship into canonical D3 link:
 * { id, source, target, type, properties, ... }
 *
 * @param {object} rawRel - Raw relationship dictionary.
 * @returns {object|null} - Normalized link object or null if completely invalid.
 */
export function normalizeLink(rawRel) {
  if (!rawRel || typeof rawRel !== 'object') {
    return null;
  }

  // 1. Resolve source ID
  const rawSource =
    rawRel.source !== undefined && rawRel.source !== null
      ? rawRel.source
      : rawRel.start !== undefined && rawRel.start !== null
        ? rawRel.start
        : rawRel.startNode !== undefined && rawRel.startNode !== null
          ? rawRel.startNode
          : rawRel.startNodeElementId;

  const source = extractNodeId(rawSource, '');
  if (!source) return null;

  // 2. Resolve target ID
  const rawTarget =
    rawRel.target !== undefined && rawRel.target !== null
      ? rawRel.target
      : rawRel.end !== undefined && rawRel.end !== null
        ? rawRel.end
        : rawRel.endNode !== undefined && rawRel.endNode !== null
          ? rawRel.endNode
          : rawRel.endNodeElementId;

  const target = extractNodeId(rawTarget, '');
  if (!target) return null;

  // 3. Resolve relationship type & label
  const type =
    rawRel.type ||
    rawRel.relation ||
    rawRel.label ||
    rawRel.properties?.type ||
    'RELATED_TO';

  const label =
    rawRel.label ||
    rawRel.relation ||
    rawRel.type ||
    type;

  // 4. Resolve unique ID without depending on array indexes
  const baseFallback = `rel_${source}_${type}_${target}`;
  const id = extractNodeId(
    rawRel.id || rawRel.elementId || rawRel.identity,
    baseFallback
  );

  // 5. Merge properties
  const parsedMeta = parseMetadata(rawRel.metadata || rawRel.metadata_json);
  const explicitProps = parseMetadata(rawRel.properties);
  const properties = {
    ...rawRel,
    ...parsedMeta,
    ...explicitProps,
    id,
    source,
    target,
    type,
    label,
  };

  delete properties.properties;
  delete properties.metadata;
  delete properties.metadata_json;

  return {
    id,
    source,
    target,
    type: String(type),
    label: String(label),
    properties,
    confidence:
      typeof properties.confidence === 'number'
        ? properties.confidence
        : typeof rawRel.confidence === 'number'
          ? rawRel.confidence
          : 1.0,
    isProofTraceEdge: !!(rawRel.isProofTraceEdge || properties.isProofTraceEdge),
    isEvidenceEdge: !!(rawRel.isEvidenceEdge || properties.isEvidenceEdge),
  };
}

/**
 * Comprehensive graph normalization layer.
 * Ingests any Neo4j response, API payload, or raw nodes/edges structure.
 * Guaranteed to NEVER silently drop valid entities or relationships:
 * - Preserves all nodes (including isolated nodes with no connections)
 * - Preserves all links (including self-referential loops and multi-edges)
 * - Generates stable, deterministic unique IDs without array indexes
 * - Computes parallel edge indices (linkIndex, totalParallelLinks) for SVG curvature
 * - Exposes full pipeline diagnostics (backend, normalized, and component metrics)
 *
 * @param {any} inputData - The raw graph payload.
 * @returns {{
 *   nodes: Array<object>,
 *   links: Array<object>,
 *   stats: {
 *     backendNodeCount: number,
 *     backendRelCount: number,
 *     nodeCount: number,
 *     linkCount: number,
 *     synthesizedNodeCount: number,
 *     duplicatesResolved: number,
 *     selfLoopCount: number,
 *     multiEdgeCount: number,
 *     isolatedNodeCount: number
 *   }
 * }}
 */
export function normalizeGraphData(inputData) {
  if (!inputData) {
    return {
      nodes: [],
      links: [],
      stats: {
        backendNodeCount: 0,
        backendRelCount: 0,
        nodeCount: 0,
        linkCount: 0,
        synthesizedNodeCount: 0,
        duplicatesResolved: 0,
        selfLoopCount: 0,
        multiEdgeCount: 0,
        isolatedNodeCount: 0,
      },
    };
  }

  // 1. Extract raw node and edge collections across all common schema shapes
  let rawNodes = [];
  let rawEdges = [];
  let reportedBackendNodeCount = 0;
  let reportedBackendRelCount = 0;

  if (Array.isArray(inputData)) {
    rawNodes = inputData;
    reportedBackendNodeCount = inputData.length;
  } else if (typeof inputData === 'object') {
    const payload = inputData.data || inputData;

    reportedBackendNodeCount =
      typeof payload.backend_node_count === 'number'
        ? payload.backend_node_count
        : typeof payload.total_nodes === 'number'
          ? payload.total_nodes
          : 0;

    reportedBackendRelCount =
      typeof payload.backend_edge_count === 'number'
        ? payload.backend_edge_count
        : typeof payload.total_edges === 'number'
          ? payload.total_edges
          : 0;

    if (Array.isArray(payload.nodes)) {
      rawNodes = payload.nodes;
      if (!reportedBackendNodeCount) reportedBackendNodeCount = rawNodes.length;
    }

    if (Array.isArray(payload.relationships)) {
      rawEdges = payload.relationships;
      if (!reportedBackendRelCount) reportedBackendRelCount = rawEdges.length;
    } else if (Array.isArray(payload.edges)) {
      rawEdges = payload.edges;
      if (!reportedBackendRelCount) reportedBackendRelCount = rawEdges.length;
    } else if (Array.isArray(payload.links)) {
      rawEdges = payload.links;
      if (!reportedBackendRelCount) reportedBackendRelCount = rawEdges.length;
    }

    // Support Neo4j Cypher Records format: [ { node, rel }, ... ]
    if (rawNodes.length === 0 && Array.isArray(payload.records)) {
      payload.records.forEach((rec) => {
        if (!rec) return;
        if (rec.node || rec.n) rawNodes.push(rec.node || rec.n);
        if (rec.m) rawNodes.push(rec.m);
        if (rec.r || rec.rel) rawEdges.push(rec.r || rec.rel);
      });
      if (!reportedBackendNodeCount) reportedBackendNodeCount = rawNodes.length;
      if (!reportedBackendRelCount) reportedBackendRelCount = rawEdges.length;
    }
  }

  // 2. Normalize and preserve every node (including isolated nodes)
  const nodeMap = new Map(); // id -> node
  let duplicatesResolved = 0;

  rawNodes.forEach((item, idx) => {
    const node = normalizeNode(item, idx);
    if (!node || !node.id) return;

    if (nodeMap.has(node.id)) {
      const existing = nodeMap.get(node.id);
      existing.properties = { ...existing.properties, ...node.properties };
      if (!existing.transliteration && node.transliteration) {
        existing.transliteration = node.transliteration;
      }
      if (node.isProofTraceNode) existing.isProofTraceNode = true;
      if (node.isEvidenceRecord) existing.isEvidenceRecord = true;
      duplicatesResolved++;
    } else {
      nodeMap.set(node.id, node);
    }
  });

  // 3. Normalize relationships with stable IDs (no array index dependency)
  const initialLinks = [];
  const tupleCounts = new Map(); // tupleKey -> occurrence count
  let synthesizedNodeCount = 0;
  let selfLoopCount = 0;

  rawEdges.forEach((item) => {
    const link = normalizeLink(item);
    if (!link) return;

    const src = link.source;
    const tgt = link.target;
    const type = link.type || 'RELATED_TO';

    if (src === tgt) {
      selfLoopCount++;
    }

    // Deterministic semantic key for tuple occurrences
    const tupleKey = `${src}::${type}::${tgt}`;
    const occurrence = (tupleCounts.get(tupleKey) || 0) + 1;
    tupleCounts.set(tupleKey, occurrence);

    // If ID was synthesized or duplicated, ensure stable unique ID without array indexes
    if (!link.id || link.id === `rel_${src}_${type}_${tgt}` || occurrence > 1) {
      link.id = `rel_${src}_${type}_${tgt}_${occurrence}`;
    }

    // Ensure source node exists — synthesize if missing so relationship is NEVER silently dropped
    if (!nodeMap.has(src)) {
      nodeMap.set(src, {
        id: src,
        label: src,
        type: 'Entity',
        properties: { isSynthesized: true, referencedBy: link.id },
        confidence: 0.9,
        hierarchyLevel: 'L5',
      });
      synthesizedNodeCount++;
    }

    // Ensure target node exists — synthesize if missing so relationship is NEVER silently dropped
    if (!nodeMap.has(tgt)) {
      nodeMap.set(tgt, {
        id: tgt,
        label: tgt,
        type: 'Entity',
        properties: { isSynthesized: true, referencedBy: link.id },
        confidence: 0.9,
        hierarchyLevel: 'L5',
      });
      synthesizedNodeCount++;
    }

    initialLinks.push(link);
  });

  // 4. Index parallel edges between the same node pair for visual curvature
  // Pair key is unordered: e.g. min(src, tgt) + '---' + max(src, tgt)
  const pairGroups = new Map();
  initialLinks.forEach((link) => {
    const pairKey = [link.source, link.target].sort().join('---');
    if (!pairGroups.has(pairKey)) {
      pairGroups.set(pairKey, []);
    }
    pairGroups.get(pairKey).push(link);
  });

  let multiEdgeCount = 0;
  const connectedNodeIds = new Set();

  pairGroups.forEach((group) => {
    const total = group.length;
    if (total > 1) {
      multiEdgeCount += total;
    }
    group.forEach((link, idx) => {
      link.linkIndex = idx;
      link.totalParallelLinks = total;
      link.isSelfReferential = link.source === link.target;
      connectedNodeIds.add(link.source);
      connectedNodeIds.add(link.target);
    });
  });

  const normalizedNodes = Array.from(nodeMap.values());
  const isolatedNodeCount = normalizedNodes.filter((n) => !connectedNodeIds.has(n.id)).length;

  return {
    nodes: normalizedNodes,
    links: initialLinks,
    stats: {
      backendNodeCount: reportedBackendNodeCount,
      backendRelCount: reportedBackendRelCount,
      nodeCount: normalizedNodes.length,
      linkCount: initialLinks.length,
      synthesizedNodeCount,
      duplicatesResolved,
      selfLoopCount,
      multiEdgeCount,
      isolatedNodeCount,
    },
  };
}
