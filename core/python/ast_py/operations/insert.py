"""Insert operations using libcst for AST-level code manipulation."""

from pathlib import Path
from typing import Any, Optional, Sequence

import libcst as cst

from ..generator.function import generate_function_node
from ..generator.imports import generate_import_node
from ..generator.klass import generate_class_node
from ..parser.params import parse_params


class InsertTransformer(cst.CSTTransformer):
    """CST Transformer for inserting nodes."""

    def __init__(
        self,
        insert_type: str,
        target_name: Optional[str] = None,
        target_class: Optional[str] = None,
        node_to_insert: Optional[cst.CSTNode] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        insert_at_start: bool = False,
    ):
        self.insert_type = insert_type
        self.target_name = target_name
        self.target_class = target_class
        self.node_to_insert = node_to_insert
        self.after = after
        self.before = before
        self.insert_at_start = insert_at_start
        self.inserted: bool = False
        self.insert_position: int | None = None

    def leave_ClassDef(
        self,
        original_node: cst.ClassDef,
        updated_node: cst.ClassDef,
    ) -> cst.ClassDef:
        """Handle inserting into a class."""
        if self.target_class and original_node.name.value == self.target_class:
            if self.insert_type in ("function", "class_variable", "slots"):
                new_body = self._insert_into_body(
                    updated_node.body.body,
                    original_node.body.body,
                )
                return updated_node.with_changes(body=updated_node.body.with_changes(body=new_body))
        return updated_node

    def leave_Module(
        self,
        original_node: cst.Module,
        updated_node: cst.Module,
    ) -> cst.Module:
        """Handle inserting at module level."""
        if self.insert_type == "import":
            new_body = self._insert_import(updated_node.body)
            return updated_node.with_changes(body=new_body)

        if self.insert_type in ("function", "class", "dunder_all") and not self.target_class:
            new_body = self._insert_into_body(
                updated_node.body,
                original_node.body,
            )
            return updated_node.with_changes(body=new_body)

        return updated_node

    def _insert_into_body(
        self,
        new_body: Sequence[Any],
        original_body: Sequence[Any],
    ) -> list[Any]:
        """Insert node into body list at appropriate position."""
        if self.inserted:
            return list(new_body)

        result = list(new_body)

        # Insert at start of class body (for class variables, __slots__)
        if self.insert_at_start:
            # Find first non-docstring statement
            insert_idx = 0
            for i, node in enumerate(original_body):
                if isinstance(node, cst.SimpleStatementLine):
                    # Check if it's a docstring
                    if len(node.body) == 1 and isinstance(node.body[0], cst.Expr):
                        if isinstance(node.body[0].value, cst.SimpleString):
                            insert_idx = i + 1
                            continue
                insert_idx = i
                break
            result.insert(insert_idx, self.node_to_insert)
            self.inserted = True
            self.insert_position = insert_idx
            return result

        if self.before:
            # Find the target and insert before it
            for i, node in enumerate(original_body):
                name = self._get_node_name(node)
                if name == self.before:
                    result.insert(i, self.node_to_insert)
                    self.inserted = True
                    self.insert_position = i
                    break
        elif self.after:
            # Find the target and insert after it
            for i, node in enumerate(original_body):
                name = self._get_node_name(node)
                if name == self.after:
                    result.insert(i + 1, self.node_to_insert)
                    self.inserted = True
                    self.insert_position = i + 1
                    break

        if not self.inserted:
            # Append at end
            result.append(self.node_to_insert)
            self.inserted = True
            self.insert_position = len(result) - 1

        return result

    def _insert_import(self, body: Sequence[Any]) -> list[Any]:
        """Insert import at the appropriate position."""
        result = list(body)

        # Find last import
        last_import_idx = -1
        for i, node in enumerate(result):
            if isinstance(node, (cst.Import, cst.ImportFrom)):
                last_import_idx = i
            elif isinstance(node, cst.SimpleStatementLine):
                if node.body and isinstance(node.body[0], (cst.Import, cst.ImportFrom)):
                    last_import_idx = i

        if last_import_idx >= 0:
            result.insert(last_import_idx + 1, self.node_to_insert)
        else:
            # Insert at beginning
            result.insert(0, self.node_to_insert)

        self.inserted = True
        self.insert_position = last_import_idx + 1 if last_import_idx >= 0 else 0
        return result

    def _get_node_name(self, node: cst.CSTNode) -> Optional[str]:
        """Get the name of a node (function, class)."""
        if isinstance(node, (cst.FunctionDef, cst.ClassDef)):
            return node.name.value
        if isinstance(node, cst.SimpleStatementLine):
            # Could be decorated function/class
            pass
        return None


