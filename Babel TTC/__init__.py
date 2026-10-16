"""
Babel V1 — Sistema de armazenamento com endereços hierárquicos.

Implementa H2: endereço curto (hash + localizador) recupera texto via índice.
"""

from .hash_address import compute_hash, compute_address
from .compression import compress, decompress
from .index import BabelIndex
from .package import BabelPackage
from .validator import validate_package
from .storage import LocalDiskStorage

__version__ = "1.0.0"
