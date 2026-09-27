/**
 * Real-time Confidence Score Validation Service for Classical Tamil Epistemic Reasoner.
 *
 * Implements client-side dynamic confidence calculation and server synchronization
 * across the complete retrieval and reasoning pipeline.
 *
 * Evaluates 6 dynamic dimensions (Total Weight = 1.0):
 *  1. Evidence Relevance (0.20)
 *  2. Source Provenance (0.15)
 *  3. Retrieval Strength (0.15)
 *  4. Premise Support (0.15)
 *  5. Reasoning Consistency (0.20)
 *  6. Validation Status (0.15)
 *
 * Enforces strict epistemic gating:
 *  - Zero evidence -> Score = 0.0
 *  - Insufficient evidence (< 2 passages) -> Capped at <= 0.25
 *  - Ungrounded Vyāpti -> Capped at <= 0.30
 *  - Unsupported conclusion -> Capped at <= 0.25
 *  - Conflicting / Cross-tiṇai evidence -> Penalized up to -0.45
 *  - Weak relevance (< 0.45) -> Penalized up to -0.25
 */

import { http } from './apiClient';

export const CONFIDENCE_LEVELS = {
  VERY_HIGH: {
    level: 'VERY_HIGH',
    labelTamil: 'ஐயமற நிறுவப்பட்டது',
    labelEnglish: 'Conclusively Established',
    description: 'Universal canonical invariance with sound multi-source cross-verification.',
    minScore: 0.85,
    badgeVariant: 'green',
    colorHex: '#059669',
    bgColor: 'bg-emerald-50 text-emerald-800 border-emerald-300',
  },
  HIGH: {
    level: 'HIGH',
    labelTamil: 'நம்பகமான முடிவு',
    labelEnglish: 'Robust Canonical Grounding',
    description: 'High-relevance canonical sūtras with consistent Nyāya premise alignment.',
    minScore: 0.70,
    badgeVariant: 'blue',
    colorHex: '#2563eb',
    bgColor: 'bg-blue-50 text-blue-800 border-blue-300',
  },
  MODERATE: {
    level: 'MODERATE',
    labelTamil: 'மிதமான உறுதிப்பாடு',
    labelEnglish: 'Plausible Inference',
    description: 'Satisfactory evidence with slight cross-source divergence or single-channel retrieval.',
    minScore: 0.50,
    badgeVariant: 'orange',
    colorHex: '#d97706',
    bgColor: 'bg-amber-50 text-amber-800 border-amber-300',
  },
  LOW: {
    level: 'LOW',
    labelTamil: 'குறைந்த உறுதிப்பாடு',
    labelEnglish: 'Weak Epistemic Basis',
    description: 'Weak textual relevance or unverified inferential leaps requiring caution.',
    minScore: 0.25,
    badgeVariant: 'amber',
    colorHex: '#ea580c',
    bgColor: 'bg-orange-50 text-orange-800 border-orange-300',
  },
  INSUFFICIENT: {
    level: 'INSUFFICIENT',
    labelTamil: 'சான்றாதாரமற்றது',
    labelEnglish: 'Insufficient / Defeasible Grounding',
    description: 'Inadequate canonical passages to ground formal Nyāya deduction without speculation.',
    minScore: 0.0,
    badgeVariant: 'slate',
    colorHex: '#dc2626',
    bgColor: 'bg-red-50 text-red-800 border-red-300',
  },
};

