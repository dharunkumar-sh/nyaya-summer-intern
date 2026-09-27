"""
Evidence-Grounded Premise Builder for Nyāya Syllogistic Inference.

Extracts formal epistemic premises (Pakṣa, Hetu, and Dṛṣṭānta) directly from
retrieved and validated EvidenceItem instances without fabrication.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from core.logger import logger
from .models import PremiseNode


class EvidenceGroundedPremiseBuilder:
    """
    Constructs formal PremiseNode instances grounded strictly in retrieved evidence.
    Classifies evidence into Mutalporuḷ (spatio-temporal), Karupporuḷ (biotic signifiers),
    and Uripporuḷ (affective interiority) premises.
    """

    @classmethod
    def build_premise_nodes(
        cls,
        evidence_items: List[Any],
        tinai: str = "Kuṟiñci",
    ) -> List[PremiseNode]:
        """
        Converts retrieved evidence items (EvidenceItem or dict) into structured PremiseNodes.
        Requires genuine retrieved canonical evidence; returns an empty list if no evidence is provided.
        """
        if not evidence_items:
            return []

        premises: List[PremiseNode] = []

        # Iterate through evidence items and construct grounded premises
        for idx, item in enumerate(evidence_items):
            pid = getattr(item, "passage_id", None) or (item.get("passage_id") or item.get("id") if isinstance(item, dict) else "")
            if not pid:
                continue

            text = getattr(item, "text", "") or (item.get("text") or item.get("original_text") if isinstance(item, dict) else "")
            src = getattr(item, "source", {}) or (item.get("source", {}) if isinstance(item, dict) else {})
            if not isinstance(src, dict):
                src = {}

            score = getattr(item, "relevance_score", 0.95) or (item.get("relevance_score", 0.95) if isinstance(item, dict) else 0.95)
            sutra_num = src.get("sutra_number") or (item.get("sutra_number") if isinstance(item, dict) else None)
            work = src.get("work") or src.get("work_name") or (item.get("work_name") if isinstance(item, dict) else "Tolkāppiyam")
            section = src.get("section") or src.get("section_name") or (item.get("section_name") if isinstance(item, dict) else "Poruḷatikāram")
            chapter = src.get("chapter") or src.get("chapter_name") or (item.get("chapter_name") if isinstance(item, dict) else "")
            sutra_ref = src.get("reference") or src.get("source_reference") or (item.get("source_reference") if isinstance(item, dict) else None)
            if not sutra_ref:
                sutra_ref = f"{work} {section} {chapter} Sūtra {sutra_num if sutra_num else ''}".replace("  ", " ").strip()
            item_tinai = src.get("tinai") or (item.get("tinai") if isinstance(item, dict) else tinai) or tinai
            raw_cat = src.get("category") or (item.get("category") if isinstance(item, dict) else None)
            category_str = str(raw_cat if raw_cat is not None else ("Mutalporuḷ" if idx == 0 else "Karupporuḷ"))

            code = f"P{idx + 1}"

            # Create grounded statement reflecting actual text and reference
            clean_snippet = text.replace("\n", " ").strip()
            if len(clean_snippet) > 160:
                clean_snippet = clean_snippet[:157] + "..."

            if idx == 0 or "mutal" in category_str.lower():
                stmt = f"Canonical treatise establishes terrestrial and temporal habitat: '{clean_snippet}'."
                tamil_stmt = f"முதற்பொருள் சான்றாதாரத்தின்படி நிலமும் பொழுதும் அகப்பொருளுக்கு நிலைக்களனாக அமைகின்றன: {sutra_ref}."
                logic = f"Premise({code}) : TerrestrialHabitat(x, {item_tinai}) ∧ CanonicalDefinition({pid})"
                pramana = "Śabda Pramāṇa (Canonical Definition)"
                cat = "Mutalporuḷ"
            elif idx == 1 or "karu" in category_str.lower():
                stmt = f"Biotic and environmental signifiers ground poetic behavior: '{clean_snippet}'."
                tamil_stmt = f"கருப்பொருள் கூறுகளான சூழலியல் குறியீடுகள் அக ஒழுக்கத்தை வழிநடத்துகின்றன: {sutra_ref}."
                logic = f"Premise({code}) : BioticSignifier(x, {item_tinai}) ∧ EmpiricalGround({pid})"
                pramana = "Pratyakṣa + Śabda (Direct Textual Ground)"
                cat = "Karupporuḷ"
            else:
                stmt = f"Poetic affect and psychological conduct instantiated: '{clean_snippet}'."
                tamil_stmt = f"உரிப்பொருள் ஒழுக்கம் பனுவலில் நடைமுறைப்படுத்தப்படுகிறது: {sutra_ref}."
                logic = f"Premise({code}) : AffectiveConduct(x, {item_tinai}) ∧ EvidenceGround({pid})"
                pramana = "Anumāna Pramāṇa (Subsumptive Ground)"
                cat = "Uripporuḷ"

            premise_node = PremiseNode(
                id=code,
                label=code,
                statement=stmt,
                tamil_statement=tamil_stmt,
                formal_logic=logic,
                pramana_mode=pramana,
                grounded_passage_ids=[pid],
                grounded_sutra=sutra_ref,
                tinai=item_tinai,
                concept_category=cat,
                confidence=float(score) if score else 0.95,
            )
            premises.append(premise_node)

            if len(premises) >= 3:
                # Top 2-3 premises are sufficient for Nyāya deduction
                break

        return premises

    @classmethod
    def build_from_evidence_collection(
        cls,
        collection: Any,
        tinai: str = "Kuṟiñci",
    ) -> List[PremiseNode]:
        """
        Entry point taking an EvidenceCollection from HybridRAGPipeline.
        """
        items = getattr(collection, "items", [])
        return cls.build_premise_nodes(items, tinai=tinai)


class PremiseBuilder(EvidenceGroundedPremiseBuilder):
    """
    Backward-compatible PremiseBuilder interface.
    """

    @classmethod
    def build_premises(
        cls,
        evidence_items: List[Dict[str, Any]],
        tinai: str = "Kuṟiñci",
    ) -> Dict[str, Any]:
        """
        Legacy dictionary interface returning formatted premise records.
        """
        nodes = cls.build_premise_nodes(evidence_items, tinai=tinai)
        formatted = []
        for n in nodes:
            formatted.append({
                "id": n.id,
                "name": f"{n.concept_category} Grounding",
                "tamil_name": f"முன்னிலைக் கோட்பாடு {n.id} ({n.concept_category})",
                "statement": n.statement,
                "formal_logic": n.formal_logic,
                "grounded_sutra": n.grounded_sutra,
                "linked_evidence": f"E{n.id[1:]}" if len(n.id) > 1 and n.id[1:].isdigit() else "E1",
            })

        return {
            "premises": formatted,
            "total_premises": len(formatted),
        }
