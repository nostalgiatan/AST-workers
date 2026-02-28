"""AST Workers - Python CLI for AST-level code operations.

A modular toolkit for manipulating Python code at the AST level.
Uses libcst for preserving formatting and comments.
"""

__version__ = "0.1.0"

from .operations import (
    delete_class,
    delete_function,
    find_symbol,
    insert_class,
    insert_function,
    insert_import,
    list_classes,
    list_functions,
    list_imports,
    rename_symbol,
)
from .utils import format_code, validate_syntax

__all__ = [
    # Operations
    "insert_function",
    "insert_class",
    "insert_import",
    "delete_function",
    "delete_class",
    "list_functions",
    "list_classes",
    "list_imports",
    "find_symbol",
    "rename_symbol",
    # Utils
    "validate_syntax",
    "format_code",
]