export const FACTOR_METADATA = {
  evidence_relevance: {
    name: 'Evidence Relevance',
    tamilName: 'பொருத்தப்பாடு',
    weight: 0.20,
    description: 'Weighted semantic similarity, lexical overlap, and score margin across retrieved passages.',
  },
  source_provenance: {
    name: 'Source Provenance',
    tamilName: 'மூல நூலின் நம்பகத்தன்மை',
    weight: 0.15,
    description: 'Authenticity of primary Tolkāppiyam Poruḷatikāram sūtra citations and structural hierarchy.',
  },
  retrieval_strength: {
    name: 'Retrieval Strength',
    tamilName: 'மீட்பு உறுதிப்பாடு',
    weight: 0.15,
    description: 'Multi-channel consensus across Semantic Vector, BM25 Lexical, and Graph Traversal.',
  },
  premise_support: {
    name: 'Premise Support',
    tamilName: 'மேற்கோள் சான்றுறுதி',
    weight: 0.15,
    description: 'Grounding of formulated premises in verified passage IDs and Mutal/Karu/Uri poetics.',
  },
  reasoning_consistency: {
    name: 'Reasoning Consistency',
    tamilName: 'நியாய முறைமை நெறி',
    weight: 0.20,
    description: 'Universal invariable concomitance (Vyāpti) and absence of Hetvābhāsa fallacies.',
  },
  validation_status: {
    name: 'Validation Status',
    tamilName: 'ஐந்தங்கச் சரிபார்ப்பு',
    weight: 0.15,
    description: 'Defeasible five-point criteria satisfaction across Pañcāvayava steps.',
  },
};

/**
 * Determine the qualitative confidence level from a raw confidence score [0.0, 1.0].
 */
export function getConfidenceLevel(score) {
  const num = typeof score === 'number' && !Number.isNaN(score) ? score : 0.0;
  if (num >= 0.85) return CONFIDENCE_LEVELS.VERY_HIGH;
  if (num >= 0.70) return CONFIDENCE_LEVELS.HIGH;
  if (num >= 0.50) return CONFIDENCE_LEVELS.MODERATE;
  if (num >= 0.25) return CONFIDENCE_LEVELS.LOW;
  return CONFIDENCE_LEVELS.INSUFFICIENT;
}

/**
 * Evaluates real-time confidence dynamically on the client side.
 * Mirrors `ConfidenceEvaluator.evaluate(...)` in Python for zero-latency UI responsiveness.
 *
 * @param {Object} params
 * @param {string} [params.query]
 * @param {Array} [params.evidenceRecords]
 * @param {string|null} [params.selectedEvidenceId]
 * @param {Array} [params.graphNodes]
 * @param {string|null} [params.selectedGraphNodeId]
 * @param {Array} [params.reasoningStages]
 * @param {Array} [params.premises]
 * @param {Object|null} [params.vyaptiRule]
 * @param {Object|null} [params.validationResults]
 * @param {Object|null} [params.finalAnswer]
 * @param {string|null} [params.tinai]
 * @param {boolean} [params.insufficientEvidence]
 * @returns {Object} Complete confidence evaluation report
 */
