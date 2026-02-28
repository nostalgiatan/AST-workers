"""Rename operations using libcst for AST-level code manipulation."""

from pathlib import Path
from typing import Any

import libcst as cst


class RenameTransformer(cst.CSTTransformer):
    """CST Transformer for renaming symbols."""

    locations: list[dict[str, Any]] = []

    def __init__(
        self,
        old_name: str,
        new_name: str,
        symbol_type: str = "function",
    ):
        self.old_name = old_name
        self.new_name = new_name
        self.symbol_type = symbol_type
        self.renamed_count = 0
        self.locations = []

    def leave_FunctionDef(
        self,
        original_node: cst.FunctionDef,
        updated_node: cst.FunctionDef,
    ) -> cst.FunctionDef:
        """Rename function definition."""
        if self.symbol_type in ("function", "all"):
            if updated_node.name.value == self.old_name:
                self.renamed_count += 1
                self.locations.append({"type": "definition", "line": None})
                return updated_node.with_changes(name=cst.Name(value=self.new_name))
        return updated_node

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        """Rename class definition."""
        if self.symbol_type in ("class", "all"):
            if updated_node.name.value == self.old_name:
                self.renamed_count += 1
                self.locations.append({"type": "definition", "line": None})
                return updated_node.with_changes(name=cst.Name(value=self.new_name))
        return updated_node

    def leave_Name(
        self,
        original_node: cst.Name,
        updated_node: cst.Name,
    ) -> cst.Name:
        """Rename name references."""
        if updated_node.value == self.old_name:
            # Check if this is in a context we should rename
            # (not as an attribute access, etc.)
            self.renamed_count += 1
            self.locations.append({"type": "reference", "line": None})
            return updated_node.with_changes(value=self.new_name)
        return updated_node


def rename_symbol(
    module_path: Path,
    old_name: str,
    new_name: str,
    symbol_type: str = "function",
    rename_references: bool = True,
) -> dict[str, Any]:
    """Rename a symbol in a module.

    Args:
        module_path: Path to the Python module
        old_name: Current name of the symbol
        new_name: New name for the symbol
        symbol_type: Type of symbol ('function', 'class', 'variable', 'all')
        rename_references: Also rename all references to the symbol

    Returns:
        Result dict with operation details
    """
    source = module_path.read_text()

    transformer = RenameTransformer(
        old_name=old_name,
        new_name=new_name,
        symbol_type=symbol_type,
    )

    tree = cst.parse_module(source)
    new_tree = tree.visit(transformer)

    if transformer.renamed_count == 0:
        raise ValueError(f"Symbol '{old_name}' not found")

    # Write back
    new_source = new_tree.code
    module_path.write_text(new_source)

    return {
        "operation": "rename_symbol",
        "target": {
            "module": str(module_path),
            "old_name": old_name,
            "new_name": new_name,
            "type": symbol_type,
        },
        "modified": True,
        "renamed_count": transformer.renamed_count,
    }
