"""Query operations for inspecting Python AST."""

import ast
from pathlib import Path
from typing import Any, Optional


def list_functions(
    module_path: Path,
    class_name: Optional[str] = None,
    include_private: bool = False,
) -> dict[str, Any]:
    """List functions in a module or class.

    Args:
        module_path: Path to the Python module
        class_name: Filter by class name (for methods)
        include_private: Include private methods (starting with _)

    Returns:
        Result dict with list of functions
    """
    source = module_path.read_text()
    tree = ast.parse(source)

    result: dict[str, Any] = {
        "operation": "list_functions",
        "target": {
            "module": str(module_path),
            "class": class_name,
        },
        "functions": [],
    }

    def extract_function_info(node: ast.FunctionDef | ast.AsyncFunctionDef, is_method: bool = False) -> dict:
        params = []

        # Positional-only args (Python 3.8+)
        # Defaults for positional-only are at the START of defaults
        num_posonly = len(node.args.posonlyargs)
        num_pos_defaults = len(node.args.defaults) - len(node.args.args)

        for i, arg in enumerate(node.args.posonlyargs):
            param = {
                "name": arg.arg,
                "annotation": ast.unparse(arg.annotation) if arg.annotation else None,
                "kind": "positional_only",
            }
            # Check for default value (from the beginning of defaults)
            default_idx = i - num_posonly + num_pos_defaults
            if default_idx >= 0 and node.args.defaults and default_idx < len(node.args.defaults):
                param["default"] = ast.unparse(node.args.defaults[default_idx])
            params.append(param)

        # Regular args
        # Defaults for regular args are at the END of defaults
        num_defaults = len(node.args.defaults)
        num_args = len(node.args.args)

        for i, arg in enumerate(node.args.args):
            param = {
                "name": arg.arg,
                "annotation": ast.unparse(arg.annotation) if arg.annotation else None,
            }
            # Check for default value
            default_idx = i - num_args + num_defaults
            if default_idx >= 0:
                param["default"] = ast.unparse(node.args.defaults[default_idx])
            params.append(param)

        # *args
        if node.args.vararg:
            params.append(
                {
                    "name": f"*{node.args.vararg.arg}",
                    "annotation": (ast.unparse(node.args.vararg.annotation) if node.args.vararg.annotation else None),
                    "kind": "var_positional",
                }
            )

        # Keyword-only args
        for i, arg in enumerate(node.args.kwonlyargs):
            param = {
                "name": arg.arg,
                "annotation": ast.unparse(arg.annotation) if arg.annotation else None,
                "kind": "keyword_only",
            }
            if node.args.kw_defaults and node.args.kw_defaults[i] is not None:
                default_val = node.args.kw_defaults[i]
                assert default_val is not None  # for mypy
                param["default"] = ast.unparse(default_val)
            params.append(param)

        # **kwargs
        if node.args.kwarg:
            params.append(
                {
                    "name": f"**{node.args.kwarg.arg}",
                    "annotation": (ast.unparse(node.args.kwarg.annotation) if node.args.kwarg.annotation else None),
                    "kind": "var_keyword",
                }
            )

        # Get docstring
        docstring = ast.get_docstring(node)

        return {
            "name": node.name,
            "line": node.lineno,
            "end_line": node.end_lineno,
            "is_async": isinstance(node, ast.AsyncFunctionDef),
            "is_method": is_method,
            "params": params,
            "return_type": ast.unparse(node.returns) if node.returns else None,
            "decorators": [ast.unparse(d) for d in node.decorator_list],
            "docstring": docstring,
        }

    if class_name:
        # Find class and list methods
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if include_private or not item.name.startswith("_"):
                            result["functions"].append(extract_function_info(item, is_method=True))
                break
    else:
        # List module-level functions
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if include_private or not node.name.startswith("_"):
                    result["functions"].append(extract_function_info(node))

    return result


def list_classes(module_path: Path) -> dict[str, Any]:
    """List classes in a module.

    Args:
        module_path: Path to the Python module

    Returns:
        Result dict with list of classes
    """
    source = module_path.read_text()
    tree = ast.parse(source)

    result: dict[str, Any] = {
        "operation": "list_classes",
        "target": {"module": str(module_path)},
        "classes": [],
    }

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_info: dict[str, Any] = {
                "name": node.name,
                "line": node.lineno,
                "end_line": node.end_lineno,
                "bases": [ast.unparse(b) for b in node.bases],
                "decorators": [ast.unparse(d) for d in node.decorator_list],
                "methods": [],
                "class_vars": [],
                "docstring": ast.get_docstring(node),
            }

            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    class_info["methods"].append(item.name)
                elif isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            class_info["class_vars"].append(target.id)
                elif isinstance(item, ast.AnnAssign):
                    if isinstance(item.target, ast.Name):
                        class_info["class_vars"].append(item.target.id)

            result["classes"].append(class_info)

    return result


def list_imports(module_path: Path) -> dict[str, Any]:
    """List imports in a module.

    Args:
        module_path: Path to the Python module

    Returns:
        Result dict with list of imports
    """
    source = module_path.read_text()
    tree = ast.parse(source)

    result: dict[str, Any] = {
        "operation": "list_imports",
        "target": {"module": str(module_path)},
        "imports": [],
    }

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                result["imports"].append(
                    {
                        "type": "import",
                        "module": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno,
                    }
                )
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                result["imports"].append(
                    {
                        "type": "from",
                        "module": node.module,
                        "name": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno,
                    }
                )

    return result


