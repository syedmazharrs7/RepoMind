from enum import Enum


class GraphEdgeKind(str, Enum):
    """Enum representing relationship types between symbols in the graph."""
    OWNS = "OWNS"
    # Reserved future edge kinds
    CALLS = "CALLS"
    IMPORTS = "IMPORTS"
    REFERENCES = "REFERENCES"
    INHERITS = "INHERITS"
    IMPLEMENTS = "IMPLEMENTS"
    USES = "USES"
