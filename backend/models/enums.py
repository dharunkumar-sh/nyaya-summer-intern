"""
Domain Enums for Classical Tamil Literature and Corpus.
"""
from enum import Enum


class AtikaramType(str, Enum):
    """The three canonical books (atikārams) of the Tolkāppiyam."""
    ELUTTU = "eluttu"
    COL = "col"
    PORUL = "porul"

    @property
    def display_name(self) -> str:
        names = {
            "eluttu": "Eḻuttatikāram (எழுத்ததிகாரம்)",
            "col": "Collatikāram (சொல்லதிகாரம்)",
            "porul": "Poruḷatikāram (பொருளதிகாரம்)",
        }
        return names.get(self.value, self.value)


class TinaiType(str, Enum):
    """The five interior landscapes (Aintinai) and generalized poetics."""
    KURINJI = "Kuriñci"
    MULLAI = "Mullai"
    MARUTHAM = "Marutam"
    NEYTHAL = "Neytal"
    PALAI = "Pālai"
    GENERAL = "General"
    PURAM = "Puram"


class HierarchyLevel(str, Enum):
    """Hierarchical Knowledge Graph and Literature structural levels."""
    L0_CORPUS = "L0_CORPUS"       # Root literature / treatise
    L1_ATIKARAM = "L1_ATIKARAM"   # Major book or canto
    L2_IYAL = "L2_IYAL"           # Chapter or thematic division
    L3_SUTRA = "L3_SUTRA"         # Individual verse, aphorism, or passage