def insert_function(
    module_path: Path,
    function_name: str,
    params_str: str = "",
    return_type: Optional[str] = None,
    body: str | list[str | tuple] = "pass",
    class_name: Optional[str] = None,
    decorators: Optional[str] = None,
    is_async: bool = False,
    docstring: Optional[str] = None,
    after: Optional[str] = None,
    before: Optional[str] = None,
) -> dict[str, Any]:
    """Insert a function into a module or class."""
    source = module_path.read_text()

    # Parse parameters
    params = parse_params(params_str)

    # Auto-add 'self' for methods if not present
    if class_name:
        if not params or params[0].name != "self":
            from ..parser.params import ParamInfo, ParamKind

            params.insert(0, ParamInfo(name="self", kind=ParamKind.POSITIONAL_OR_KEYWORD))

    # Parse decorators
    dec_list = None
    if decorators:
        dec_list = [d.strip() for d in decorators.split(",")]

    # Handle body - parse JSON if it's a string that looks like a list
    parsed_body: str | list[str | tuple] = body
    if isinstance(body, str) and body.strip().startswith("["):
        import json

        try:
            parsed_body = json.loads(body)
        except json.JSONDecodeError:
            pass  # Keep as string if not valid JSON

    # Generate function node
    func_node = generate_function_node(
        name=function_name,
        params=params,
        body=parsed_body,
        return_type=return_type,
        decorators=dec_list,
        is_async=is_async,
        docstring=docstring,
    )

    node_to_insert = func_node

    # Create transformer
    transformer = InsertTransformer(
        insert_type="function",
        target_name=function_name,
        target_class=class_name,
        node_to_insert=node_to_insert,
        after=after,
        before=before,
    )

    # Parse and transform
    tree = cst.parse_module(source)
    new_tree = tree.visit(transformer)

    if not transformer.inserted:
        raise ValueError(
            f"Could not insert function '{function_name}'" + (f" into class '{class_name}'" if class_name else "")
        )

    # Write back
    new_source = new_tree.code
    module_path.write_text(new_source)

    return {
        "operation": "insert_function",
        "target": {
            "module": str(module_path),
            "class": class_name,
            "function": function_name,
        },
        "modified": True,
        "location": {"position": transformer.insert_position},
    }


def insert_class(
    module_path: Path,
    class_name: str,
    bases: Optional[str] = None,
    decorators: Optional[str] = None,
    docstring: Optional[str] = None,
    class_vars: Optional[str] = None,
    after: Optional[str] = None,
    before: Optional[str] = None,
) -> dict[str, Any]:
    """Insert a class into a module.

    Args:
        module_path: Path to the Python module
        class_name: Name of the class to insert
        bases: Comma-separated base classes
        decorators: Comma-separated decorator strings
        docstring: Class docstring
        class_vars: Class variables (format: "name:type=value,..." or "name=value,...")
        after: Insert after this function/class name
        before: Insert before this function/class name
    """
    source = module_path.read_text()

    # Parse bases
    base_list = None
    if bases:
        base_list = [b.strip() for b in bases.split(",")]

    # Parse decorators
    dec_list = None
    if decorators:
        dec_list = [d.strip() for d in decorators.split(",")]

    # Parse class vars
    body_nodes = []

    # Add docstring first
    if docstring:
        body_nodes.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.SimpleString(value=f'"""{docstring}"""'))]))

    # Add class variables
    if class_vars:
        var_nodes = _parse_class_vars(class_vars)
        body_nodes.extend(var_nodes)

    # Add pass if no body
    if not body_nodes:
        body_nodes = [cst.SimpleStatementLine(body=[cst.Pass()])]

    # Generate class node
    class_node = generate_class_node(
        name=class_name,
        bases=base_list,
        decorators=dec_list,
        body=body_nodes,
    )

    # Create transformer
    transformer = InsertTransformer(
        insert_type="class",
        target_name=class_name,
        node_to_insert=class_node,
        after=after,
        before=before,
    )

    # Parse and transform
    tree = cst.parse_module(source)
    new_tree = tree.visit(transformer)

    if not transformer.inserted:
        raise ValueError(f"Could not insert class '{class_name}'")

    # Write back
    new_source = new_tree.code
    module_path.write_text(new_source)

    return {
        "operation": "insert_class",
        "target": {
            "module": str(module_path),
            "class": class_name,
        },
        "modified": True,
        "location": {"position": transformer.insert_position},
    }


