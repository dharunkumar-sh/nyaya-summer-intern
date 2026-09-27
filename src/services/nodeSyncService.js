/**
 * Intelligent Synchronization and Stable ID Resolution Service.
 *
 * Provides bidirectional resolution between Query Center elements
 * (retrieved passages, entities, concepts, events, evidence nodes, premises,
 * rules, and conclusions) and D3 Knowledge Graph nodes/edges.
 */

/**
 * Normalizes an entity or node identifier for resilient, diacritic-tolerant matching.
 * Strips Sanskrit/Tamil romanized diacritics (e.g., Kuṟiñci -> kurinci, Cēyōṉ -> ceyon),
 * removes non-alphanumeric noise, and standardizes spacing.
 *
 * @param {any} val - Raw input identifier or string.
 * @returns {string} - Clean normalized search token.
 */
export function normalizeEntityId(val) {
  if (val === null || val === undefined) return '';
  const str = String(val).trim().toLowerCase();

  // Normalize Unicode diacritics
  return str
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '') // remove combining marks
    .replace(/ṟ/g, 'r')
    .replace(/[ñṅ]/g, 'n')
    .replace(/[ḷḻ]/g, 'l')
    .replace(/ō/g, 'o')
    .replace(/ē/g, 'e')
    .replace(/[ṭṯ]/g, 't')
    .replace(/ṇ/g, 'n')
    .replace(/ā/g, 'a')
    .replace(/ī/g, 'i')
    .replace(/ū/g, 'u')
    .replace(/[^a-z0-9\u0B80-\u0BFF]/g, '') // preserve Tamil Unicode script & standard alphanumerics
    .trim();
}

/**
 * Known semantic aliases and Nyāya inference stage mappings.
 */
export const NYAYA_STAGE_ALIASES = {
  pratijna: ['p1', 'pratijna', 'thesis', 'proposition', 'premise1', 'premise'],
  hetu: ['p2', 'hetu', 'reason', 'ground', 'cause', 'premise2'],
  udaharana: ['r1', 'udaharana', 'rule', 'rule1', 'vyapti', 'universal_rule'],
  upanaya: ['i1', 'upanaya', 'application', 'subsumption', 'inference1'],
  nigamana: ['c1', 'nigamana', 'conclusion', 'conclusion1', 'synthesized_truth'],
  e1: ['evidence1', 'e1'],
  e2: ['evidence2', 'e2'],
  e3: ['evidence3', 'e3'],
  p1: ['pratijna', 'premise1', 'p1'],
  p2: ['hetu', 'premise2', 'p2'],
  r1: ['udaharana', 'rule1', 'r1', 'vyapti'],
  i1: ['upanaya', 'inference1', 'i1'],
  c1: ['nigamana', 'conclusion1', 'c1'],
};

/**
 * Finds a corresponding D3 node in a node list using a stable ID or multi-field descriptor.
 *
 * Handles:
 * 1. Direct ID match (`node.id === targetId`)
 * 2. Canonical passage ID (`node.passageId === targetId`, `node.properties.passage_id`)
 * 3. Evidence / Step code (`node.code === targetId`, `node.id === 'E1'`)
 * 4. Case- and diacritic-insensitive label / transliteration / name match
 * 5. Tamil script label match (`node.tamilLabel === targetId`)
 * 6. Aliases list matching
 * 7. Nyāya deductive stage mapping (`pratijna` -> `P1`, `udaharana` -> `R1`, `nigamana` -> `C1`)
 * 8. Sūtra number / citation extraction (e.g. Sūtra 18 -> matches node with sutraNumber 18)
 *
 * @param {Array<object>} nodes - Current D3 simulation nodes.
 * @param {any} target - Target ID, string token, or object descriptor.
 * @returns {object|null} - Matching D3 node or null.
 */
