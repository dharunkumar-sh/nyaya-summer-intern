"""
Tamil tokenizer, morphological processor, and lemmatizer for Classical literary texts.

Supports:
- Word-level tokenization preserving Tamil Unicode
- Expanded clitic/suffix splitter
- Deterministic suffix-stripping lemmatizer
- Stopword classification without destroying literary meaning
- Token metadata (is_stopword, is_particle, lemma)
"""
import re
from typing import List, Dict, Any, Optional
from .tamil_normalizer import TamilNormalizer


class TamilTokenizer:
    """Tokenizes Classical Tamil literary texts with morphological awareness."""

    # -------------------------------------------------------------------------
    # 1. Classical Tamil literary particles (never stripped from tokens list)
    # -------------------------------------------------------------------------
    PARTICLES: set = {
        # Emphasizers
        "ஏ", "உம்", "ஓ", "மன்", "கொல்", "தில்", "அந்தில்", "ஆங்கு",
        # Connectors / clitics
        "ஆல்", "இல்", "ஓடு", "கண்", "அது", "அன்", "இன்", "அம்",
        # Interrogatives
        "ஆ", "ஓ", "கொல்",
    }

    # -------------------------------------------------------------------------
    # 2. Extended Classical Tamil stopword list
    #    Grammatical/meta words that carry minimal semantic content
    #    BUT are preserved in `tokens`; removed only from `content_tokens`
    # -------------------------------------------------------------------------
    STOPWORDS: set = {
        # Reporting / quotative
        "என", "என்ற", "என்று", "மொழிப", "என்ப", "என்மனார்",
        "கூறுப", "சொல்லப்படும்", "சொல்லலாம்",
        # Temporal markers (generic)
        "காலைய", "காலை", "முறை",
        # Demonstratives
        "இவை", "அவை", "அவ்வகை", "இவ்வகை", "அத்தகைய",
        # Particles / meta
        "பிறவும்", "தொகைஇ", "செய்தி", "பகுதியொடு",
        "என்ற", "ஆகும்", "ஆகிய", "ஆன",
        # Connectors
        "மற்றும்", "அல்லது", "அதாவது",
        # Verb auxiliaries
        "படும்", "படுவது", "படுவன", "படுமே",
        # Common pronouns (generic)
        "அது", "இது", "அவர்", "இவர்",
        # Relative participle bases
        "ஆகிய", "ஒரு", "பல",
        # Numeral/quantity words not semantically distinctive
        "எண்", "மூன்று", "நான்கு", "ஐந்து",
    }

    # -------------------------------------------------------------------------
    # 3. Suffix-stripping lemmatizer: ordered longest-first
    #    Strips common inflectional/derivational suffixes deterministically
    # -------------------------------------------------------------------------
    SUFFIX_MAP: List[tuple] = sorted([
        # Plural suffixes
        ("கள்", ""),
        ("கன்", ""),
        # Case suffixes (vibhakti)
        ("ஐ", ""),        # accusative
        ("ஆல்", ""),      # instrumental
        ("ஓடு", ""),      # sociative
        ("கண்", ""),      # locative
        ("இல்", ""),      # locative
        ("இற்கு", ""),    # dative
        ("இடம்", ""),     # dative (animate)
        ("நின்று", ""),   # ablative
        ("ஆக", ""),       # adverbial
        ("ஆன", ""),       # adjectival
        ("உடைய", ""),     # genitive
        ("இன்", ""),      # genitive
        # Verbal suffixes
        ("கிறது", ""),    # present
        ("கிறான்", ""),
        ("கிறாள்", ""),
        ("கிறார்", ""),
        ("கின்றது", ""),
        ("கின்றான்", ""),
        ("ந்தது", ""),    # past
        ("ந்தான்", ""),
        ("ந்தாள்", ""),
        ("ந்தார்", ""),
        ("வது", ""),      # future/verbal noun
        ("வான்", ""),
        ("வாள்", ""),
        ("வார்", ""),
        ("தல்", ""),      # verbal noun (infinitive)
        ("அல்", ""),
        # Emphasizers
        ("ஏ", ""),
        ("உம்", ""),
        ("ஓ", ""),
    ], key=lambda x: -len(x[0]))   # longest match first

    # Minimum stem length — never strip below this
    MIN_STEM = 2

    @classmethod
    def lemmatize(cls, word: str) -> str:
        """
        Deterministic suffix-stripping lemmatizer.
        Tries each suffix in order (longest first) and strips the first match
        that leaves a stem of at least MIN_STEM characters.
        Literary meaning is preserved — no dictionary lookup required.
        """
        for suffix, replacement in cls.SUFFIX_MAP:
            if word.endswith(suffix) and len(word) - len(suffix) >= cls.MIN_STEM:
                return word[: len(word) - len(suffix)] + replacement
        return word

    @classmethod
    def split_clitics(cls, word: str) -> List[str]:
        """
        Heuristically segments terminal clitics from a Tamil noun/verb.
        Returns [stem, clitic] or [word] if no clitic found.
        """
        for particle in sorted(cls.PARTICLES, key=len, reverse=True):
            if word.endswith(particle) and len(word) > len(particle) + cls.MIN_STEM:
                stem = word[: len(word) - len(particle)]
                return [stem, particle]
        return [word]

    @classmethod
    def tokenize_words(cls, text: str, remove_stopwords: bool = False) -> List[str]:
        """
        Splits normalized text into word tokens.
        Stopwords are optionally excluded from the returned list.
        """
        clean_text = TamilNormalizer.strip_punctuation(text)
        tokens = [t.strip() for t in clean_text.split() if t.strip()]
        if remove_stopwords:
            tokens = [t for t in tokens if t not in cls.STOPWORDS]
        return tokens

    @classmethod
    def tokenize_with_metadata(
        cls,
        text: str,
        include_lemmas: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Tokenizes text and returns rich token objects:
        {
          "token":       "உரிப்பொருள்",
          "lemma":       "உரிப்பொருள்",
          "is_stopword": False,
          "is_particle": False,
          "position":    2,
        }
        Stopwords are flagged but retained so literary meaning is intact.
        """
        clean_text = TamilNormalizer.strip_punctuation(text)
        raw_tokens = [t.strip() for t in clean_text.split() if t.strip()]

        result: List[Dict[str, Any]] = []
        for pos, tok in enumerate(raw_tokens):
            lemma = cls.lemmatize(tok) if include_lemmas else tok
            result.append({
                "token":       tok,
                "lemma":       lemma,
                "is_stopword": tok in cls.STOPWORDS,
                "is_particle": tok in cls.PARTICLES,
                "position":    pos,
            })
        return result
