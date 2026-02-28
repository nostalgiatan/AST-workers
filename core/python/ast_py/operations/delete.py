"""Delete operations using libcst for AST-level code manipulation."""

from pathlib import Path
from typing import Any, Optional

import libcst as cst


class DeleteTransformer(cst.CSTTransformer):
    """CST Transformer for deleting nodes."""

    def __init__(
        self,
        delete_type: str,
        target_name: str,
        target_class: Optional[str] = None,
    ):
        self.delete_type = delete_type
        self.target_name = target_name
        self.target_class = target_class
        self.deleted = False
        self.deleted_position = None

    def leave_FunctionDef(
        self,
        original_node: cst.FunctionDef,
        updated_node: cst.FunctionDef,
    ) -> cst.FunctionDef | cst.RemovalSentinel:
        """Handle function deletion."""
        if self.delete_type == "function":
            if not self.target_class:  # Module-level function
                if updated_node.name.value == self.target_name:
                    self.deleted = True
                    return cst.RemoveFromParent()
        return updated_node

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        """Handle class deletion and method deletion within classes."""
        if self.delete_type == "class":
            if updated_node.name.value == self.target_name:
                self.deleted = True
                # Return empty class (can't remove directly from parent)
                return updated_node.with_changes(body=cst.IndentedBlock(body=[]))
        elif self.delete_type == "function" and self.target_class:
            # Delete method from class
            if updated_node.name.value == self.target_class:
                new_body = [
                    node
                    for node in updated_node.body.body
                    if not (isinstance(node, cst.FunctionDef) and node.name.value == self.target_name)
                ]
                if len(new_body) != len(updated_node.body.body):
                    self.deleted = True
                return updated_node.with_changes(body=updated_node.body.with_changes(body=new_body))
        return updated_node


class ClassMethodDeleter(cst.CSTTransformer):
    """Delete a method from a class and return sentinel if class becomes empty."""

    def __init__(self, method_name: str, class_name: str):
        self.method_name = method_name
        self.class_name = class_name
        self.deleted = False

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        if updated_node.name.value == self.class_name:
            new_body = [
                node
                for node in updated_node.body.body
                if not (isinstance(node, cst.FunctionDef) and node.name.value == self.method_name)
            ]
            if len(new_body) != len(updated_node.body.body):
                self.deleted = True
            return updated_node.with_changes(body=updated_node.body.with_changes(body=new_body))
        return updated_node


def delete_function(
    module_path: Path,
    function_name: str,
    class_name: Optional[str] = None,
) -> dict[str, Any]:
    """Delete a function from a module or class.

    Args:
        module_path: Path to the Python module
        function_name: Name of the function to delete
        class_name: Class name if deleting a method

    Returns:
        Result dict with operation details
    """
    source = module_path.read_text()

    # Use base class type to satisfy mypy
    transformer: cst.CSTTransformer
    if class_name:
        transformer = ClassMethodDeleter(
            method_name=function_name,
            class_name=class_name,
        )
    else:
        transformer = DeleteTransformer(
            delete_type="function",
            target_name=function_name,
            target_class=None,
        )

    tree = cst.parse_module(source)
    new_tree = tree.visit(transformer)

    # Both transformer types have a 'deleted' attribute
    deleted = bool(getattr(transformer, "deleted", False))

    if not deleted:
        raise ValueError(f"Function '{function_name}' not found" + (f" in class '{class_name}'" if class_name else ""))

    # Write back
    new_source = new_tree.code
    module_path.write_text(new_source)

    return {
        "operation": "delete_function",
        "target": {
            "module": str(module_path),
            "class": class_name,
            "function": function_name,
        },
        "modified": True,
    }


def delete_class(
    module_path: Path,
    class_name: str,
) -> dict[str, Any]:
    """Delete a class from a module.

    Args:
        module_path: Path to the Python module
        class_name: Name of the class to delete

    Returns:
        Result dict with operation details
    """
    source = module_path.read_text()

    transformer = DeleteTransformer(
        delete_type="class",
        target_name=class_name,
    )

    tree = cst.parse_module(source)
    new_tree = tree.visit(transformer)

    if not transformer.deleted:
        raise ValueError(f"Class '{class_name}' not found")

    # For class deletion, we need to handle it differently
    # since we can't directly remove from Module body
    # We'll use a module-level visitor
    new_tree = _remove_class_from_module(new_tree, class_name)

    # Write back
    new_source = new_tree.code
    module_path.write_text(new_source)

    return {
        "operation": "delete_class",
        "target": {
            "module": str(module_path),
            "class": class_name,
        },
        "modified": True,
    }


def _remove_class_from_module(tree: cst.Module, class_name: str) -> cst.Module:
    """Remove a class from module body."""
    new_body: list[cst.BaseStatement] = []
    for node in tree.body:
        if isinstance(node, cst.ClassDef):
            if node.name.value != class_name:
                new_body.append(node)
        else:
            new_body.append(node)
    return tree.with_changes(body=new_body)