export function findNodeByStableId(nodes, target) {
  if (!Array.isArray(nodes) || nodes.length === 0 || !target) {
    return null;
  }

  // If target is an object, extract all possible candidate identifiers
  let rawCandidates = [];
  if (typeof target === 'object') {
    if (target.id) rawCandidates.push(target.id);
    if (target.code) rawCandidates.push(target.code);
    if (target.passageId) rawCandidates.push(target.passageId);
    if (target.passage_id) rawCandidates.push(target.passage_id);
    if (target.label) rawCandidates.push(target.label);
    if (target.name) rawCandidates.push(target.name);
    if (target.transliteration) rawCandidates.push(target.transliteration);
    if (target.tamilLabel) rawCandidates.push(target.tamilLabel);
    if (target.key) rawCandidates.push(target.key);
    if (target.sanskritName) rawCandidates.push(target.sanskritName);
    if (Array.isArray(target.aliases)) rawCandidates.push(...target.aliases);
  } else {
    rawCandidates.push(target);
  }

  // Filter and deduplicate raw candidates
  const candidateList = Array.from(new Set(rawCandidates.filter(Boolean).map(String)));
  if (candidateList.length === 0) return null;

  // PASS 1: Exact ID or Code Match
  for (const cand of candidateList) {
    const candLower = cand.toLowerCase().trim();
    const exact = nodes.find((n) => {
      const nId = String(n.id || '').toLowerCase().trim();
      const nCode = String(n.code || '').toLowerCase().trim();
      const nPassageId = String(n.passageId || n.properties?.passage_id || n.properties?.passageId || '').toLowerCase().trim();
      return nId === candLower || nCode === candLower || nPassageId === candLower;
    });
    if (exact) return exact;
  }

  // PASS 2: Nyāya Stage Alias Mapping
  for (const cand of candidateList) {
    const candNorm = normalizeEntityId(cand);
    for (const [key, aliases] of Object.entries(NYAYA_STAGE_ALIASES)) {
      if (candNorm === key || aliases.includes(candNorm)) {
        const stageNode = nodes.find((n) => {
          const nIdNorm = normalizeEntityId(n.id);
          const nCodeNorm = normalizeEntityId(n.code);
          const nLabelNorm = normalizeEntityId(n.label);
          const hasMatchingAlias = Array.isArray(n.aliases) && n.aliases.some((a) => {
            const aNorm = normalizeEntityId(a);
            return aNorm === key || aliases.includes(aNorm);
          });

          return (
            nIdNorm === key ||
            aliases.includes(nIdNorm) ||
            nCodeNorm === key ||
            aliases.includes(nCodeNorm) ||
            aliases.includes(nLabelNorm) ||
            hasMatchingAlias
          );
        });
        if (stageNode) return stageNode;
      }
    }
  }

  // PASS 3: Diacritic-tolerant Normalized Token Match (Label, Name, Transliteration)
  for (const cand of candidateList) {
    const candNorm = normalizeEntityId(cand);
    if (!candNorm) continue;

    const matched = nodes.find((n) => {
      const nIdNorm = normalizeEntityId(n.id);
      if (nIdNorm === candNorm) return true;

      const nLabelNorm = normalizeEntityId(n.label);
      if (nLabelNorm === candNorm) return true;

      const nNameNorm = normalizeEntityId(n.name);
      if (nNameNorm === candNorm) return true;

      const nTransNorm = normalizeEntityId(n.transliteration);
      if (nTransNorm === candNorm) return true;

      const nTamil = String(n.tamilLabel || n.tamil_label || '').trim();
      if (nTamil && nTamil === cand.trim()) return true;

      if (Array.isArray(n.aliases)) {
        if (n.aliases.some((a) => normalizeEntityId(a) === candNorm)) return true;
      }

      return false;
    });

    if (matched) return matched;
  }

  // PASS 4: Substring / Sūtra Number Heuristic
  for (const cand of candidateList) {
    const sutraMatch = cand.match(/s[uū]tra\s*(\d+)/i);
    if (sutraMatch) {
      const num = parseInt(sutraMatch[1], 10);
      const sutraNode = nodes.find(
        (n) =>
          n.sutraNumber === num ||
          n.properties?.sutra_number === num ||
          n.properties?.sutraNumber === num ||
          n.id?.includes(`_${num}`) ||
          n.passageId?.includes(`_${num}`)
      );
      if (sutraNode) return sutraNode;
    }
  }

  // PASS 5: Partial Inclusion for Concept/Entity Chips
  for (const cand of candidateList) {
    const candNorm = normalizeEntityId(cand);
    if (candNorm.length >= 4) {
      const partial = nodes.find((n) => {
        const nIdNorm = normalizeEntityId(n.id);
        const nLabelNorm = normalizeEntityId(n.label);
        const nTransNorm = normalizeEntityId(n.transliteration);
        return (
          nIdNorm.includes(candNorm) ||
          candNorm.includes(nIdNorm) ||
          (nLabelNorm && (nLabelNorm.includes(candNorm) || candNorm.includes(nLabelNorm))) ||
          (nTransNorm && (nTransNorm.includes(candNorm) || candNorm.includes(nTransNorm)))
        );
      });
      if (partial) return partial;
    }
  }

  return null;
}

/**
 * Resolves all evidence records from the Query Center that correlate with a given graph node.
 * Matches by passageId, ID, code, mentioned entities, concepts, or tinai.
 *
 * @param {object} node - The selected D3 graph node.
 * @param {Array<object>} evidenceRecords - List of retrieved evidence records from ReasonerContext.
 * @returns {Array<object>} - Array of matching evidence items (or empty array).
 */
