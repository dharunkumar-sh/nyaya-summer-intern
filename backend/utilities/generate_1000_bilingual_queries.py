"""
Utility script to generate exactly 1000 high-quality mixed Tamil and English queries
based on Ontology.csv (1,000 canonical concepts) and Query_Mapping.csv (2,640 query records).
Saves output to:
- src/data/canonical_1000_queries.json
- public/data/canonical_1000_queries.json
- backend/data/processed/canonical_1000_queries.json
"""

import csv
import json
import os
import re
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ONTOLOGY_CSV = ROOT_DIR / "backend" / "data" / "raw" / "Ontology.csv"
QUERY_MAPPING_CSV = ROOT_DIR / "backend" / "dataset" / "Query_Mapping.csv"

SRC_DATA_DIR = ROOT_DIR / "src" / "data"
PUBLIC_DATA_DIR = ROOT_DIR / "public" / "data"
BACKEND_DATA_DIR = ROOT_DIR / "backend" / "data" / "processed"

SRC_DATA_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKEND_DATA_DIR.mkdir(parents=True, exist_ok=True)

TAMIL_REGEX = re.compile(r"[\u0B80-\u0BFF]")

THEME_MAPPINGS = {
    "Grammar": "Grammar (இலக்கணம்)",
    "Porul": "Poetics & Semiotics (பொருளதிகாரம்)",
    "Akam": "Akam Interior Love (அகத்திணை)",
    "Puram": "Puram Heroics & Society (புறத்திணை)",
    "Culture": "Culture & Ethics (அறம் மற்றும் பண்பாடு)",
    "Language": "Linguistic Philosophy (மொழி தத்துவம்)",
    "Meta": "Epistemic Meta-Framework (மெய்யியல்)",
    "Commentary": "Commentary & Hermeneutics (உரை மரபு)",
    "Literature": "Sangam Literature (சங்க இலக்கியம்)",
}

QUESTION_TEMPLATES = [
    # How / Process
    (
        "How / Process",
        "How does {tamil} ({english}) operate through {relation} within Tolkāppiyam {theme}?",
        "தொல்காப்பிய {tamil_theme} அமைப்பில் {tamil} ({english}) எவ்வாறு இயங்குகிறது?",
    ),
    (
        "How / Process",
        "How is {tamil} ({english}) structurally linked to {parent} through {relation} in classical Tamil poetics?",
        "{tamil} ({english}) மற்றும் {tamil_parent} இடையேயான தொடர்பு எவ்வாறு வெளிப்படுகிறது?",
    ),
    (
        "How / Process",
        "In what manner does {tamil} ({english}) govern epistemic relations in {theme} literature?",
        "செவ்வியல் தமிழ் மரபில் {tamil} ({english}) எவ்வாறு பொருண்மையை விளக்குகிறது?",
    ),
    # Why / Justification
    (
        "Why / Justification",
        "Why is {tamil} ({english}) considered a foundational concept in Tolkāppiyam {theme}?",
        "தொல்காப்பியத்தில் {tamil} ({english}) முதன்மையான கருத்தாக அமைவது ஏன்?",
    ),
    (
        "Why / Justification",
        "What epistemic justification grounds {tamil} ({english}) under the {category} framework?",
        "{category} நெறியில் {tamil} ({english}) அமைவதற்கான சான்று மற்றும் காரணம் யாது?",
    ),
    (
        "Why / Justification",
        "Why does classical poetics treat {tamil} ({english}) as having a {relation} relation with {parent}?",
        "{tamil} ({english}) எவ்வாறு {parent} உடனும் {relation} தொடர்பிலும் அமைகிறது?",
    ),
    # What / Fact
    (
        "What / Fact",
        "What are the defining characteristics and poetic manifestations of {tamil} ({english}) in Tolkāppiyam?",
        "தொல்காப்பிய நெறியில் {tamil} ({english}) என்பதன் இலக்கணமும் பொருட்பண்பும் யாவை?",
    ),
    (
        "What / Fact",
        "What is the canonical role of {tamil} ({english}) in ancient Tamil {theme} tradition?",
        "பண்டைத் தமிழ் {tamil_theme} மரபில் {tamil} ({english}) வகிக்கும் இடம் என்ன?",
    ),
    (
        "What / Fact",
        "What canonical sutra principles govern {tamil} ({english}) and its associated {relation} relation?",
        "{tamil} ({english}) கோட்பாட்டை வரையறுக்கும் தொல்காப்பிய விதி யாது?",
    ),
    # Who / Entity
    (
        "Who / Entity",
        "What entity, archetype, or expressive agent embodies {tamil} ({english}) in classical Tolkāppiyam verses?",
        "தொல்காப்பிய செய்யுள்களில் {tamil} ({english}) யாரால் அல்லது எதனால் வெளிப்படுத்தப்படுகிறது?",
    ),
]


