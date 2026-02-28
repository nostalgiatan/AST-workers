"""AST operations for Python code modification.

Uses libcst for preserving formatting when available, falls back to ast module.
"""

import ast
import re
from pathlib import Path
from typing import Any


def parse_params(params_str: str) -> list[dict]:
    """Parse parameter string into structured data.

    Examples:
        "x:int, y:str='default'" -> [{"name": "x", "annotation": "int"}, ...]
    """
    if not params_str.strip():
        return []

    params = []
    # Split by comma, but handle nested brackets/quotes
    parts = []
    current = ""
    depth = 0
    in_string = False
    string_char = None

    for char in params_str:
        if char in ('"', "'") and (not in_string or char == string_char):
            if in_string and current.endswith("\\"):
                pass  # escaped
            else:
                in_string = not in_string
                string_char = char if in_string else None
        elif char in "([{<":
            depth += 1
        elif char in ")]}>":
            depth -= 1
        elif char == "," and depth == 0 and not in_string:
            parts.append(current.strip())
            current = ""
            continue
        current += char
    if current.strip():
        parts.append(current.strip())

    for part in parts:
        param = {"name": None, "annotation": None, "default": None}

        # Check for default value
        if "=" in part:
            eq_pos = part.index("=")
            default_part = part[eq_pos + 1 :].strip()
            name_annot = part[:eq_pos].strip()
            param["default"] = default_part
        else:
            name_annot = part

        # Check for type annotation
        if ":" in name_annot:
            colon_pos = name_annot.index(":")
            param["name"] = name_annot[:colon_pos].strip()
            param["annotation"] = name_annot[colon_pos + 1 :].strip()
        else:
            param["name"] = name_annot.strip()

        params.append(param)

    return params


def get_indentation(line: str) -> str:
    """Get the indentation string from a line."""
    match = re.match(r"^(\s*)", line)
    return match.group(1) if match else ""


def find_class_end(source_lines: list[str], class_start: int, base_indent: str) -> int:
    """Find the line number after the last method/attribute of a class."""
    i = class_start + 1
    last_content = class_start

    while i < len(source_lines):
        line = source_lines[i]
        stripped = line.strip()

        # Empty line, continue
        if not stripped:
            i += 1
            continue

        indent = get_indentation(line)

        # If indent is back to or less than class indent, class has ended
        if len(indent) <= len(base_indent):
            break

        # Still inside class
        last_content = i
        i += 1

    return last_content


def find_function_end(source_lines: list[str], func_start: int, base_indent: str) -> int:
    """Find the last line of a function."""
    i = func_start + 1
    last_content = func_start

    while i < len(source_lines):
        line = source_lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        indent = get_indentation(line)

        # If indent is back to or less than function indent, function has ended
        if len(indent) <= len(base_indent):
            break

        last_content = i
        i += 1

    return last_content


def generate_function_code(
    function_name: str,
    params: list[dict],
    return_type: str | None,
    body: str,
    indent: str,
    is_async: bool = False,
    decorators: list[str] | None = None,
) -> str:
    """Generate function code as string."""
    lines = []

    # Decorators
    if decorators:
        for dec in decorators:
            if dec.startswith("@"):
                lines.append(f"{indent}{dec}")
            else:
                lines.append(f"{indent}@{dec}")

    # Function signature
    async_kw = "async " if is_async else ""
    params_str = ", ".join(
        p["name"]
        + (f": {p['annotation']}" if p.get("annotation") else "")
        + (f" = {p['default']}" if p.get("default") else "")
        for p in params
    )

    return_annot = f" -> {return_type}" if return_type else ""
    sig = f"{indent}{async_kw}def {function_name}({params_str}){return_annot}:"
    lines.append(sig)

    # Body
    body_indent = indent + "    "
    body_lines = body.strip().split("\n")
    for bline in body_lines:
        if bline.strip():
            lines.append(f"{body_indent}{bline.strip()}")
        else:
            lines.append("")

    if not body.strip() or body.strip() == "pass":
        lines.append(f"{body_indent}pass")

    return "\n".join(lines)