def _parse_class_vars(class_vars_str: str) -> list[cst.SimpleStatementLine]:
    """Parse class variables string into CST nodes.

    Formats:
        "name=value"
        "name:type=value"
        "count:int=0, name:str='test'"
    """
    nodes = []

    # Split by comma, respecting brackets and quotes
    parts = _split_respecting_brackets(class_vars_str)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        annotation = None
        value = None

        # Check for type annotation
        colon_pos = _find_colon_outside_brackets(part)
        if colon_pos >= 0:
            name_part = part[:colon_pos].strip()
            annotation = part[colon_pos + 1 :].strip()

            # Check for value in annotation part
            eq_pos = _find_equals_outside_brackets(annotation)
            if eq_pos >= 0:
                value = annotation[eq_pos + 1 :].strip()
                annotation = annotation[:eq_pos].strip()
        else:
            # No annotation, check for value
            eq_pos = _find_equals_outside_brackets(part)
            if eq_pos >= 0:
                name_part = part[:eq_pos].strip()
                value = part[eq_pos + 1 :].strip()
            else:
                name_part = part

        # Build the assignment
        if annotation and value:
            # AnnAssign: name: type = value
            node = cst.SimpleStatementLine(
                body=[
                    cst.AnnAssign(
                        target=cst.Name(value=name_part),
                        annotation=cst.Annotation(annotation=cst.parse_expression(annotation)),
                        value=cst.parse_expression(value),
                    )
                ]
            )
        elif annotation:
            # AnnAssign without value: name: type
            node = cst.SimpleStatementLine(
                body=[
                    cst.AnnAssign(
                        target=cst.Name(value=name_part),
                        annotation=cst.Annotation(annotation=cst.parse_expression(annotation)),
                    )
                ]
            )
        elif value:
            # Regular assign: name = value
            node = cst.SimpleStatementLine(
                body=[
                    cst.Assign(
                        targets=[cst.AssignTarget(target=cst.Name(value=name_part))],
                        value=cst.parse_expression(value),
                    )
                ]
            )
        else:
            continue

        nodes.append(node)

    return nodes


def _split_respecting_brackets(s: str) -> list[str]:
    """Split string by comma, respecting brackets and quotes."""
    parts = []
    current = ""
    depth = 0
    in_string = False
    string_char = None

    for char in s:
        if char in ('"', "'") and not in_string:
            in_string = True
            string_char = char
            current += char
        elif char == string_char and in_string:
            in_string = False
            string_char = None
            current += char
        elif not in_string:
            if char in "([{<":
                depth += 1
                current += char
            elif char in ")]}>":
                depth -= 1
                current += char
            elif char == "," and depth == 0:
                parts.append(current.strip())
                current = ""
            else:
                current += char
        else:
            current += char

    if current.strip():
        parts.append(current.strip())

    return parts


def _find_colon_outside_brackets(s: str) -> int:
    """Find first colon outside brackets and quotes."""
    depth = 0
    in_string = False
    string_char = None

    for i, char in enumerate(s):
        if char in ('"', "'") and not in_string:
            in_string = True
            string_char = char
        elif char == string_char and in_string:
            in_string = False
            string_char = None
        elif not in_string:
            if char in "([{<":
                depth += 1
            elif char in ")]}>":
                depth -= 1
            elif char == ":" and depth == 0:
                return i
    return -1


def _find_equals_outside_brackets(s: str) -> int:
    """Find first equals outside brackets and quotes."""
    depth = 0
    in_string = False
    string_char = None

    for i, char in enumerate(s):
        if char in ('"', "'") and not in_string:
            in_string = True
            string_char = char
        elif char == string_char and in_string:
            in_string = False
            string_char = None
        elif not in_string:
            if char in "([{<":
                depth += 1
            elif char in ")]}>":
                depth -= 1
            elif char == "=" and depth == 0:
                return i
    return -1