export function findAssociatedEvidenceForNode(node, evidenceRecords) {
  if (!node || !Array.isArray(evidenceRecords) || evidenceRecords.length === 0) {
    return [];
  }

  const nodeId = String(node.id || '').trim();
  const nodeNorm = normalizeEntityId(nodeId);
  const nodeLabelNorm = normalizeEntityId(node.label);
  const nodeTransNorm = normalizeEntityId(node.transliteration);
  const nodeNameNorm = normalizeEntityId(node.name);

  return evidenceRecords.filter((ev) => {
    // 1. Direct ID / passage ID / code match
    const evId = String(ev.id || '').trim();
    const evPassageId = String(ev.passageId || '').trim();
    const evCode = String(ev.code || '').trim();

    if (
      evId === nodeId ||
      evPassageId === nodeId ||
      evCode.toLowerCase() === nodeId.toLowerCase()
    ) {
      return true;
    }

    // 2. Mentioned entities check
    const entities = Array.isArray(ev.entities) ? ev.entities : [];
    for (const ent of entities) {
      const entLabel = typeof ent === 'string' ? ent : (ent?.label || ent?.name || ent?.id || '');
      const entNorm = normalizeEntityId(entLabel);
      if (
        entNorm &&
        (entNorm === nodeNorm ||
          entNorm === nodeLabelNorm ||
          entNorm === nodeTransNorm ||
          entNorm === nodeNameNorm)
      ) {
        return true;
      }
    }

    // 3. Mentioned concepts check
    const concepts = Array.isArray(ev.concepts) ? ev.concepts : [];
    for (const cpt of concepts) {
      const cptLabel = typeof cpt === 'string' ? cpt : (cpt?.label || cpt?.name || cpt?.id || '');
      const cptNorm = normalizeEntityId(cptLabel);
      if (
        cptNorm &&
        (cptNorm === nodeNorm ||
          cptNorm === nodeLabelNorm ||
          cptNorm === nodeTransNorm ||
          cptNorm === nodeNameNorm)
      ) {
        return true;
      }
    }

    // 4. Tiṇai classification match
    if (ev.tinai && (nodeNorm.includes(normalizeEntityId(ev.tinai)) || normalizeEntityId(ev.tinai).includes(nodeNorm))) {
      return true;
    }

    // 5. Proof node linkage
    if (node.isProofTraceNode && node.passageId && (node.passageId === evId || node.passageId === evPassageId)) {
      return true;
    }

    return false;
  });
}

/**
 * Extracts a multi-hop induced neighborhood around a target node.
 * Returns sets of visited node IDs and induced edge IDs.
 *
 * @param {string} centerId - Center node ID.
 * @param {Array<object>} edges - Normalized graph links.
 * @param {number} hops - Neighborhood depth (1, 2, or more).
 * @returns {{ visitedNodeIds: Set<string>, inducedEdgeIds: Set<string>, directNeighborIds: Set<string> }}
 */
export function getInducedSubgraphNeighborhood(centerId, edges, hops = 1) {
  const visitedNodeIds = new Set([String(centerId)]);
  const directNeighborIds = new Set();
  const inducedEdgeIds = new Set();

  if (!centerId || !Array.isArray(edges)) {
    return { visitedNodeIds, inducedEdgeIds, directNeighborIds };
  }

  const effectiveHops = typeof hops === 'number' ? Math.max(1, hops) : 1;
  let currentLevel = [String(centerId)];

  const extractId = (endpoint) => {
    if (!endpoint) return '';
    if (typeof endpoint === 'object') return String(endpoint.id || endpoint);
    return String(endpoint);
  };

  for (let hop = 0; hop < effectiveHops; hop++) {
    const nextLevel = [];
    currentLevel.forEach((curr) => {
      edges.forEach((edge) => {
        const src = extractId(edge.source);
        const tgt = extractId(edge.target);

        if (src === curr) {
          if (hop === 0) directNeighborIds.add(tgt);
          if (!visitedNodeIds.has(tgt)) {
            visitedNodeIds.add(tgt);
            nextLevel.push(tgt);
          }
        } else if (tgt === curr) {
          if (hop === 0) directNeighborIds.add(src);
          if (!visitedNodeIds.has(src)) {
            visitedNodeIds.add(src);
            nextLevel.push(src);
          }
        }
      });
    });
    currentLevel = nextLevel;
  }

  // Collect all edges where both endpoints belong to the visited neighborhood
  edges.forEach((edge) => {
    const src = extractId(edge.source);
    const tgt = extractId(edge.target);
    if (visitedNodeIds.has(src) && visitedNodeIds.has(tgt)) {
      inducedEdgeIds.add(String(edge.id));
    }
  });

  return { visitedNodeIds, inducedEdgeIds, directNeighborIds };
}