def insert_function(
    module_path: Path,
    function_name: str,
    params_str: str = "",
    return_type: str | None = None,
    body: str = "pass",
    class_name: str | None = None,
    decorators: str | None = None,
    is_async: bool = False,
    after: str | None = None,
    before: str | None = None,
) -> dict[str, Any]:
    """Insert a function into a module or class."""

    source = module_path.read_text()
    source_lines = source.split("\n")
    tree = ast.parse(source)

    # Parse parameters
    params = parse_params(params_str)

    # Parse decorators
    dec_list = None
    if decorators:
        dec_list = [d.strip() for d in decorators.split(",")]

    result = {
        "operation": "insert_function",
        "target": {
            "module": str(module_path),
            "class": class_name,
            "function": function_name,
        },
        "modified": False,
    }

    if class_name:
        # Find the class
        class_node = None
        class_start_line = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                class_node = node
                class_start_line = node.lineno - 1  # 0-indexed
                break

        if not class_node:
            raise ValueError(f"Class '{class_name}' not found in module")

        # Get class indentation
        class_indent = get_indentation(source_lines[class_start_line])
        method_indent = class_indent + "    "

        # Auto-add 'self' parameter for methods if not present
        if params and params[0]["name"] != "self":
            params.insert(0, {"name": "self", "annotation": None, "default": None})
        elif not params:
            params = [{"name": "self", "annotation": None, "default": None}]

        # Find insert position
        insert_line = None

        if after:
            # Find the method to insert after
            for item in class_node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == after:
                    func_start = item.lineno - 1
                    func_indent = get_indentation(source_lines[func_start])
                    insert_line = find_function_end(source_lines, func_start, func_indent) + 1
                    break
        elif before:
            # Find the method to insert before
            for item in class_node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == before:
                    insert_line = item.lineno - 1
                    break

        if insert_line is None:
            # Insert at end of class
            insert_line = find_class_end(source_lines, class_start_line, class_indent) + 1

        # Generate function code
        func_code = generate_function_code(
            function_name=function_name,
            params=params,
            return_type=return_type,
            body=body,
            indent=method_indent,
            is_async=is_async,
            decorators=dec_list,
        )

        # Insert into source
        source_lines.insert(insert_line, "")
        source_lines.insert(insert_line + 1, func_code)
        result["location"] = {"line": insert_line + 1}

    else:
        # Insert at module level
        insert_line = len(source_lines)  # Default: end of file

        if after:
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == after:
                    func_start = node.lineno - 1
                    func_indent = get_indentation(source_lines[func_start])
                    insert_line = find_function_end(source_lines, func_start, func_indent) + 1
                    break
        elif before:
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == before:
                    insert_line = node.lineno - 1
                    break

        # Generate function code
        func_code = generate_function_code(
            function_name=function_name,
            params=params,
            return_type=return_type,
            body=body,
            indent="",
            is_async=is_async,
            decorators=dec_list,
        )

        if insert_line >= len(source_lines):
            source_lines.append("")
            source_lines.append(func_code)
            result["location"] = {"line": len(source_lines)}
        else:
            source_lines.insert(insert_line, "")
            source_lines.insert(insert_line + 1, func_code)
            result["location"] = {"line": insert_line + 1}

    # Write back
    new_source = "\n".join(source_lines)
    module_path.write_text(new_source)
    result["modified"] = True

    return result


def insert_class(
    module_path: Path,
    class_name: str,
    bases: str | None = None,
    decorators: str | None = None,
    after: str | None = None,
) -> dict[str, Any]:
    """Insert a class into a module."""

    source = module_path.read_text()
    source_lines = source.split("\n")
    tree = ast.parse(source)

    result = {
        "operation": "insert_class",
        "target": {
            "module": str(module_path),
            "class": class_name,
        },
        "modified": False,
    }

    # Build class code
    lines = []

    if decorators:
        for dec in decorators.split(","):
            dec = dec.strip()
            if dec.startswith("@"):
                lines.append(dec)
            else:
                lines.append(f"@{dec}")

    bases_str = ""
    if bases:
        bases_str = f"({bases})"

    lines.append(f"class {class_name}{bases_str}:")
    lines.append("    pass")

    class_code = "\n".join(lines)

    # Find insert position
    insert_line = len(source_lines)

    if after:
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name == after:
                    node_start = node.lineno - 1
                    node_indent = get_indentation(source_lines[node_start])
                    insert_line = find_function_end(source_lines, node_start, node_indent) + 1
                    break

    if insert_line >= len(source_lines):
        source_lines.append("")
        source_lines.append(class_code)
        result["location"] = {"line": len(source_lines)}
    else:
        source_lines.insert(insert_line, "")
        source_lines.insert(insert_line + 1, class_code)
        result["location"] = {"line": insert_line + 1}

    new_source = "\n".join(source_lines)
    module_path.write_text(new_source)
    result["modified"] = True

    return result


def insert_import(
    module_path: Path,
    name: str | None = None,
    from_module: str | None = None,
    alias: str | None = None,
) -> dict[str, Any]:
    """Insert an import statement."""

    source = module_path.read_text()
    source_lines = source.split("\n")
    tree = ast.parse(source)

    result = {
        "operation": "insert_import",
        "target": {
            "module": str(module_path),
        },
        "modified": False,
    }

    # Build import statement
    if from_module:
        if name:
            import_str = f"from {from_module} import {name}"
        else:
            import_str = f"from {from_module} import *"
    else:
        import_str = f"import {name}"

    if alias and not (from_module and name is None):
        import_str += f" as {alias}"

    result["target"]["import"] = import_str

    # Find position after last import
    last_import_line = -1
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            last_import_line = node.end_lineno

    if last_import_line >= 0:
        source_lines.insert(last_import_line, import_str)
        result["location"] = {"line": last_import_line}
    else:
        # Insert at beginning
        source_lines.insert(0, import_str)
        source_lines.insert(1, "")
        result["location"] = {"line": 1}

    new_source = "\n".join(source_lines)
    module_path.write_text(new_source)
    result["modified"] = True

    return result