def clean_str(s):
    if not s:
        return ""
    return str(s).strip()


def run():
    print("Reading Ontology.csv...")
    with open(ONTOLOGY_CSV, mode="r", encoding="utf-8", errors="ignore") as f:
        ont_rows = list(csv.DictReader(f))

    print(f"Loaded {len(ont_rows)} ontology concepts.")

    print("Reading Query_Mapping.csv...")
    with open(QUERY_MAPPING_CSV, mode="r", encoding="utf-8", errors="ignore") as f:
        qm_rows = list(csv.DictReader(f))

    print(f"Loaded {len(qm_rows)} query mapping records.")

    # Index QM rows by lowercase Thinai / Type and Tamil / English
    qm_by_concept = {}
    for r in qm_rows:
        t = clean_str(r.get("Thinai / Type")).lower()
        q = clean_str(r.get("Example User Query"))
        if t and q and TAMIL_REGEX.search(q) and any(c.isascii() and c.isalpha() for c in q):
            qm_by_concept.setdefault(t, []).append(r)

    results = []

    for idx, ont in enumerate(ont_rows):
        cid = int(ont.get("ID", idx + 1))
        theme_raw = clean_str(ont.get("Main Theme", "Literature"))
        eng_label = clean_str(ont.get("English_Label", f"Concept {cid}"))
        tam_label = clean_str(ont.get("Tamil_Label", eng_label))
        cat_raw = clean_str(ont.get("Category", theme_raw))
        parent = clean_str(ont.get("Parent_Concept", "Tolkappiyam"))
        child = clean_str(ont.get("Child_Concepts", ""))
        rel = clean_str(ont.get("Relation_Type", "associated_with"))
        desc = clean_str(ont.get("Description", ""))
        keywords_str = clean_str(ont.get("Keywords", ""))
        domain = clean_str(ont.get("Domain", theme_raw))
        syn_tam = clean_str(ont.get("Synonyms_Tamil", ""))
        syn_eng = clean_str(ont.get("Synonyms_English", ""))

        category_display = THEME_MAPPINGS.get(theme_raw, f"{theme_raw} ({cat_raw})")

        # Determine difficulty based on index / relations
        if cid % 3 == 0:
            diff = "Advanced"
            depth = 3
        elif cid % 2 == 0:
            diff = "Intermediate"
            depth = 2
        else:
            diff = "Beginner"
            depth = 1

        # Check if we have an existing mixed query in Query_Mapping
        matched_qm = None
        key_eng = eng_label.lower()
        key_tam = tam_label.lower()
        if key_eng in qm_by_concept:
            matched_qm = qm_by_concept[key_eng][0]
        elif key_tam in qm_by_concept:
            matched_qm = qm_by_concept[key_tam][0]

        # Template assignment
        tmpl_idx = cid % len(QUESTION_TEMPLATES)
        qtype, eng_tmpl, tam_tmpl = QUESTION_TEMPLATES[tmpl_idx]

        tamil_theme_map = {
            "Grammar": "எழுத்து/சொல் இலக்கண",
            "Porul": "பொருளிலக்கண",
            "Akam": "அகத்திணை",
            "Puram": "புறத்திணை",
            "Culture": "பண்பாட்டு",
            "Language": "மொழி",
            "Meta": "மெய்யியல்",
            "Commentary": "உரை",
            "Literature": "இலக்கிய",
        }
        tamil_theme_val = tamil_theme_map.get(theme_raw, "இலக்கிய")

        if matched_qm and clean_str(matched_qm.get("Example User Query")):
            raw_q = clean_str(matched_qm["Example User Query"])
            # Ensure it includes Tamil label if not already present
            if tam_label not in raw_q:
                raw_q = f"{raw_q} ({tam_label})"
            main_query = raw_q
            tam_query = tam_tmpl.format(
                tamil=tam_label,
                english=eng_label,
                theme=theme_raw,
                tamil_theme=tamil_theme_val,
                category=cat_raw,
                parent=parent,
                tamil_parent=parent,
                relation=rel,
            )
        else:
            main_query = eng_tmpl.format(
                tamil=tam_label,
                english=eng_label,
                theme=theme_raw,
                tamil_theme=tamil_theme_val,
                category=cat_raw,
                parent=parent,
                tamil_parent=parent,
                relation=rel,
            )
            tam_query = tam_tmpl.format(
                tamil=tam_label,
                english=eng_label,
                theme=theme_raw,
                tamil_theme=tamil_theme_val,
                category=cat_raw,
                parent=parent,
                tamil_parent=parent,
                relation=rel,
            )

        # Build clean title
        title = f"{eng_label} ({tam_label})"

        # Canonical formula
        canonical = f"Tolkāppiyam → {theme_raw} → {eng_label} ({tam_label}) → {rel}"

        # Thinai classification
        thinai_val = "Grammar"
        if "kurinji" in eng_label.lower() or "குறிஞ்சி" in tam_label:
            thinai_val = "Kuṟiñci (குறிஞ்சி)"
        elif "mullai" in eng_label.lower() or "முல்லை" in tam_label:
            thinai_val = "Mullai (முல்லை)"
        elif "marutham" in eng_label.lower() or "marutam" in eng_label.lower() or "மருதம்" in tam_label:
            thinai_val = "Marutam (மருதம்)"
        elif "neithal" in eng_label.lower() or "neytal" in eng_label.lower() or "நெய்தல்" in tam_label:
            thinai_val = "Neytal (நெய்தல்)"
        elif "palai" in eng_label.lower() or "பாலை" in tam_label:
            thinai_val = "Pālai (பாலை)"
        elif theme_raw == "Akam":
            thinai_val = "Akattiṇai (அகம்)"
        elif theme_raw == "Puram":
            thinai_val = "Puṟattiṇai (புறம்)"
        elif theme_raw == "Grammar":
            thinai_val = "Ilakkaṇam (இலக்கணம்)"
        else:
            thinai_val = f"{theme_raw} ({cat_raw})"

        keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]
        if eng_label not in keywords:
            keywords.append(eng_label)
        if tam_label not in keywords:
            keywords.append(tam_label)

        record = {
            "id": f"Q-{cid:04d}",
            "index": cid,
            "title": title,
            "query": main_query,
            "tamilQuery": tam_query,
            "category": category_display,
            "theme": theme_raw,
            "thinai": thinai_val,
            "tamilConcept": tam_label,
            "englishConcept": eng_label,
            "synonymsTamil": syn_tam,
            "synonymsEnglish": syn_eng,
            "relation": rel,
            "parentConcept": parent,
            "childConcepts": child,
            "queryType": qtype,
            "difficulty": diff,
            "depth": depth,
            "searchMode": "hybrid",
            "description": desc or f"Canonical inquiry grounding {tam_label} in Tolkāppiyam {theme_raw}.",
            "canonicalForm": canonical,
            "domain": domain,
            "keywords": keywords[:8],
        }

        results.append(record)

    # Ensure exactly 1000 items
    assert len(results) == 1000, f"Expected 1000 items, got {len(results)}"

    # Validate that every single query has both Tamil and English
    for i, r in enumerate(results):
        q = r["query"]
        assert TAMIL_REGEX.search(q), f"Query at index {i} does not contain Tamil characters: {q}"
        assert any(c.isascii() and c.isalpha() for c in q), f"Query at index {i} does not contain English characters: {q}"

    print(f"Validation passed: 1000/1000 queries have mixed Tamil and English!")

    # Write files
    for path in [
        SRC_DATA_DIR / "canonical_1000_queries.json",
        PUBLIC_DATA_DIR / "canonical_1000_queries.json",
        BACKEND_DATA_DIR / "canonical_1000_queries.json",
    ]:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"Saved: {path} ({path.stat().st_size:,} bytes)")

    print("Generation completed successfully!")


if __name__ == "__main__":
    run()
