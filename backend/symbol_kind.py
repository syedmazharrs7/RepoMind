from enum import Enum


class SymbolKind(str, Enum):
    """Enum representing types of code symbols extracted from source files."""
    MODULE = "MODULE"
    CLASS = "CLASS"
    FUNCTION = "FUNCTION"
    METHOD = "METHOD"
    CONSTRUCTOR = "CONSTRUCTOR"
    VARIABLE = "VARIABLE"
    CONSTANT = "CONSTANT"
    IMPORT = "IMPORT"
    PARAMETER = "PARAMETER"
    DECORATOR = "DECORATOR"
    PROPERTY = "PROPERTY"
    UNKNOWN = "UNKNOWN"