def list_functions(
    module_path: Path,
    class_name: str | None = None,
    include_private: bool = False,
) -> dict[str, Any]:
    """List functions in a module or class."""

    source = module_path.read_text()
    tree = ast.parse(source)

    result = {
        "operation": "list_functions",
        "target": {
            "module": str(module_path),
            "class": class_name,
        },
        "functions": [],
    }

    def extract_function_info(node, is_method: bool = False) -> dict:
        params = []
        for arg in node.args.args:
            param = {"name": arg.arg}
            if arg.annotation:
                param["annotation"] = ast.unparse(arg.annotation)
            params.append(param)

        # Handle *args
        if node.args.vararg:
            params.append(
                {
                    "name": f"*{node.args.vararg.arg}",
                    "annotation": (ast.unparse(node.args.vararg.annotation) if node.args.vararg.annotation else None),
                }
            )

        # Handle **kwargs
        if node.args.kwarg:
            params.append(
                {
                    "name": f"**{node.args.kwarg.arg}",
                    "annotation": (ast.unparse(node.args.kwarg.annotation) if node.args.kwarg.annotation else None),
                }
            )

        return {
            "name": node.name,
            "line": node.lineno,
            "is_async": isinstance(node, ast.AsyncFunctionDef),
            "is_method": is_method,
            "params": params,
            "return_type": ast.unparse(node.returns) if node.returns else None,
            "decorators": [ast.unparse(d) for d in node.decorator_list],
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
    """List classes in a module."""

    source = module_path.read_text()
    tree = ast.parse(source)

    result = {
        "operation": "list_classes",
        "target": {"module": str(module_path)},
        "classes": [],
    }

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_info = {
                "name": node.name,
                "line": node.lineno,
                "bases": [ast.unparse(b) for b in node.bases],
                "decorators": [ast.unparse(d) for d in node.decorator_list],
                "methods": [],
            }
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    class_info["methods"].append(item.name)
            result["classes"].append(class_info)

    return result


def list_imports(module_path: Path) -> dict[str, Any]:
    """List imports in a module."""

    source = module_path.read_text()
    tree = ast.parse(source)

    result = {
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


def delete_function(
    module_path: Path,
    function_name: str,
    class_name: str | None = None,
) -> dict[str, Any]:
    """Delete a function from a module or class."""

    source = module_path.read_text()
    source_lines = source.split("\n")
    tree = ast.parse(source)

    result = {
        "operation": "delete_function",
        "target": {
            "module": str(module_path),
            "class": class_name,
            "function": function_name,
        },
        "modified": False,
    }

    def find_and_delete(body_nodes, parent_indent: str = "") -> bool:
        for node in body_nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
                func_start = node.lineno - 1
                func_indent = get_indentation(source_lines[func_start])
                func_end = find_function_end(source_lines, func_start, func_indent)

                # Delete lines (in reverse order to maintain indices)
                for i in range(func_end, func_start - 1, -1):
                    del source_lines[i]

                result["location"] = {"line": func_start + 1, "end_line": func_end + 1}
                return True
        return False

    if class_name:
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                class_indent = get_indentation(source_lines[node.lineno - 1])
                if find_and_delete(node.body, class_indent + "    "):
                    break
    else:
        find_and_delete(tree.body)

    new_source = "\n".join(source_lines)
    module_path.write_text(new_source)
    result["modified"] = True

    return result


def rename_symbol(
    module_path: Path,
    old_name: str,
    new_name: str,
    symbol_type: str = "function",
) -> dict[str, Any]:
    """Rename a symbol in a module."""

    source = module_path.read_text()
    ast.parse(source)

    result = {
        "operation": "rename_symbol",
        "target": {
            "module": str(module_path),
            "old_name": old_name,
            "new_name": new_name,
            "type": symbol_type,
        },
        "modified": False,
        "occurrences": [],
    }

    # Find all occurrences and replace
    # This is a simple string-based approach for now
    # A more sophisticated approach would use AST transformation

    lines = source.split("\n")
    modified_lines = []

    # Pattern to match the symbol (word boundary)
    pattern = r"\b" + re.escape(old_name) + r"\b"

    for i, line in enumerate(lines):
        new_line, count = re.subn(pattern, new_name, line)
        if count > 0:
            result["occurrences"].append({"line": i + 1, "count": count})
        modified_lines.append(new_line)

    new_source = "\n".join(modified_lines)
    module_path.write_text(new_source)
    result["modified"] = len(result["occurrences"]) > 0

    return result