def insert_class_variable(
    module_path: Path,
    class_name: str,
    var_name: str,
    var_type: Optional[str] = None,
    var_value: Optional[str] = None,
) -> dict[str, Any]:
    """Insert a class variable into a class.

    Args:
        module_path: Path to the Python module
        class_name: Target class name
        var_name: Variable name
        var_type: Type annotation (optional)
        var_value: Initial value (optional)
    """
    source = module_path.read_text()

    # Build the assignment node
    if var_type and var_value:
        node = cst.SimpleStatementLine(
            body=[
                cst.AnnAssign(
                    target=cst.Name(value=var_name),
                    annotation=cst.Annotation(annotation=cst.parse_expression(var_type)),
                    value=cst.parse_expression(var_value),
                )
            ]
        )
    elif var_type:
        node = cst.SimpleStatementLine(
            body=[
                cst.AnnAssign(
                    target=cst.Name(value=var_name),
                    annotation=cst.Annotation(annotation=cst.parse_expression(var_type)),
                )
            ]
        )
    elif var_value:
        node = cst.SimpleStatementLine(
            body=[
                cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name(value=var_name))],
                    value=cst.parse_expression(var_value),
                )
            ]
        )
    else:
        raise ValueError("Must provide either var_type or var_value")

    # Create transformer
    transformer = InsertTransformer(
        insert_type="class_variable",
        target_class=class_name,
        node_to_insert=node,
        insert_at_start=True,
    )

    # Parse and transform
    tree = cst.parse_module(source)
    new_tree = tree.visit(transformer)

    if not transformer.inserted:
        raise ValueError(f"Could not insert variable into class '{class_name}'")

    # Write back
    new_source = new_tree.code
    module_path.write_text(new_source)

    return {
        "operation": "insert_class_variable",
        "target": {
            "module": str(module_path),
            "class": class_name,
            "variable": var_name,
        },
        "modified": True,
    }


def insert_slots(
    module_path: Path,
    class_name: str,
    slots: list[str],
) -> dict[str, Any]:
    """Insert __slots__ into a class.

    Args:
        module_path: Path to the Python module
        class_name: Target class name
        slots: List of slot names
    """
    source = module_path.read_text()

    # Build __slots__ assignment
    slot_strings = [f'"{s}"' for s in slots]
    slots_tuple = f"({', '.join(slot_strings)})"

    node = cst.SimpleStatementLine(
        body=[
            cst.Assign(
                targets=[cst.AssignTarget(target=cst.Name(value="__slots__"))],
                value=cst.parse_expression(slots_tuple),
            )
        ]
    )

    # Create transformer
    transformer = InsertTransformer(
        insert_type="slots",
        target_class=class_name,
        node_to_insert=node,
        insert_at_start=True,
    )

    # Parse and transform
    tree = cst.parse_module(source)
    new_tree = tree.visit(transformer)

    if not transformer.inserted:
        raise ValueError(f"Could not insert __slots__ into class '{class_name}'")

    # Write back
    new_source = new_tree.code
    module_path.write_text(new_source)

    return {
        "operation": "insert_slots",
        "target": {
            "module": str(module_path),
            "class": class_name,
            "slots": slots,
        },
        "modified": True,
    }


def insert_dunder_all(
    module_path: Path,
    names: list[str],
    mode: str = "replace",
) -> dict[str, Any]:
    """Insert or update __all__ in a module.

    Args:
        module_path: Path to the Python module
        names: List of names to export
        mode: "replace", "append", or "prepend"
    """
    source = module_path.read_text()
    tree = cst.parse_module(source)

    # Check if __all__ exists
    existing_all = None
    existing_all_idx = None

    for i, node in enumerate(tree.body):
        if isinstance(node, cst.SimpleStatementLine):
            for stmt in node.body:
                if isinstance(stmt, cst.Assign):
                    for target in stmt.targets:
                        if isinstance(target.target, cst.Name) and target.target.value == "__all__":
                            existing_all = stmt
                            existing_all_idx = i
                            break

    if existing_all and mode != "replace":
        # Get existing names
        existing_names = []
        if isinstance(existing_all.value, (cst.List, cst.Tuple)):
            for elem in existing_all.value.elements:
                if isinstance(elem.value, cst.SimpleString):
                    existing_names.append(elem.value.value.strip("\"'"))

        if mode == "append":
            names = existing_names + [n for n in names if n not in existing_names]
        elif mode == "prepend":
            names = [n for n in names if n not in existing_names] + existing_names

    # Build new __all__ node
    name_strings = [f'"{n}"' for n in names]
    all_value = f"[{', '.join(name_strings)}]"

    new_all = cst.SimpleStatementLine(
        body=[
            cst.Assign(
                targets=[cst.AssignTarget(target=cst.Name(value="__all__"))],
                value=cst.parse_expression(all_value),
            )
        ]
    )

    if existing_all_idx is not None:
        # Replace existing
        new_body = list(tree.body)
        new_body[existing_all_idx] = new_all
        new_tree = tree.with_changes(body=new_body)
    else:
        # Insert new - find position after imports and before first class/function
        insert_idx = 0
        for i, node in enumerate(tree.body):
            if isinstance(node, (cst.Import, cst.ImportFrom)):
                insert_idx = i + 1
            elif isinstance(node, cst.SimpleStatementLine):
                if node.body and isinstance(node.body[0], (cst.Import, cst.ImportFrom)):
                    insert_idx = i + 1
                else:
                    break
            else:
                break

        new_body = list(tree.body)
        new_body.insert(insert_idx, new_all)
        new_tree = tree.with_changes(body=new_body)

    # Write back
    new_source = new_tree.code
    module_path.write_text(new_source)

    return {
        "operation": "insert_dunder_all",
        "target": {
            "module": str(module_path),
        },
        "modified": True,
        "names": names,
    }


