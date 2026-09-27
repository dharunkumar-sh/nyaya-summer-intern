"""
Hierarchical Knowledge Graph Builder for Classical Tamil Literary Knowledge.

Constructs a multi-level structural hierarchy (L0-L5) across five logical layers:
- L0: Literature (Source Layer)
- L1: Work (Source Layer)
- L2: Section (Source Layer)
- L3: Verse/Passage (Source Layer)
- L4: Concept (Concept Layer)
- L5: Entity/Event (Entity Layer / Event Layer)
plus the Reasoning Layer (Nyāya syllogistic members and epistemological axioms).

Built on top of GraphStore abstraction (NetworkXGraphStore), ready for Neo4j.
"""
from __future__ import annotations

import networkx as nx
from typing import Dict, Any, List, Optional
from ingestion.corpus_loader import corpus_loader
from core.logger import logger
from .ontology import TolkappiyamOntology
from .store import (
    GraphStore,
    NetworkXGraphStore,
    HierarchyLevel,
    LogicalLayer,
    KGNode,
    KGEdge,
)


class KnowledgeGraphBuilder:
    """
    Builds and manages the hierarchical, multi-layered knowledge graph.
    Delegates to GraphStore for storage and query abstraction.
    """

    def __init__(self, store: Optional[GraphStore] = None):
        self.store: GraphStore = store or NetworkXGraphStore()
        self.build_graph()

    @property
    def graph(self) -> nx.MultiDiGraph:
        """Exposes underlying NetworkX graph for backward compatibility."""
        if hasattr(self.store, "graph"):
            return self.store.graph
        return nx.MultiDiGraph()

    def build_graph(self) -> None:
        """Populates hierarchical nodes and edges from corpus, semiotics, and ontology."""
        self.store.clear()

        # -------------------------------------------------------------------
        # 1. L0 – Literature Layer (Source Layer)
        # -------------------------------------------------------------------
        self.store.add_node(
            KGNode(
                id="lit-sangam",
                label="Classical Tamil Sangam Literature",
                type="Literature",
                hierarchy_level="L0",
                source="Tamil Sangam Corpus",
                confidence=1.0,
                metadata={
                    "layer": LogicalLayer.SOURCE.value,
                    "category": "Literature",
                    "transliteration": "Caṅka Ilakkiyam",
                    "description": "Ancient Classical Tamil literary corpus spanning poetics, grammar, and ethics.",
                    "x": 360,
                    "y": 20,
                    "radius": 40,
                },
            )
        )

        # -------------------------------------------------------------------
        # 2. L1 – Work Layer (Source Layer)
        # -------------------------------------------------------------------
        self.store.add_node(
            KGNode(
                id="work-tolkappiyam",
                label="தொல்காப்பியம்",
                type="Work",
                hierarchy_level="L1",
                source="lit-sangam",
                confidence=1.0,
                metadata={
                    "layer": LogicalLayer.SOURCE.value,
                    "category": "Work",
                    "transliteration": "Tolkāppiyam",
                    "author": "Tolkāppiyar",
                    "period": "Classical Sangam / Pre-Sangam",
                    "description": "The foundational Tamil grammar and poetics treatise comprising 1,610 sūtras in three books.",
                    "x": 360,
                    "y": 50,
                    "radius": 36,
                },
            )
        )
        self.store.add_edge(
            KGEdge(
                source="lit-sangam",
                relation="contains_work",
                target="work-tolkappiyam",
                source_id="corpus_metadata",
                confidence=1.0,
                validation_level="corpus_validated",
                metadata={"label": "நூல் (Contains Work)"},
            )
        )

        # -------------------------------------------------------------------
        # 3. L2 – Section Layer (Source Layer)
        # -------------------------------------------------------------------
        sections = [
            {
                "id": "sec-eluttu",
                "label": "எழுத்ததிகாரம்",
                "transliteration": "Eḻuttatikāram",
                "english": "Book of Orthography & Phonology",
                "parent": "work-tolkappiyam",
                "sutra_count": 483,
            },
            {
                "id": "sec-col",
                "label": "சொல்லதிகாரம்",
                "transliteration": "Collatikāram",
                "english": "Book of Morphology & Syntax",
                "parent": "work-tolkappiyam",
                "sutra_count": 463,
            },
            {
                "id": "sec-porul",
                "label": "பொருளதிகாரம்",
                "transliteration": "Poruḷatikāram",
                "english": "Book of Poetics & Epistemology",
                "parent": "work-tolkappiyam",
                "sutra_count": 664,
            },
            {
                "id": "sec-porul-akam",
                "label": "அகத்திணையியல்",
                "transliteration": "Akattiṇaiyiyal",
                "english": "Chapter on Interior Landscape Poetics",
                "parent": "sec-porul",
                "sutra_count": 55,
            },
            {
                "id": "sec-porul-mey",
                "label": "மெய்ப்பாட்டியல்",
                "transliteration": "Meyppāṭṭiyal",
                "english": "Chapter on Aesthetic Emotional Realization",
                "parent": "sec-porul",
                "sutra_count": 27,
            },
        ]

        for sec in sections:
            self.store.add_node(
                KGNode(
                    id=sec["id"],
                    label=sec["label"],
                    type="Section",
                    hierarchy_level="L2",
                    source="work-tolkappiyam",
                    confidence=1.0,
                    metadata={
                        "layer": LogicalLayer.SOURCE.value,
                        "category": "Section",
                        "transliteration": sec["transliteration"],
                        "english": sec["english"],
                        "sutra_count": sec["sutra_count"],
                    },
                )
            )
            self.store.add_edge(
                KGEdge(
                    source=sec["parent"],
                    relation="contains_section",
                    target=sec["id"],
                    source_id="corpus_metadata",
                    confidence=1.0,
                    validation_level="corpus_validated",
                    metadata={"label": "அதிகாரம் / இயல் (Contains Section)"},
                )
            )

        # -------------------------------------------------------------------
        # 4. L3 – Verse / Passage Layer (Source Layer)
        # -------------------------------------------------------------------
        canonical_sutras = corpus_loader.get_all_sutras()
        for sutra in canonical_sutras:
            s_id = sutra.get("id")
            s_num = sutra.get("sutra_number")
            s_iyal = sutra.get("iyal", "Akattiṇaiyiyal")
            parent_sec = "sec-porul-mey" if "Meyppāṭṭiyal" in s_iyal else "sec-porul-akam"

            self.store.add_node(
                KGNode(
                    id=s_id,
                    label=f"Sūtra {s_num}",
                    type="Verse",
                    hierarchy_level="L3",
                    source=f"Tolkāppiyam {s_iyal} {s_num}",
                    confidence=1.0,
                    metadata={
                        "layer": LogicalLayer.SOURCE.value,
                        "category": "Evidence",
                        "sutra_number": s_num,
                        "iyal": s_iyal,
                        "atikaram": sutra.get("atikaram", "Poruḷatikāram"),
                        "tinai": sutra.get("tinai", "General"),
                        "citation": f"Tolkāppiyam {s_iyal} Sūtra {s_num}",
                        "original_text": sutra.get("tamil_text", ""),
                        "translation": sutra.get("english_translation", ""),
                    },
                )
            )
            self.store.add_edge(
                KGEdge(
                    source=parent_sec,
                    relation="contains_passage",
                    target=s_id,
                    source_id="canonical_index",
                    confidence=1.0,
                    validation_level="corpus_validated",
                    metadata={"label": "சூத்திரம் (Contains Sūtra)"},
                )
            )

        # -------------------------------------------------------------------
        # 5. L4 – Concept Layer (Concept Layer)
        # -------------------------------------------------------------------
        canonical_concepts = [
            {
                "id": "mutalporul",
                "label": "முதற்பொருள்",
                "transliteration": "Mutalporuḷ",
                "category": "Concept",
                "x": 360,
                "y": 80,
                "radius": 34,
                "description": "The fundamental spatio-temporal ground of all Akam poetry (Space & Time).",
                "citation": "Tolkāppiyam Akattiṇaiyiyal Sūtra 4",
                "sutra_ref": "tol-porul-akam-004",
            },
            {
                "id": "karupporul",
                "label": "கருப்பொருள்",
                "transliteration": "Karupporuḷ",
                "category": "Concept",
                "x": 360,
                "y": 260,
                "radius": 30,
                "description": "14 ecological and cultural signifiers (Deity, Flora, Fauna, Music).",
                "citation": "Akattiṇaiyiyal Sūtra 18",
                "sutra_ref": "tol-porul-akam-018",
            },
            {
                "id": "uriporul",
                "label": "உரிப்பொருள்",
                "transliteration": "Uripporuḷ",
                "category": "Concept",
                "x": 360,
                "y": 410,
                "radius": 36,
                "description": "Invariable human interior emotional experience (Love, Separation, Pining).",
                "citation": "Akattiṇaiyiyal Sūtra 14",
                "sutra_ref": "tol-porul-akam-014",
            },
            {
                "id": "tinai",
                "label": "திணை",
                "transliteration": "Tiṇai",
                "category": "Concept",
                "x": 120,
                "y": 170,
                "radius": 32,
                "description": "Ecological poetics convention harmonizing landscape, time, and interior mood.",
                "citation": "Akattiṇaiyiyal Sūtra 3",
                "sutra_ref": "tol-porul-akam-003",
            },
            {
                "id": "meyppatu",
                "label": "மெய்ப்பாடு",
                "transliteration": "Meyppāṭu",
                "category": "Concept",
                "x": 600,
                "y": 410,
                "radius": 32,
                "description": "Aesthetic emotional manifestations appearing in poetic discourse.",
                "citation": "Meyppāṭṭiyal Sūtra 1",
                "sutra_ref": "tol-porul-mey-001",
            },
        ]

        for c in canonical_concepts:
            self.store.add_node(
                KGNode(
                    id=c["id"],
                    label=c["label"],
                    type="Concept",
                    hierarchy_level="L4",
                    source=c["citation"],
                    confidence=1.0,
                    metadata={
                        "layer": LogicalLayer.CONCEPT.value,
                        "category": "Concept",
                        "transliteration": c["transliteration"],
                        "description": c["description"],
                        "citation": c["citation"],
                        "x": c["x"],
                        "y": c["y"],
                        "radius": c["radius"],
                    },
                )
            )
            # Link from sūtra to concept
            if self.store.has_node(c["sutra_ref"]):
                self.store.add_edge(
                    KGEdge(
                        source=c["sutra_ref"],
                        relation="exposes_concept",
                        target=c["id"],
                        source_id=c["sutra_ref"],
                        confidence=1.0,
                        validation_level="corpus_validated",
                        metadata={"label": "கோட்பாடு (Exposes Concept)"},
                    )
                )

        # -------------------------------------------------------------------
        # 6. L5 – Entity & Event Layer (Entity Layer / Event Layer)
        # -------------------------------------------------------------------
        canonical_entities_events = [
            {
                "id": "nilam",
                "label": "நிலம்",
                "transliteration": "Nilam",
                "category": "Object",
                "layer": LogicalLayer.ENTITY.value,
                "x": 220,
                "y": 170,
                "radius": 28,
                "description": "Terrestrial landscape (Mountains, Forests, Plains, Littoral, Wasteland).",
                "citation": "Akattiṇaiyiyal Sūtra 4",
                "sutra_ref": "tol-porul-akam-004",
            },
            {
                "id": "polutu",
                "label": "பொழுது",
                "transliteration": "Poḻutu",
                "category": "Object",
                "layer": LogicalLayer.ENTITY.value,
                "x": 500,
                "y": 170,
                "radius": 28,
                "description": "Temporal dimensions: Six seasonal spans and six day-night hours.",
                "citation": "Akattiṇaiyiyal Sūtra 4",
                "sutra_ref": "tol-porul-akam-004",
            },
            {
                "id": "ceyon",
                "label": "சேயோன்",
                "transliteration": "Cēyōṉ",
                "category": "Person",
                "layer": LogicalLayer.ENTITY.value,
                "x": 100,
                "y": 280,
                "radius": 30,
                "description": "Presiding Mountain Deity of Kuṟiñci tract (Red Murukan archetype).",
                "citation": "Akattiṇaiyiyal Sūtra 5",
                "sutra_ref": "tol-porul-akam-005",
            },
            {
                "id": "kurinci",
                "label": "குறிஞ்சி",
                "transliteration": "Kuṟiñci",
                "category": "Object",
                "layer": LogicalLayer.ENTITY.value,
                "x": 250,
                "y": 280,
                "radius": 32,
                "description": "Misty montane ecological tract of clandestine nocturnal love.",
                "citation": "Akattiṇaiyiyal Sūtra 5",
                "sutra_ref": "tol-porul-akam-005",
            },
            {
                "id": "venkai",
                "label": "வேங்கை",
                "transliteration": "Vēṅkai",
                "category": "Object",
                "layer": LogicalLayer.ENTITY.value,
                "x": 480,
                "y": 280,
                "radius": 26,
                "description": "Golden kino tree flowering as biotic signifier of lovers' maturity.",
                "citation": "Akattiṇaiyiyal Sūtra 18",
                "sutra_ref": "tol-porul-akam-018",
            },
            {
                "id": "punartal",
                "label": "புணர்தல்",
                "transliteration": "Puṇartal",
                "category": "Event",
                "layer": LogicalLayer.EVENT.value,
                "x": 220,
                "y": 410,
                "radius": 30,
                "description": "Passionate clandestine union of lovers in montane nocturnal landscape.",
                "citation": "Akattiṇaiyiyal Sūtra 14",
                "sutra_ref": "tol-porul-akam-014",
            },
            {
                "id": "mayon",
                "label": "மாயோன்",
                "transliteration": "Māyōṉ",
                "category": "Person",
                "layer": LogicalLayer.ENTITY.value,
                "x": 80,
                "y": 380,
                "radius": 28,
                "description": "Presiding deity of the Mullai pastoral tract (Viṣṇu archetype).",
                "citation": "Akattiṇaiyiyal Sūtra 5",
                "sutra_ref": "tol-porul-akam-005",
            },
            {
                "id": "mullai",
                "label": "முல்லை",
                "transliteration": "Mullai",
                "category": "Object",
                "layer": LogicalLayer.ENTITY.value,
                "x": 160,
                "y": 350,
                "radius": 28,
                "description": "Pastoral deciduous forest realm of patient endurance.",
                "citation": "Akattiṇaiyiyal Sūtra 5",
                "sutra_ref": "tol-porul-akam-005",
            },
            {
                "id": "pirital",
                "label": "பிரிதல்",
                "transliteration": "Pirital",
                "category": "Event",
                "layer": LogicalLayer.EVENT.value,
                "x": 300,
                "y": 470,
                "radius": 28,
                "description": "Lovers' painful separation across arid wasteland (Pālai).",
                "citation": "Akattiṇaiyiyal Sūtra 14",
                "sutra_ref": "tol-porul-akam-014",
            },
        ]

        for item in canonical_entities_events:
            self.store.add_node(
                KGNode(
                    id=item["id"],
                    label=item["label"],
                    type="Event" if item["category"] == "Event" else "Entity",
                    hierarchy_level="L5",
                    source=item["citation"],
                    confidence=1.0,
                    metadata={
                        "layer": item["layer"],
                        "category": item["category"],
                        "transliteration": item["transliteration"],
                        "description": item["description"],
                        "citation": item["citation"],
                        "x": item["x"],
                        "y": item["y"],
                        "radius": item["radius"],
                    },
                )
            )
            # Link from sūtra to entity/event
            if self.store.has_node(item["sutra_ref"]):
                self.store.add_edge(
                    KGEdge(
                        source=item["sutra_ref"],
                        relation="instantiates_entity",
                        target=item["id"],
                        source_id=item["sutra_ref"],
                        confidence=1.0,
                        validation_level="corpus_validated",
                        metadata={"label": "உறுப்பு (Instantiates Entity)"},
                    )
                )

        # -------------------------------------------------------------------
        # 7. Reasoning Layer Nodes (Reasoning Layer)
        # -------------------------------------------------------------------
        for sutra in canonical_sutras:
            nyaya = sutra.get("nyaya_mapping", {})
            if nyaya:
                rsn_id = f"rsn-{sutra['id']}"
                member = nyaya.get("member", "Hetu")
                pramana = nyaya.get("pramana", "Śabda Pramāṇa")
                axiom = nyaya.get("axiom", "")

                self.store.add_node(
                    KGNode(
                        id=rsn_id,
                        label=f"{member} ({pramana})",
                        type="Reasoning",
                        hierarchy_level="L4",
                        source=sutra["id"],
                        confidence=0.98,
                        metadata={
                            "layer": LogicalLayer.REASONING.value,
                            "category": "Reasoning",
                            "member": member,
                            "pramana": pramana,
                            "axiom": axiom,
                            "description": f"Nyāya epistemic grounding for {sutra['id']}",
                        },
                    )
                )
                self.store.add_edge(
                    KGEdge(
                        source=sutra["id"],
                        relation="grounds_deduction",
                        target=rsn_id,
                        source_id=sutra["id"],
                        confidence=0.98,
                        validation_level="corpus_validated",
                        metadata={"label": "அளவை ஆதாரம் (Grounds Deduction)"},
                    )
                )

        # -------------------------------------------------------------------
        # 8. Canonical Semiotic Cross-Edges
        # -------------------------------------------------------------------
        canonical_edges = [
            {"id": "e1", "source": "mutalporul", "target": "nilam", "label": "அடக்கியது (Contains)", "predicate": "consistsOf", "conf": 0.95},
            {"id": "e2", "source": "mutalporul", "target": "polutu", "label": "அடக்கியது (Contains)", "predicate": "consistsOf", "conf": 0.95},
            {"id": "e3", "source": "nilam", "target": "kurinci", "label": "உட்கூறு (Grounds)", "predicate": "hasHabitat", "conf": 0.95},
            {"id": "e4", "source": "ceyon", "target": "kurinci", "label": "தெய்வம் (Presides)", "predicate": "presidesOver", "conf": 0.95},
            {"id": "e5", "source": "kurinci", "target": "karupporul", "label": "கருத்தொடர்பு (Signifies)", "predicate": "manifestsSignifierFor", "conf": 0.90},
            {"id": "e6", "source": "karupporul", "target": "venkai", "label": "மலர் (Flora)", "predicate": "includesComponent", "conf": 0.95},
            {"id": "e7", "source": "mutalporul", "target": "uriporul", "label": "நிலைக்களம் (Aesthetic Base)", "predicate": "groundsIn", "conf": 0.98},
            {"id": "e8", "source": "kurinci", "target": "punartal", "label": "உரிப்பொருள் (Invariable Affect)", "predicate": "hasUripporuḷ", "conf": 0.98},
            {"id": "e9", "source": "venkai", "target": "punartal", "label": "புணர்தல் அடையாளம் (Signifier)", "predicate": "evokesAffect", "conf": 0.85},
            {"id": "e10", "source": "punartal", "target": "uriporul", "label": "மெய்ப்பாட்டு நெறி (Realization)", "predicate": "manifestsAs", "conf": 0.95},
            {"id": "e11", "source": "mayon", "target": "mullai", "label": "தெய்வம் (Presides)", "predicate": "presidesOver", "conf": 0.95},
            {"id": "e12", "source": "tinai", "target": "mutalporul", "label": "மூலாதாரம் (Grounds)", "predicate": "groundsIn", "conf": 0.95},
            {"id": "e13", "source": "uriporul", "target": "meyppatu", "label": "வெளிப்பாடு (Manifests)", "predicate": "manifestsAs", "conf": 0.92},
            {"id": "e14", "source": "mullai", "target": "pirital", "label": "தொடர்பு (Pertains)", "predicate": "hasUripporuḷ", "conf": 0.90},
        ]

        for edge in canonical_edges:
            self.store.add_edge(
                KGEdge(
                    id=edge["id"],
                    source=edge["source"],
                    relation=edge["predicate"],
                    target=edge["target"],
                    source_id="canonical_axiom",
                    confidence=edge.get("conf", 0.95),
                    validation_level="corpus_validated",
                    metadata={
                        "label": edge["label"],
                        "predicate": edge["predicate"],
                    },
                )
            )

        logger.info(
            f"Constructed Hierarchical Knowledge Graph: {self.store.node_count()} nodes, {self.store.edge_count()} edges"
        )

    def merge_duplicate_entities(self, canonical_id: str, alias_ids: List[str]) -> KGNode:
        """Merges duplicate or alias entities into a single canonical node."""
        return self.store.merge_nodes(canonical_id, alias_ids)

    def get_full_graph_data(self) -> Dict[str, Any]:
        """Exports graph in pure JSON format formatted for Cytoscape and SVG rendering."""
        nodes = [n.to_dict() for n in self.store.get_all_nodes()]
        node_ids = {str(n["id"]) for n in nodes}

        raw_edges = self.store.get_all_edges()
        edges = []
        seen_edge_ids = set()
        pair_counts = {}
        for e in raw_edges:
            ed = e.to_dict()
            if "type" not in ed:
                ed["type"] = ed.get("relation", "RELATED_TO")

            src = str(ed.get("source") or "")
            tgt = str(ed.get("target") or "")
            if not src or not tgt:
                continue

            # Alias uripporul <-> uriporul
            if src == "uripporul" and "uriporul" in node_ids:
                src = "uriporul"
                ed["source"] = src
            if tgt == "uripporul" and "uriporul" in node_ids:
                tgt = "uriporul"
                ed["target"] = tgt

            # Validate endpoints exist (supports self-referential edges where src == tgt)
            if src not in node_ids or tgt not in node_ids:
                continue

            pair_key = (src, ed.get("type"), tgt)
            pair_counts[pair_key] = pair_counts.get(pair_key, 0) + 1

            edge_id = str(ed.get("id") or "")
            if not edge_id or edge_id in seen_edge_ids:
                # Deterministic stable ID without array index
                edge_id = f"e_{src}_{ed.get('type')}_{tgt}_{pair_counts[pair_key]}"
                ed["id"] = edge_id
            seen_edge_ids.add(edge_id)
            edges.append(ed)

        return {
            "nodes": nodes,
            "edges": edges,
            "relationships": edges,
            "categories": TolkappiyamOntology.get_category_config(),
            "hierarchy_levels": TolkappiyamOntology.get_hierarchy_config(),
            "logical_layers": TolkappiyamOntology.get_layer_config(),
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "backend_node_count": len(nodes),
            "backend_edge_count": len(raw_edges),
        }


# Singleton KG instance
kg_instance = KnowledgeGraphBuilder()
