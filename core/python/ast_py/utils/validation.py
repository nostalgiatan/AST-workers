"""Syntax validation utilities."""

import ast
from pathlib import Path
from typing import Any


def validate_syntax(source: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "valid": True,
        "error": None,
        "error_line": None,
        "error_column": None,
    }

    try:
        ast.parse(source)
    except SyntaxError as e:
        result["valid"] = False
        result["error"] = str(e)
        result["error_line"] = e.lineno
        result["error_column"] = e.offset
        result["error_text"] = e.text

    return result


def validate_module(module_path: Path) -> dict[str, Any]:
    """Validate a Python module's syntax.

    Args:
        module_path: Path to the Python module

    Returns:
        Validation result dict
    """
    source = module_path.read_text()
    result = validate_syntax(source)
    result["module"] = str(module_path)
    return result


def check_for_issues(source: str) -> list[dict[str, Any]]:
    """Check for common issues in Python code.

    Args:
        source: Python source code string

    Returns:
        List of issues found
    """
    issues: list[dict[str, Any]] = []

    # First validate syntax
    validation = validate_syntax(source)
    if not validation["valid"]:
        issues.append(
            {
                "type": "syntax_error",
                "line": validation["error_line"],
                "column": validation["error_column"],
                "message": validation["error"],
            }
        )
        return issues  # Can't check further if syntax is invalid

    tree = ast.parse(source)

    # Check for undefined names (simple check)
    defined_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            defined_names.add(node.name)
        elif isinstance(node, ast.ClassDef):
            defined_names.add(node.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name.split(".")[0]
                defined_names.add(name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname or alias.name
                defined_names.add(name)

    # Check for redefined functions
    func_defs: dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name in func_defs and not node.name.startswith("_"):
                issues.append(
                    {
                        "type": "redefinition",
                        "line": node.lineno,
                        "name": node.name,
                        "message": f"Function '{node.name}' redefined (first at line {func_defs[node.name]})",
                    }
                )
            func_defs[node.name] = node.lineno

    return issues
