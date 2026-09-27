/**
 * Language Detection & Classical Tamil Terminology Preservation Service.
 *
 * Provides resilient, Unicode-aware language detection for user queries
 * (Tamil, English, and Bilingual/Code-mixed), preserves invariant classical
 * literary terminology (Mutalporuḷ, Karupporuḷ, Uripporuḷ, Tiṇai, etc.),
 * and formats canonical citations.
 */

// Curated list of romanized Classical Tamil literary and philosophical tokens
const KNOWN_LITERARY_TERMS = [
  { term: 'tolkappiyam', tamil: 'தொல்காப்பியம்', transliteration: 'Tolkāppiyam' },
  { term: 'porulatikaram', tamil: 'பொருளதிகாரம்', transliteration: 'Poruḷatikāram' },
  { term: 'akattinaiyiyal', tamil: 'அகத்திணையியல்', transliteration: 'Akattiṇaiyiyal' },
  { term: 'purattinaiyiyal', tamil: 'புறத்திணையியல்', transliteration: 'Puṟattiṇaiyiyal' },
  { term: 'mutalporul', tamil: 'முதற்பொருள்', transliteration: 'Mutalporuḷ' },
  { term: 'karupporul', tamil: 'கருப்பொருள்', transliteration: 'Karupporuḷ' },
  { term: 'uripporul', tamil: 'உரிப்பொருள்', transliteration: 'Uripporuḷ' },
  { term: 'kurinci', tamil: 'குறிஞ்சி', transliteration: 'Kuṟiñci' },
  { term: 'kurinji', tamil: 'குறிஞ்சி', transliteration: 'Kuṟiñci' },
  { term: 'mullai', tamil: 'முல்லை', transliteration: 'Mullai' },
  { term: 'marutam', tamil: 'மருதம்', transliteration: 'Marutam' },
  { term: 'marutham', tamil: 'மருதம்', transliteration: 'Marutam' },
  { term: 'neytal', tamil: 'நெய்தல்', transliteration: 'Neytal' },
  { term: 'neythal', tamil: 'நெய்தல்', transliteration: 'Neytal' },
  { term: 'palai', tamil: 'பாலை', transliteration: 'Pālai' },
  { term: 'tinai', tamil: 'திணை', transliteration: 'Tiṇai' },
  { term: 'thinai', tamil: 'திணை', transliteration: 'Tiṇai' },
  { term: 'punartal', tamil: 'புணர்தல்', transliteration: 'Puṇartal' },
  { term: 'iruttal', tamil: 'இருத்தல்', transliteration: 'Iruttal' },
  { term: 'utal', tamil: 'ஊடல்', transliteration: 'Ūṭal' },
  { term: 'oodal', tamil: 'ஊடல்', transliteration: 'Ūṭal' },
  { term: 'irankal', tamil: 'இரங்கல்', transliteration: 'Iraṅkal' },
  { term: 'pirital', tamil: 'பிரிதல்', transliteration: 'Pirital' },
  { term: 'mayon', tamil: 'மாயோன்', transliteration: 'Māyōṉ' },
  { term: 'ceyon', tamil: 'சேயோன்', transliteration: 'Cēyōṉ' },
  { term: 'varunan', tamil: 'வருணன்', transliteration: 'Varuṇaṉ' },
  { term: 'vendan', tamil: 'வேந்தன்', transliteration: 'Vēntaṉ' },
  { term: 'kotravai', tamil: 'கொற்றவை', transliteration: 'Koṟṟavai' },
  { term: 'vyapti', tamil: 'வியாப்தி', transliteration: 'Vyāpti' },
  { term: 'pratijna', tamil: 'பிரதிஞ்ஞா', transliteration: 'Pratijñā' },
  { term: 'hetu', tamil: 'ஹேது', transliteration: 'Hetu' },
  { term: 'udaharana', tamil: 'உதாரணம்', transliteration: 'Udāharaṇa' },
  { term: 'upanaya', tamil: 'உபநயம்', transliteration: 'Upanaya' },
  { term: 'nigamana', tamil: 'நிகமனம்', transliteration: 'Nigamana' },
  { term: 'hetvabhasa', tamil: 'ஹேத்வாபாசம்', transliteration: 'Hetvābhāsa' },
  { term: 'pramana', tamil: 'பிரமாணம்', transliteration: 'Pramāṇa' },
];