export function calculateClientConfidence({
  query = '',
  evidenceRecords = [],
  selectedEvidenceId = null,
  graphNodes = [],
  selectedGraphNodeId = null,
  reasoningStages = [],
  premises = [],
  vyaptiRule = null,
  validationResults = null,
  finalAnswer = null,
  tinai = null,
  insufficientEvidence = false,
} = {}) {
  const records = Array.isArray(evidenceRecords) ? evidenceRecords : [];
  const count = records.length;

  // 1. Zero evidence guard
  if (count === 0 || insufficientEvidence || finalAnswer?.status === 'insufficient_evidence') {
    return createInsufficientReport({
      reason: 'No canonical Tolkāppiyam evidence passages retrieved to ground Nyāya deduction.',
      penaltyCode: 'P_ZERO_EVIDENCE',
      gatingMultiplier: 0.0,
      records,
    });
  }

  // ---------------------------------------------------------
  // 1. Evidence Relevance Factor (Weight 0.20)
  // ---------------------------------------------------------
  const scores = records.map((r) => {
    const raw = r.score ?? r.relevance_score ?? r.confidenceScore ?? r.confidence;
    return typeof raw === 'number' && !Number.isNaN(raw) ? raw : 0.5;
  });
  const topRelevance = scores.length > 0 ? Math.max(...scores) : 0.0;
  const meanRelevance = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0.0;

  // Selected evidence boost or active focus adjustment
  let selectedBonus = 0.0;
  if (selectedEvidenceId) {
    const sel = records.find((r) => r.id === selectedEvidenceId || r.code === selectedEvidenceId);
    if (sel) {
      const selScore = sel.score ?? sel.relevance_score ?? 0.8;
      selectedBonus = Math.min(0.05, selScore * 0.05);
    }
  }

  // Query keyword overlap bonus
  const cleanQ = String(query || '').trim().toLowerCase();
  let queryBonus = 0.0;
  if (cleanQ) {
    const qWords = cleanQ.split(/\s+/).filter((w) => w.length > 2);
    let matched = 0;
    records.forEach((r) => {
      const txt = `${r.tamilText || ''} ${r.translation || ''} ${r.reference || ''}`.toLowerCase();
      qWords.forEach((w) => {
        if (txt.includes(w)) matched++;
      });
    });
    if (qWords.length > 0 && matched > 0) {
      queryBonus = Math.min(0.04, (matched / (qWords.length * count)) * 0.04);
    }
  }

  const rawRelevanceScore = Math.min(1.0, Math.max(0.0, (topRelevance * 0.6 + meanRelevance * 0.4) + selectedBonus + queryBonus));
  const relevanceFactor = {
    factor_name: 'evidence_relevance',
    weight: 0.20,
    raw_score: Number(rawRelevanceScore.toFixed(4)),
    weighted_score: Number((rawRelevanceScore * 0.20).toFixed(4)),
    status: rawRelevanceScore >= 0.70 ? 'PASS' : rawRelevanceScore >= 0.45 ? 'MODERATE' : 'WEAK',
    details: `Top relevance ${topRelevance.toFixed(2)}, mean ${meanRelevance.toFixed(2)} across ${count} verses.`,
  };

  // ---------------------------------------------------------
  // 2. Source Provenance Factor (Weight 0.15)
  // ---------------------------------------------------------
  let primaryCount = 0;
  let canonicalCitations = 0;
  records.forEach((r) => {
    const work = String(r.work || r.source || '').toLowerCase();
    const section = String(r.section || r.chapter || '').toLowerCase();
    const ref = String(r.reference || '').toLowerCase();
    if (work.includes('tolkappiyam') || work.includes('தொல்காப்பியம்') || ref.includes('sūtra') || ref.includes('sutra') || ref.includes('tol-')) {
      primaryCount++;
    }
    if (section.includes('porul') || section.includes('பொருள்') || section.includes('akam') || section.includes('அகம்') || ref.includes('akam')) {
      canonicalCitations++;
    }
  });

  const primaryRatio = count > 0 ? primaryCount / count : 0.0;
  const citationRatio = count > 0 ? canonicalCitations / count : 0.0;
  const rawProvenanceScore = Math.min(1.0, Math.max(0.0, primaryRatio * 0.6 + citationRatio * 0.4));
  const provenanceFactor = {
    factor_name: 'source_provenance',
    weight: 0.15,
    raw_score: Number(rawProvenanceScore.toFixed(4)),
    weighted_score: Number((rawProvenanceScore * 0.15).toFixed(4)),
    status: rawProvenanceScore >= 0.75 ? 'PASS' : 'PARTIAL',
    details: `${primaryCount}/${count} primary Tolkāppiyam citations with canonical Poruḷatikāram grounding.`,
  };

  // ---------------------------------------------------------
  // 3. Retrieval Strength Factor (Weight 0.15)
  // ---------------------------------------------------------
  const channelSet = new Set();
  records.forEach((r) => {
    const badges = Array.isArray(r.badges) ? r.badges : [];
    badges.forEach((b) => {
      const lbl = String(b.label || b).toLowerCase();
      if (lbl.includes('vector') || lbl.includes('semantic')) channelSet.add('semantic');
      if (lbl.includes('bm25') || lbl.includes('lexical') || lbl.includes('keyword')) channelSet.add('bm25');
      if (lbl.includes('graph') || lbl.includes('traversal')) channelSet.add('graph');
    });
    if (r.retrieval_method) channelSet.add(String(r.retrieval_method).toLowerCase());
  });

  // Graph traversal boost if graphNodes exist or graph node focus is selected
  if ((Array.isArray(graphNodes) && graphNodes.length > 0) || selectedGraphNodeId) {
    channelSet.add('graph');
  }

  const consensusMultiplier = channelSet.size >= 3 ? 1.0 : channelSet.size === 2 ? 0.85 : 0.65;
  const volumeScore = Math.min(1.0, count / 4.0);
  const rawRetrievalScore = Math.min(1.0, Math.max(0.0, volumeScore * 0.5 + consensusMultiplier * 0.5));
  const retrievalFactor = {
    factor_name: 'retrieval_strength',
    weight: 0.15,
    raw_score: Number(rawRetrievalScore.toFixed(4)),
    weighted_score: Number((rawRetrievalScore * 0.15).toFixed(4)),
    status: channelSet.size >= 2 ? 'PASS' : 'MODERATE',
    details: `${channelSet.size}-channel consensus (${Array.from(channelSet).join(', ') || 'default'}) across ${count} verses.`,
  };

  // ---------------------------------------------------------
  // 4. Premise Support Factor (Weight 0.15)
  // ---------------------------------------------------------
  const premiseList = Array.isArray(premises) && premises.length > 0
    ? premises
    : (Array.isArray(reasoningStages) ? reasoningStages.filter((s) => s.stageNumber <= 2) : []);

  let groundedPremises = 0;
  premiseList.forEach((p) => {
    if (p.linkedEvidenceId || p.groundedPassageId || p.epistemicGrounding || p.passage_id) {
      groundedPremises++;
    }
  });

  const premiseRatio = premiseList.length > 0 ? groundedPremises / premiseList.length : (count >= 2 ? 0.90 : 0.40);
  const rawPremiseScore = Math.min(1.0, Math.max(0.0, premiseRatio));
  const premiseFactor = {
    factor_name: 'premise_support',
    weight: 0.15,
    raw_score: Number(rawPremiseScore.toFixed(4)),
    weighted_score: Number((rawPremiseScore * 0.15).toFixed(4)),
    status: rawPremiseScore >= 0.70 ? 'PASS' : 'WEAK',
    details: `${groundedPremises}/${premiseList.length || 2} premises supported by verified passage identifiers.`,
  };

  // ---------------------------------------------------------
  // 5. Reasoning Consistency Factor (Weight 0.20)
  // ---------------------------------------------------------
  let hasVyapti = Boolean(vyaptiRule);
  if (!hasVyapti && Array.isArray(reasoningStages)) {
    const udaharana = reasoningStages.find((s) => String(s.sanskritName || '').toLowerCase().includes('udaharana') || s.stageNumber === 3);
    if (udaharana && udaharana.formalLogic && !udaharana.formalLogic.includes('UNAVAILABLE')) {
      hasVyapti = true;
    }
  }

  // Check Hetvābhāsa fallacies in validationResults
  const fallacies = validationResults?.fallacies || {};
  const asiddha = Number(fallacies.asiddha || 0.0);
  const viruddha = Number(fallacies.viruddha || 0.0);
  const savyabhicara = Number(fallacies.savyabhicara || 0.0);
  const satpratipaksa = Number(fallacies.satpratipaksa || 0.0);
  const badhita = Number(fallacies.badhita || 0.0);

  const totalFallacyScore = asiddha + viruddha + savyabhicara + satpratipaksa + badhita;
  const fallacyDeduction = Math.min(0.60, totalFallacyScore * 0.30);

  let rawConsistencyScore = hasVyapti ? 1.0 - fallacyDeduction : 0.0;
  rawConsistencyScore = Math.min(1.0, Math.max(0.0, rawConsistencyScore));

  const consistencyFactor = {
    factor_name: 'reasoning_consistency',
    weight: 0.20,
    raw_score: Number(rawConsistencyScore.toFixed(4)),
    weighted_score: Number((rawConsistencyScore * 0.20).toFixed(4)),
    status: hasVyapti && totalFallacyScore === 0 ? 'PASS' : hasVyapti ? 'MODERATE' : 'FAIL',
    details: hasVyapti
      ? totalFallacyScore === 0
        ? 'Universal Vyāpti established with 0 Hetvābhāsa fallacies detected.'
        : `Vyāpti active with fallacy penalty (-${(fallacyDeduction * 100).toFixed(0)}%).`
      : 'No invariable Vyāpti rule established from canonical corpus.',
  };

  // ---------------------------------------------------------
  // 6. Validation Status Factor (Weight 0.15)
  // ---------------------------------------------------------
  const checks = Array.isArray(validationResults?.checks) ? validationResults.checks : [];
  let passedChecks = 0;
  checks.forEach((c) => {
    if (c.status === 'PASS' || c.passed === true) passedChecks++;
  });

  let rawValidationScore = checks.length > 0
    ? passedChecks / checks.length
    : (validationResults?.soundnessScore ?? (hasVyapti && count >= 2 ? 0.95 : 0.50));

  rawValidationScore = Math.min(1.0, Math.max(0.0, rawValidationScore));
  const validationFactor = {
    factor_name: 'validation_status',
    weight: 0.15,
    raw_score: Number(rawValidationScore.toFixed(4)),
    weighted_score: Number((rawValidationScore * 0.15).toFixed(4)),
    status: rawValidationScore >= 0.80 ? 'PASS' : 'PARTIAL',
    details: `${passedChecks}/${checks.length || 5} defeasible checks passed (Pratijñā, Hetu, Udāharaṇa, Upanaya, Nigamana).`,
  };

  // ---------------------------------------------------------
  // Epistemic Penalties & Strict Gating Rules
  // ---------------------------------------------------------
  const penalties = [];
  let gatingMultiplier = 1.0;

  // Rule A: Insufficient evidence count (< 2 canonical passages)
  if (count < 2) {
    penalties.push({
      penalty_name: 'P_INSUFFICIENT_EVIDENCE',
      deduction: 0.35,
      reason: `Only ${count} passage retrieved; at least 2 are required to formulate universal Vyāpti.`,
      cap: 0.25,
    });
    gatingMultiplier = Math.min(gatingMultiplier, 0.25);
  }

  // Rule B: Ungrounded Vyāpti
  if (!hasVyapti) {
    penalties.push({
      penalty_name: 'P_UNGROUNDED_VYAPTI',
      deduction: 0.25,
      reason: 'No universal invariable concomitance rule found; speculative syllogism blocked.',
      cap: 0.30,
    });
    gatingMultiplier = Math.min(gatingMultiplier, 0.30);
  }

  // Rule C: Conflicting evidence / Cross-tiṇai discordance
  const tinais = new Set();
  records.forEach((r) => {
    if (r.tinai && r.tinai !== 'General' && r.tinai !== 'all') {
      tinais.add(r.tinai);
    }
  });
  const targetTinai = tinai && tinai !== 'all' ? tinai : null;
  const isTargetDiscordant = Boolean(targetTinai && tinais.size > 1 && !tinais.has(targetTinai));
  if (tinais.size >= 3 || viruddha > 0 || isTargetDiscordant) {
    const ded = viruddha > 0 ? 0.30 : isTargetDiscordant ? 0.20 : 0.15;
    penalties.push({
      penalty_name: 'P_CONFLICTING_EVIDENCE',
      deduction: ded,
      reason: isTargetDiscordant
        ? `Evidence exhibits discordance with requested ${targetTinai} habitat (${Array.from(tinais).join(', ')}).`
        : `Cross-tiṇai discordance across ${tinais.size} habitats or Viruddha contradictory evidence detected.`,
      cap: null,
    });
  }

  // Rule D: Weak relevance
  if (meanRelevance < 0.45) {
    penalties.push({
      penalty_name: 'P_WEAK_RELEVANCE',
      deduction: 0.20,
      reason: `Mean relevance (${meanRelevance.toFixed(2)}) is below the required 0.45 canonical threshold.`,
      cap: null,
    });
  }

  // Aggregate weighted base score
  const baseScore =
    relevanceFactor.weighted_score +
    provenanceFactor.weighted_score +
    retrievalFactor.weighted_score +
    premiseFactor.weighted_score +
    consistencyFactor.weighted_score +
    validationFactor.weighted_score;

  // Apply additive deductions
  let penaltySum = 0.0;
  penalties.forEach((p) => {
    penaltySum += p.deduction;
  });

  let adjustedScore = Math.max(0.0, baseScore - penaltySum);

  // Apply strict gating cap
  if (gatingMultiplier < 1.0) {
    adjustedScore = Math.min(adjustedScore, gatingMultiplier);
  }

  // Final bounding [0.0, 1.0]
  const finalScore = Number(Math.min(1.0, Math.max(0.0, adjustedScore)).toFixed(4));
  const stars = Number(Math.max(0.0, Math.min(5.0, finalScore * 5.0)).toFixed(1));
  const levelObj = getConfidenceLevel(finalScore);

  return {
    confidenceScore: finalScore,
    confidencePercentage: Math.round(finalScore * 100),
    confidenceStars: stars,
    confidenceLevel: levelObj.level,
    levelInfo: levelObj,
    isSufficient: finalScore >= 0.25 && count >= 2,
    factors: {
      evidence_relevance: relevanceFactor,
      source_provenance: provenanceFactor,
      retrieval_strength: retrievalFactor,
      premise_support: premiseFactor,
      reasoning_consistency: consistencyFactor,
      validation_status: validationFactor,
    },
    penalties,
    gatingMultiplier,
    timestamp: Date.now(),
    evidenceCount: count,
  };
}