def insert_import(
    module_path: Path,
    name: Optional[str] = None,
    from_module: Optional[str] = None,
    alias: Optional[str] = None,
    check_duplicate: bool = True,
) -> dict[str, Any]:
    """Insert an import statement."""
    source = module_path.read_text()

    # Check for duplicate
    if check_duplicate:
        tree = cst.parse_module(source)
        if _import_exists(tree, name, from_module, alias):
            return {
                "operation": "insert_import",
                "target": {
                    "module": str(module_path),
                    "import": _format_import_str(name, from_module, alias),
                },
                "modified": False,
                "message": "Import already exists",
            }

    # Generate import node
    import_node = generate_import_node(
        name=name,
        from_module=from_module,
        alias=alias,
    )

    # Wrap in SimpleStatementLine
    stmt = cst.SimpleStatementLine(body=[import_node])

    # Create transformer
    transformer = InsertTransformer(
        insert_type="import",
        node_to_insert=stmt,
    )

    # Parse and transform
    tree = cst.parse_module(source)
    new_tree = tree.visit(transformer)

    # Write back
    new_source = new_tree.code
    module_path.write_text(new_source)

    return {
        "operation": "insert_import",
        "target": {
            "module": str(module_path),
            "import": _format_import_str(name, from_module, alias),
        },
        "modified": True,
        "location": {"position": transformer.insert_position},
    }


def _import_exists(
    tree: cst.Module,
    name: Optional[str],
    from_module: Optional[str],
    alias: Optional[str],
) -> bool:
    """Check if an import already exists in the module."""
    for node in tree.body:
        if isinstance(node, cst.SimpleStatementLine):
            for stmt in node.body:
                if isinstance(stmt, cst.Import):
                    for alias_node in stmt.names:
                        if _match_import_alias(alias_node, name, alias):
                            return True
                elif isinstance(stmt, cst.ImportFrom):
                    if from_module and _match_import_from(stmt, from_module, name, alias):
                        return True
        elif isinstance(node, cst.Import):
            for alias_node in node.names:
                if _match_import_alias(alias_node, name, alias):
                    return True
        elif isinstance(node, cst.ImportFrom):
            if from_module and _match_import_from(node, from_module, name, alias):
                return True
    return False


def _match_import_alias(
    alias_node: cst.ImportAlias,
    name: Optional[str],
    alias: Optional[str],
) -> bool:
    "Check if import alias matches."
    node_name = _get_alias_name(alias_node.name)
    if node_name != name:
        return False
    if alias:
        if alias_node.asname is None:
            return False
        if isinstance(alias_node.asname.name, cst.Name):
            return alias_node.asname.name.value == alias
        return False
    return alias_node.asname is None


def _match_import_from(
    node: cst.ImportFrom,
    from_module: str,
    name: Optional[str],
    alias: Optional[str],
) -> bool:
    "Check if from import matches."
    if node.module is None:
        return False
    node_module = _get_alias_name(node.module)
    if node_module != from_module:
        return False
    if name == "*":
        return isinstance(node.names, cst.ImportStar)
    if isinstance(node.names, cst.ImportStar):
        return False
    for alias_node in node.names:
        if isinstance(alias_node, cst.ImportAlias):
            if _match_import_alias(alias_node, name, alias):
                return True
    return False


def _get_alias_name(node: cst.CSTNode) -> str:
    """Get name from import alias node."""
    if isinstance(node, cst.Name):
        return node.value
    elif isinstance(node, cst.Attribute):
        return f"{_get_alias_name(node.value)}.{node.attr.value}"
    return ""


def _format_import_str(
    name: Optional[str],
    from_module: Optional[str],
    alias: Optional[str],
) -> str:
    """Format import as string."""
    if from_module:
        result = f"from {from_module} import {name or '*'}"
    else:
        result = f"import {name}"
    if alias:
        result += f" as {alias}"
    return result
