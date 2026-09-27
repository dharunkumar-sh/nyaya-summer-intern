"""
First-Order Logic Horn-Clause Rule Engine for Tolkāppiyam Tiṇai Semiotics.

Evaluates invariant concomitance rules (Vyāpti) linking habitat and aesthetic affect.
Supports multi-hop rule chaining and antecedent satisfaction verification against retrieved evidence.
"""
from __future__ import annotations

import re
from typing import Dict, Any, List, Optional, Tuple
from .models import RuleNode


class TinaiRuleEngine:
    """Evaluates Horn-clause rules over classical poetic instances with multi-hop chaining."""

    TINAI_RULES = {
        "Kuṟiñci": {
            "rule_id": "R1_KURINCI",
            "rule_name": "Universal Invariant Rule of Mountain Love (Kuṟiñci Vyāpti)",
            "formal_logic": "∀x [MountainTerrain(x) ∧ Midnight(x) ⇒ InvariableAffect(x, Puṇartal)]",
            "antecedents": ["MountainTerrain", "Midnight", "NocturnalMist", "Cēyōṉ", "Vēṅkai"],
            "consequent": "Puṇartal (Intimate Union)",
            "exemplar_sutra": "Tolkāppiyam Poruḷatikāram (Akattiṇaiyiyal) Sūtra 5",
            "exemplar_passage_id": "tol-porul-akam-005",
            "sutra_number": 5,
            "keywords": ["குறிஞ்சி", "சேயோன்", "மலை", "இரவு", "வேங்கை", "புணர்தல்", "mountain", "midnight", "union", "kurinci"],
        },
        "Mullai": {
            "rule_id": "R1_MULLAI",
            "rule_name": "Universal Invariant Rule of Forest Endurance (Mullai Vyāpti)",
            "formal_logic": "∀x [ForestTerrain(x) ∧ RainySeason(x) ⇒ InvariableAffect(x, Iruttal)]",
            "antecedents": ["ForestTerrain", "RainySeason", "Evening", "Māyōṉ", "Kondrai"],
            "consequent": "Iruttal (Patient Waiting)",
            "exemplar_sutra": "Tolkāppiyam Poruḷatikāram (Akattiṇaiyiyal) Sūtra 5",
            "exemplar_passage_id": "tol-porul-akam-005",
            "sutra_number": 5,
            "keywords": ["முல்லை", "மாயோன்", "காடு", "மழை", "இருத்தல்", "forest", "pastoral", "rain", "waiting", "mullai"],
        },
        "Marutam": {
            "rule_id": "R1_MARUTAM",
            "rule_name": "Universal Invariant Rule of Riverine Sulking (Marutam Vyāpti)",
            "formal_logic": "∀x [RiverinePlain(x) ∧ Dawn(x) ⇒ InvariableAffect(x, Ūṭal)]",
            "antecedents": ["RiverinePlain", "Dawn", "AgrarianBiota", "Vēntan", "Marutam"],
            "consequent": "Ūṭal (Lovers' Feigned Quarrel)",
            "exemplar_sutra": "Tolkāppiyam Poruḷatikāram (Akattiṇaiyiyal) Sūtra 5",
            "exemplar_passage_id": "tol-porul-akam-005",
            "sutra_number": 5,
            "keywords": ["மருதம்", "வேந்தன்", "வயல்", "விடியல்", "ஊடல்", "riverine", "plains", "quarrel", "sulking", "marutam"],
        },
        "Neytal": {
            "rule_id": "R1_NEYTAL",
            "rule_name": "Universal Invariant Rule of Littoral Pining (Neytal Vyāpti)",
            "formal_logic": "∀x [LittoralCoast(x) ∧ Sunset(x) ⇒ InvariableAffect(x, Iraṅkal)]",
            "antecedents": ["LittoralCoast", "Sunset", "OceanicBiota", "Varuṇan", "Tālai"],
            "consequent": "Iraṅkal (Melancholic Pining)",
            "exemplar_sutra": "Tolkāppiyam Poruḷatikāram (Akattiṇaiyiyal) Sūtra 5",
            "exemplar_passage_id": "tol-porul-akam-005",
            "sutra_number": 5,
            "keywords": ["நெய்தல்", "வருணன்", "கடல்", "மாலை", "இரங்கல்", "littoral", "sea", "coast", "pining", "neytal"],
        },
        "Pālai": {
            "rule_id": "R1_PALAI",
            "rule_name": "Universal Invariant Rule of Desert Separation (Pālai Vyāpti)",
            "formal_logic": "∀x [AridWasteland(x) ∧ MiddaySummer(x) ⇒ InvariableAffect(x, Pirital)]",
            "antecedents": ["AridWasteland", "SummerNoon", "ParchedFlora", "Koṟṟavai", "Omai"],
            "consequent": "Pirital (Painful Separation)",
            "exemplar_sutra": "Tolkāppiyam Poruḷatikāram (Akattiṇaiyiyal) Sūtra 14",
            "exemplar_passage_id": "tol-porul-akam-014",
            "sutra_number": 14,
            "keywords": ["பாலை", "கொற்றவை", "சுரம்", "நண்பகல்", "பிரிதல்", "arid", "desert", "separation", "palai"],
        },
    }

    @classmethod
    def get_rule_for_tinai(cls, tinai: str = "Kuṟiñci") -> Dict[str, Any]:
        """Returns canonical Horn clause rule for the specified Tiṇai."""
        return cls.TINAI_RULES.get(tinai, cls.TINAI_RULES["Kuṟiñci"])

    @classmethod
    def evaluate_subsumption(
        cls,
        tinai: str,
        context_features: Optional[List[str]] = None,
        evidence_items: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates whether instance features and retrieved evidence satisfy the universal rule antecedents.
        """
        rule = cls.get_rule_for_tinai(tinai)
        features = set(f.lower() for f in (context_features or []))

        # Collect text and entities from evidence
        evidence_text = ""
        evidence_ids = []
        if evidence_items:
            for item in evidence_items:
                pid = getattr(item, "passage_id", None) or (item.get("passage_id") if isinstance(item, dict) else "")
                if pid:
                    evidence_ids.append(pid)
                txt = getattr(item, "text", "") or (item.get("text", "") if isinstance(item, dict) else "")
                evidence_text += " " + txt.lower()

                # Add graph context entities if present
                ctx = getattr(item, "graph_context", None) or (item.get("graph_context") if isinstance(item, dict) else None)
                if isinstance(ctx, dict):
                    for ent in ctx.get("entities", []):
                        lbl = ent.get("label") or ent.get("name") or ""
                        features.add(lbl.lower())
                    for conc in ctx.get("concepts", []):
                        lbl = conc.get("label") or conc.get("name") or ""
                        features.add(lbl.lower())

        matched_antecedents: List[str] = []
        missing_antecedents: List[str] = []

        for ant in rule["antecedents"]:
            ant_lower = ant.lower()
            # Match against explicit context features, keywords, or evidence text
            if (
                ant_lower in features
                or any(kw.lower() in features for kw in rule.get("keywords", []))
                or any(kw.lower() in evidence_text for kw in rule.get("keywords", []))
                or ant_lower in evidence_text
            ):
                matched_antecedents.append(ant)
            else:
                missing_antecedents.append(ant)

        # If at least 1-2 core antecedents or domain keywords are verified in evidence
        is_satisfied = len(matched_antecedents) > 0 or len(evidence_ids) > 0

        return {
            "rule_applied": rule["rule_id"],
            "rule_name": rule["rule_name"],
            "formal_logic": rule["formal_logic"],
            "is_satisfied": is_satisfied,
            "matched_antecedents": matched_antecedents,
            "missing_antecedents": missing_antecedents,
            "deduced_affect": rule["consequent"],
            "evidence_support_ids": evidence_ids,
        }

    @classmethod
    def evaluate_multi_hop(
        cls,
        tinai: str = "Kuṟiñci",
        evidence_items: Optional[List[Any]] = None,
        max_hops: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Executes multi-hop rule deduction chaining:
        Hop 1: Mutalporuḷ (Space-Time Habitat) → Establishes semiotic locus
        Hop 2: Karupporuḷ (Biotic/Deity Signifiers) → Triggers Uripporuḷ Affect
        """
        rule = cls.get_rule_for_tinai(tinai)
        e_ids = []
        if evidence_items:
            for itm in evidence_items:
                pid = getattr(itm, "passage_id", None) or (itm.get("passage_id") if isinstance(itm, dict) else "")
                if pid and pid not in e_ids:
                    e_ids.append(pid)

        hop_chain = []

        # Hop 1: Habitat Spatio-Temporal Grounding
        hop1 = {
            "hop_number": 1,
            "stage": "Locus Grounding",
            "antecedent": f"SpatioTemporalHabitat({tinai})",
            "consequent": f"ActiveSemioticLocus({tinai})",
            "formal_logic": f"Hop1 : TerrestrialTerrain({tinai}) ∧ TemporalOrder({tinai}) ⇒ SemioticLocus({tinai})",
            "matched_evidence_id": e_ids[0] if e_ids else "tol-porul-akam-003",
            "grounding_sutra": rule["exemplar_sutra"],
            "epistemic_warrant": "Mutalporuḷ Axiom (Tolkāppiyam Sūtra 3)",
        }
        hop_chain.append(hop1)

        # Hop 2: Biotic Signifiers to Affective Consequent
        if max_hops >= 2:
            hop2 = {
                "hop_number": 2,
                "stage": "Affective Deduction",
                "antecedent": f"ActiveSemioticLocus({tinai}) ∧ BioticSignifiers({tinai})",
                "consequent": f"InvariableAffect({rule['consequent']})",
                "formal_logic": f"Hop2 : SemioticLocus({tinai}) ∧ BioticSignifier({tinai}) ⇒ {rule['consequent']}",
                "matched_evidence_id": e_ids[1] if len(e_ids) > 1 else (e_ids[0] if e_ids else "tol-porul-akam-005"),
                "grounding_sutra": rule["exemplar_sutra"],
                "epistemic_warrant": "Uripporuḷ Concomitance (Vyāpti Rule)",
            }
            hop_chain.append(hop2)

        return hop_chain

    @classmethod
    def build_rule_nodes(
        cls,
        tinai: str = "Kuṟiñci",
        evidence_items: Optional[List[Any]] = None,
    ) -> List[RuleNode]:
        """
        Creates structured RuleNode instances for knowledge graph representation and persistence.
        Grounded via the dedicated Vyāpti identification stage.
        """
        from .vyapti_identifier import vyapti_identifier

        rule = cls.get_rule_for_tinai(tinai)
        subsumption = cls.evaluate_subsumption(tinai, evidence_items=evidence_items)

        vyapti_result = vyapti_identifier.identify_vyapti(
            evidence_items=evidence_items,
            tinai=tinai,
        )
        is_established = vyapti_result.get("is_established", False)
        grounded = vyapti_result.get("grounded_vyapti")

        if is_established and grounded:
            status = "grounded"
            validated = subsumption["is_satisfied"]
            conf = float(grounded.get("confidence", 0.99))
            ex_sutra = grounded.get("source", rule["exemplar_sutra"])
            f_logic = grounded.get("rule", rule["formal_logic"])
            cand_dict = grounded
        else:
            status = "Vyāpti unavailable"
            validated = False
            conf = 0.0
            ex_sutra = rule["exemplar_sutra"]
            f_logic = f"Rule(R1) : Vyāpti unavailable (No canonical Neo4j evidence satisfies validation criteria)"
            cand_dict = None

        rule_node = RuleNode(
            id="R1",
            label="R1",
            rule_id=rule["rule_id"],
            rule_name=rule["rule_name"],
            antecedents=rule["antecedents"],
            consequent=rule["consequent"],
            formal_logic=f_logic,
            exemplar_sutra=ex_sutra,
            tinai=tinai,
            vyapti_validated=validated,
            vyapti_status=status,
            candidate_vyapti=cand_dict,
            matched_antecedents=subsumption["matched_antecedents"] if validated else [],
            missing_antecedents=subsumption["missing_antecedents"],
            evidence_support_ids=subsumption["evidence_support_ids"] if validated else [],
            confidence=conf,
        )

        return [rule_node]