/**
 * Creates an explicit insufficient report for empty or defeasible states.
 */
function createInsufficientReport({ reason, penaltyCode, gatingMultiplier = 0.0, records = [] }) {
  const levelObj = CONFIDENCE_LEVELS.INSUFFICIENT;
  return {
    confidenceScore: 0.0,
    confidencePercentage: 0,
    confidenceStars: 0.0,
    confidenceLevel: levelObj.level,
    levelInfo: levelObj,
    isSufficient: false,
    factors: {
      evidence_relevance: {
        factor_name: 'evidence_relevance',
        weight: 0.20,
        raw_score: 0.0,
        weighted_score: 0.0,
        status: 'FAIL',
        details: reason,
      },
      source_provenance: {
        factor_name: 'source_provenance',
        weight: 0.15,
        raw_score: 0.0,
        weighted_score: 0.0,
        status: 'FAIL',
        details: 'No verified canonical Tolkāppiyam citations available.',
      },
      retrieval_strength: {
        factor_name: 'retrieval_strength',
        weight: 0.15,
        raw_score: 0.0,
        weighted_score: 0.0,
        status: 'FAIL',
        details: 'Multi-channel retrieval returned 0 grounded passages.',
      },
      premise_support: {
        factor_name: 'premise_support',
        weight: 0.15,
        raw_score: 0.0,
        weighted_score: 0.0,
        status: 'FAIL',
        details: 'Premises cannot be formulated without primary source text.',
      },
      reasoning_consistency: {
        factor_name: 'reasoning_consistency',
        weight: 0.20,
        raw_score: 0.0,
        weighted_score: 0.0,
        status: 'FAIL',
        details: 'Universal Vyāpti cannot be induced from zero evidence.',
      },
      validation_status: {
        factor_name: 'validation_status',
        weight: 0.15,
        raw_score: 0.0,
        weighted_score: 0.0,
        status: 'FAIL',
        details: 'Epistemic validation blocked by insufficiency guard.',
      },
    },
    penalties: [
      {
        penalty_name: penaltyCode,
        deduction: 1.0,
        reason,
        cap: 0.0,
      },
    ],
    gatingMultiplier,
    timestamp: Date.now(),
    evidenceCount: records.length,
  };
}

/**
 * Validates confidence with the backend Flask API asynchronously.
 * Falls back gracefully to `calculateClientConfidence` if offline or timeout occurs.
 */
export async function validateConfidenceOnServer(payload, { signal = null, timeoutMs = 8000 } = {}) {
  try {
    const res = await http.post('/api/reasoning/confidence/validate', payload, { signal, timeoutMs });
    if (res?.success && res?.data) {
      const data = res.data;
      const levelObj = getConfidenceLevel(data.confidenceScore || data.confidence_score);
      return {
        ...data,
        confidenceScore: data.confidenceScore ?? data.confidence_score ?? 0.0,
        confidencePercentage: Math.round((data.confidenceScore ?? data.confidence_score ?? 0.0) * 100),
        confidenceStars: data.confidenceStars ?? data.confidence_stars ?? 0.0,
        confidenceLevel: levelObj.level,
        levelInfo: levelObj,
        isSufficient: data.isSufficient ?? data.is_sufficient ?? false,
      };
    }
  } catch (err) {
    console.warn('Backend confidence validation failed, using client evaluator:', err.message);
  }

  // Fallback to client evaluator
  return calculateClientConfidence(payload);
}