function normalizeDiacritics(str) {
  return (str || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
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
    .toLowerCase();
}

/**
 * Detects the language composition and terminology of a user inquiry.
 *
 * @param {string} query - Raw query text.
 * @returns {object} Structured language detection result.
 */
export function detectQueryLanguage(query) {
  if (!query || typeof query !== 'string' || !query.trim()) {
    return {
      code: 'empty',
      label: 'Awaiting Query',
      script: 'None',
      isTamil: false,
      isEnglish: false,
      isBilingual: false,
      hasTamilTerms: false,
      tamilRatio: 0,
      latinRatio: 0,
      scriptBadgeVariant: 'slate',
      detectedTerms: [],
      preservationNote: 'Original language will be preserved without machine translation alteration.',
    };
  }

  const clean = query.trim();

  // Match Tamil Unicode block (U+0B80 to U+0BFF)
  const tamilChars = (clean.match(/[\u0B80-\u0BFF]/g) || []).length;
  // Match standard Latin alphabetical characters
  const latinChars = (clean.match(/[a-zA-Z]/g) || []).length;
  const totalLetters = tamilChars + latinChars;

  // Detect any embedded classical Tamil terminology using diacritic-tolerant word boundaries
  const normalizedQuery = normalizeDiacritics(clean);
  const detectedTerms = KNOWN_LITERARY_TERMS.filter((entry) => {
    if (clean.includes(entry.tamil)) return true;
    const termNorm = normalizeDiacritics(entry.term);
    const regex = new RegExp(`(^|[^a-zA-Z0-9])${termNorm}([^a-zA-Z0-9]|$)`, 'i');
    return regex.test(normalizedQuery);
  });

  const tamilRatio = totalLetters > 0 ? tamilChars / totalLetters : 0;
  const latinRatio = totalLetters > 0 ? latinChars / totalLetters : 0;

  // 1. Pure or Predominantly Tamil Query (≥75% Tamil characters or zero Latin)
  if (tamilChars > 0 && (latinChars === 0 || tamilRatio >= 0.75)) {
    return {
      code: 'ta',
      label: 'தமிழ் (Tamil)',
      script: 'Tamil Unicode',
      isTamil: true,
      isEnglish: false,
      isBilingual: false,
      hasTamilTerms: true,
      tamilRatio: Math.round(tamilRatio * 100),
      latinRatio: Math.round(latinRatio * 100),
      scriptBadgeVariant: 'purple',
      detectedTerms,
      preservationNote: 'Original Tamil script preserved. Generated synthesis incorporates formal Poruḷatikāram epistemic terminology.',
    };
  }

  // 2. Bilingual / Code-mixed Query (Both Tamil Unicode & Latin present)
  if (tamilChars > 0 && latinChars > 0) {
    return {
      code: 'bilingual',
      label: 'Bilingual (தமிழ் / English)',
      script: 'Bilingual Code-mixed',
      isTamil: true,
      isEnglish: true,
      isBilingual: true,
      hasTamilTerms: true,
      tamilRatio: Math.round(tamilRatio * 100),
      latinRatio: Math.round(latinRatio * 100),
      scriptBadgeVariant: 'indigo',
      detectedTerms,
      preservationNote: 'Bilingual inquiry detected. Original Tamil verses preserved alongside parallel transliterated terminology.',
    };
  }

  // 3. English Query with Classical Tamil Terminology
  if (detectedTerms.length > 0) {
    return {
      code: 'en',
      label: 'English (Classical Terminology)',
      script: 'Latin with Literary Terms',
      isTamil: false,
      isEnglish: true,
      isBilingual: false,
      hasTamilTerms: true,
      tamilRatio: 0,
      latinRatio: 100,
      scriptBadgeVariant: 'blue',
      detectedTerms,
      preservationNote: 'English inquiry grounded on Classical Tamil literary concepts. Terminology preserved in original transliteration.',
    };
  }

  // 4. Pure English Query
  return {
    code: 'en',
    label: 'English',
    script: 'Latin',
    isTamil: false,
    isEnglish: true,
    isBilingual: false,
    hasTamilTerms: false,
    tamilRatio: 0,
    latinRatio: 100,
    scriptBadgeVariant: 'blue',
    detectedTerms: [],
    preservationNote: 'English inquiry. Retrieved sūtras presented in authentic Classical Tamil with secondary English translation.',
  };
}

/**
 * Formats a canonical source citation string from an evidence record.
 * Example: "Tolkāppiyam • Poruḷatikāram • Akattiṇaiyiyal • Sūtra 5"
 *
 * @param {object} item - Evidence item or sūtra record.
 * @returns {string} Fully articulated citation.
 */
export function formatSourceCitation(item) {
  if (!item) return 'Tolkāppiyam';
  const parts = [];

  const work = item.work || item.source || 'Tolkāppiyam';
  parts.push(work);

  const section = item.rawSection || item.section;
  if (section && section !== work) {
    parts.push(section);
  }

  if (item.chapter && item.chapter !== section) {
    parts.push(item.chapter);
  }

  if (item.sutraNumber !== null && item.sutraNumber !== undefined) {
    parts.push(`Sūtra ${item.sutraNumber}`);
  } else if (item.sutra_number !== null && item.sutra_number !== undefined) {
    parts.push(`Sūtra ${item.sutra_number}`);
  }

  if (item.tinai && item.tinai !== 'General' && item.tinai !== 'all') {
    parts.push(`[${item.tinai}]`);
  }

  return parts.join(' • ');
}

/**
 * Canonical dictionary of core Tolkāppiyam literary and Nyāya philosophical terms.
 */
export const CANONICAL_TAMIL_TERMINOLOGY = {
  mutalporul: {
    tamil: 'முதற்பொருள்',
    transliteration: 'Mutalporuḷ',
    definition: 'Primary spatio-temporal ground: Land (Nilam) and Time/Season (Pōḻutu).',
    category: 'Akattinai Triad',
  },
  karupporul: {
    tamil: 'கருப்பொருள்',
    transliteration: 'Karupporuḷ',
    definition: 'Biotic, ecological, and cultural signifiers: Deities, fauna, flora, instruments, and occupations.',
    category: 'Akattinai Triad',
  },
  uripporul: {
    tamil: 'உரிப்பொருள்',
    transliteration: 'Uripporuḷ',
    definition: 'Essential psychological mood and emotional interiority appropriate to each landscape.',
    category: 'Akattinai Triad',
  },
  kurinci: {
    tamil: 'குறிஞ்சி',
    transliteration: 'Kuṟiñci',
    definition: 'Montane landscape of clandestine union (Puṇartal) presided over by Cēyōṉ.',
    category: 'Aintinai',
  },
  mullai: {
    tamil: 'முல்லை',
    transliteration: 'Mullai',
    definition: 'Pastoral forest landscape of patient domestic waiting (Iruttal) presided over by Māyōṉ.',
    category: 'Aintinai',
  },
  marutam: {
    tamil: 'மருதம்',
    transliteration: 'Marutam',
    definition: 'Riverine agricultural landscape of lover\'s sulking (Ūṭal) presided over by Vēntaṉ.',
    category: 'Aintinai',
  },
  neytal: {
    tamil: 'நெய்தல்',
    transliteration: 'Neytal',
    definition: 'Maritime coastal seashore landscape of poignant pining (Iraṅkal) presided over by Varuṇaṉ.',
    category: 'Aintinai',
  },
  palai: {
    tamil: 'பாலை',
    transliteration: 'Pālai',
    definition: 'Arid scrubland landscape of separation (Pirital) presided over by Koṟṟavai.',
    category: 'Aintinai',
  },
  vyapti: {
    tamil: 'வியாப்தி',
    transliteration: 'Vyāpti',
    definition: 'Universal invariant relation of invariable concomitance between signifier and signified.',
    category: 'Nyaya Epistemology',
  },
};