def find_symbol(
    module_path: Path,
    name: str,
    symbol_type: Optional[str] = None,
) -> dict[str, Any]:
    """Find a symbol (function, class, or variable) in a module.

    Args:
        module_path: Path to the Python module
        name: Symbol name to find
        symbol_type: Type of symbol ('function', 'class', 'variable', or None for any)

    Returns:
        Result dict with symbol information
    """
    source = module_path.read_text()
    tree = ast.parse(source)

    result: dict[str, Any] = {
        "operation": "find_symbol",
        "target": {
            "module": str(module_path),
            "name": name,
            "type": symbol_type,
        },
        "found": False,
        "symbols": [],
    }

    for node in tree.body:
        # Check functions
        if symbol_type in (None, "function"):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == name:
                    result["symbols"].append(
                        {
                            "type": "function",
                            "name": node.name,
                            "line": node.lineno,
                            "end_line": node.end_lineno,
                            "is_async": isinstance(node, ast.AsyncFunctionDef),
                        }
                    )

        # Check classes
        if symbol_type in (None, "class"):
            if isinstance(node, ast.ClassDef):
                if node.name == name:
                    result["symbols"].append(
                        {
                            "type": "class",
                            "name": node.name,
                            "line": node.lineno,
                            "end_line": node.end_lineno,
                        }
                    )

        # Check module-level variables
        if symbol_type in (None, "variable"):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == name:
                        result["symbols"].append(
                            {
                                "type": "variable",
                                "name": name,
                                "line": node.lineno,
                            }
                        )
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name) and node.target.id == name:
                    result["symbols"].append(
                        {
                            "type": "variable",
                            "name": name,
                            "line": node.lineno,
                        }
                    )

    result["found"] = len(result["symbols"]) > 0
    return result


def show_symbol(module_path: Path, name: str, symbol_type: Optional[str] = None) -> dict[str, Any]:
    """Show a symbol with surrounding context.

    Supports scoped naming like 'Class.method' or 'Class.InnerClass.method'.

    Args:
        module_path: Path to the Python module
        name: Symbol name, supports dot notation for scope (e.g., 'Class.method')
        symbol_type: Optional type filter ('function', 'class', 'variable', 'import')

    Returns:
        Result dict with symbol location and surrounding code
    """
    source = module_path.read_text()
    lines = source.splitlines()
    tree = ast.parse(source)

    result: dict[str, Any] = {
        "operation": "show_symbol",
        "target": {"name": name, "type": symbol_type},
        "found": False,
    }

    # Parse scoped name (e.g., "Class.method" -> ["Class", "method"])
    scope_parts = name.split(".")
    target_name = scope_parts[-1]
    scope_path = scope_parts[:-1]

    def find_in_scope(nodes: list[ast.stmt], scope_idx: int = 0) -> ast.AST | None:
        """Recursively find symbol in scope chain."""
        for node in nodes:
            # Check if we need to match scope
            if scope_idx < len(scope_path):
                # We're looking for a scope container (class/function)
                scope_name = scope_path[scope_idx]

                if isinstance(node, ast.ClassDef) and node.name == scope_name:
                    # Found the class, continue searching in its body
                    return find_in_scope(list(node.body), scope_idx + 1)

                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == scope_name:
                    # Found a function scope, continue searching
                    return find_in_scope(list(node.body), scope_idx + 1)
            else:
                # We're at the target scope, look for the symbol
                matched = _match_symbol(node, target_name, symbol_type)
                if matched is not None:
                    return matched

        return None

    def _match_symbol(node: ast.AST, target: str, stype: Optional[str]) -> ast.AST | None:
        """Check if node matches the target symbol."""
        # Function (including async)
        if stype in (None, "function"):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == target:
                    return node

        # Class
        if stype in (None, "class"):
            if isinstance(node, ast.ClassDef):
                if node.name == target:
                    return node

        # Variable (assignment)
        if stype in (None, "variable"):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and t.id == target:
                        return node
            if isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name) and node.target.id == target:
                    return node

        # Import
        if stype in (None, "import"):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == target or alias.asname == target:
                        return node
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == target or alias.asname == target:
                        return node

        return None

    matched_node = find_in_scope(list(tree.body))

    if matched_node is not None and hasattr(matched_node, "lineno"):
        lineno = matched_node.lineno
        end_lineno = getattr(matched_node, "end_lineno", lineno)

        if lineno is not None:
            result["found"] = True
            result["line"] = lineno
            result["end_line"] = end_lineno

            # Determine symbol type
            if isinstance(matched_node, ast.AsyncFunctionDef):
                result["symbol_type"] = "async_function"
            elif isinstance(matched_node, ast.FunctionDef):
                result["symbol_type"] = "function"
            elif isinstance(matched_node, ast.ClassDef):
                result["symbol_type"] = "class"
            elif isinstance(matched_node, (ast.Assign, ast.AnnAssign)):
                result["symbol_type"] = "variable"
            elif isinstance(matched_node, (ast.Import, ast.ImportFrom)):
                result["symbol_type"] = "import"
            else:
                result["symbol_type"] = "unknown"

            # Get surrounding context (4 lines before, 3 after)
            start = max(0, lineno - 4)
            end = min(len(lines), (end_lineno or lineno) + 3)
            result["code"] = "\n".join(lines[start:end])

            # Add docstring if available
            if isinstance(matched_node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                result["docstring"] = ast.get_docstring(matched_node)

    return result
