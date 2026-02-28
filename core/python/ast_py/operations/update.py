"""Update operations using libcst for AST-level code manipulation."""

from pathlib import Path
from typing import Any, Optional, Sequence

import libcst as cst

from ..generator.function import _build_parameters
from ..parser.params import ParamKind, parse_params


class UpdateFunctionTransformer(cst.CSTTransformer):
    """CST Transformer for updating function definitions."""

    def __init__(
        self,
        function_name: str,
        class_name: Optional[str] = None,
        new_body: Optional[str] = None,
        params: Optional[str] = None,  # Complete replacement of parameters
        add_params: Optional[str] = None,
        remove_params: Optional[list[str]] = None,
        new_return_type: Optional[str] = None,
        add_decorators: Optional[list[str]] = None,
        remove_decorators: Optional[list[str]] = None,
        new_docstring: Optional[str] = None,
    ):
        self.function_name = function_name
        self.class_name = class_name
        self.new_body = new_body
        self.params = params
        self.add_params = add_params
        self.remove_params = remove_params or []
        self.new_return_type = new_return_type
        self.add_decorators = add_decorators or []
        self.remove_decorators = remove_decorators or []
        self.new_docstring = new_docstring
        self.found = False
        self.updated = False
        self.in_target_class = False

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        if self.class_name and node.name.value == self.class_name:
            self.in_target_class = True
        return True

    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
        if self.class_name and original_node.name.value == self.class_name:
            self.in_target_class = False
        return updated_node

    def leave_FunctionDef(
        self,
        original_node: cst.FunctionDef,
        updated_node: cst.FunctionDef,
    ) -> cst.FunctionDef:
        if original_node.name.value != self.function_name:
            return updated_node
        if self.class_name and (not self.in_target_class):
            return updated_node
        self.found = True
        changes: dict[str, Any] = {}
        if self.new_body is not None:
            changes["body"] = self._build_new_body(self.new_body)
            self.updated = True
        if self.params is not None:
            # Complete replacement of parameters
            parsed_params = parse_params(self.params)
            new_params = _build_parameters(parsed_params)
            changes["params"] = new_params
            self.updated = True
        elif self.add_params or self.remove_params:
            new_params = self._update_parameters(original_node.params)
            changes["params"] = new_params
            self.updated = True
        if self.new_return_type is not None:
            if self.new_return_type == "":
                changes["returns"] = None
            else:
                changes["returns"] = cst.Annotation(annotation=cst.parse_expression(self.new_return_type))
            self.updated = True
        if self.add_decorators or self.remove_decorators:
            new_decorators = self._update_decorators(list(original_node.decorators))
            changes["decorators"] = new_decorators
            self.updated = True
        if self.new_docstring is not None:
            changes["body"] = self._update_docstring(updated_node.body)
            self.updated = True
        if changes:
            return updated_node.with_changes(**changes)
        return updated_node

    def _build_new_body(self, body_str: str) -> cst.BaseSuite:
        """Build function body from string or structured list.

        Supports two formats:
        1. Simple string - treated as single-line body
        2. Structured list - list of strings/tuples for multi-line:
           - str: newline at base indent
           - tuple: one level deeper indent for each item
           - nested tuples: multiple levels of indent

        Example:
            body=[
                "result = {",
                ("valid: True,", "error: None"),  # indented
                "}",
                "try:",
                ("do_something()",),  # indented
                "except Error:",
                (("handle_error()",),),  # double indented
            ]
        """
        # Handle structured list format
        if body_str.startswith("[") and body_str.endswith("]"):
            return self._build_structured_body(body_str)

        # Simple string format - use existing logic
        import re

        if not body_str.strip():
            return cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])])

        # Detect multi-line structures (if, for, while, try, with, class, def, match)
        multi_line_keywords = re.compile(
            r"^\s*(if|for|while|try|with|class|def|match|async\s+(def|for|with))\b",
            re.MULTILINE,
        )
        has_multi_line = bool(multi_line_keywords.search(body_str))

        if has_multi_line:
            # For multi-line structures, use ast module to properly handle indentation
            # Try different indentation strategies
            for strategy in ["ast_unparse", "dedent", "strip", "asis"]:
                try:
                    result = self._try_parse_with_strategy(body_str, strategy)
                    if result:
                        return result
                except Exception:
                    continue

        # Single-line or fallback: simple line-by-line parsing
        print("DEBUG: Using line-by-line fallback")
        return self._parse_simple_body(body_str)

    def _build_structured_body(self, body_str: str) -> cst.BaseSuite:
        try:
            body_list = eval(body_str)
            if isinstance(body_list, list):
                return self._parse_structured_list(body_list)
        except Exception:
            pass
        import re

        multi_line_keywords = re.compile("^\\s*(if|for|while|try|with|class|def|match|async)\\b", re.MULTILINE)
        has_multi_line = bool(multi_line_keywords.search(body_str))
        if has_multi_line:
            for strategy in ["dedent", "strip", "asis"]:
                try:
                    result = self._try_parse_with_strategy(body_str, strategy)
                    if result:
                        return result
                except Exception:
                    pass
        return self._parse_simple_body(body_str)

    def _parse_structured_list(self, body_list: list) -> cst.BaseSuite:
        import libcst as cst

        lines = []
        for item in body_list:
            if isinstance(item, str):
                lines.append("    " + item)
            elif isinstance(item, tuple):
                for sub in item:
                    if isinstance(sub, str):
                        lines.append("        " + sub)
                    elif isinstance(sub, tuple):
                        for sub2 in sub:
                            if isinstance(sub2, str):
                                lines.append("            " + sub2)
        indented = "\\n".join(lines)
        dummy_code = f"def _dummy_():\\n{indented}"
        module = cst.parse_module(dummy_code)
        for node in module.body:
            if isinstance(node, cst.FunctionDef) and node.name.value == "_dummy_":
                return node.body
        return cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])])

    def _try_parse_with_strategy(self, body_str: str, strategy: str) -> cst.BaseSuite | None:
        import ast
        import textwrap

        if strategy == "dedent":
            normalized = textwrap.dedent(body_str)
        elif strategy == "strip":
            lines = body_str.split("\n")
            normalized = "\n".join((line.lstrip() for line in lines))
        elif strategy == "ast_unparse":
            normalized = None
            try:
                lines = body_str.split("\n")
                min_indent = float("inf")
                for line in lines:
                    if line.strip():
                        indent = len(line) - len(line.lstrip())
                        min_indent = min(min_indent, indent)
                if min_indent == float("inf"):
                    min_indent = 0
                for scale in [1, 0.5, 2]:
                    try:
                        normalized_lines = []
                        for line in lines:
                            if line.strip():
                                orig_indent = len(line) - len(line.lstrip())
                                relative_indent = orig_indent - min_indent
                                new_indent = int(relative_indent * scale)
                                normalized_lines.append(" " * new_indent + line.lstrip())
                            else:
                                normalized_lines.append("")
                        func_lines = ["    " + line if line.strip() else line for line in normalized_lines]
                        dummy_code = "def _dummy_():\n" + "\n".join(func_lines)
                        tree = ast.parse(dummy_code)
                        func_node = tree.body[0]
                        statements = []
                        if isinstance(func_node, ast.FunctionDef):
                            for stmt in func_node.body:
                                stmt_code = ast.unparse(stmt)
                                statements.append(stmt_code)
                            normalized = "\n".join(statements)
                        break
                    except SyntaxError:
                        continue
            except Exception:
                pass
            if normalized is None:
                return None
        else:
            normalized = body_str
        assert normalized is not None
        lines = normalized.split("\n")
        indented = "\n".join(("    " + line if line.strip() else line for line in lines))
        func_code = f"def _dummy_():\n{indented}"
        module = cst.parse_module(func_code)
        for node in module.body:
            if isinstance(node, cst.FunctionDef) and node.name.value == "_dummy_":
                return node.body
        return None

    def _parse_simple_body(self, body_str: str) -> cst.BaseSuite:
        """Parse simple single-line body statements."""

        # Fallback: parse line by line (for simple cases)
        lines = body_str.strip().split("\n")
        statements = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                parsed = cst.parse_statement(line)
                statements.append(parsed)
            except Exception:
                # Try as expression
                try:
                    expr = cst.parse_expression(line)
                    statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=expr)]))
                except Exception:
                    pass

        if not statements:
            statements = [cst.SimpleStatementLine(body=[cst.Pass()])]

        return cst.IndentedBlock(body=statements)

    def _update_parameters(self, old_params: cst.Parameters) -> cst.Parameters:
        """Update parameters by adding/removing."""
        # Get existing param names
        existing_names = set()

        # Collect all existing parameters
        posonly_params = list(old_params.posonly_params or [])
        params = list(old_params.params or [])
        kwonly_params = list(old_params.kwonly_params or [])
        star_arg: cst.Param | cst.ParamStar | cst.MaybeSentinel = old_params.star_arg
        star_kwarg: cst.Param | None = old_params.star_kwarg

        for p in posonly_params:
            if isinstance(p, cst.Param):
                existing_names.add(p.name.value)
        for p in params:
            if isinstance(p, cst.Param):
                existing_names.add(p.name.value)
        for p in kwonly_params:
            if isinstance(p, cst.Param):
                existing_names.add(p.name.value)
        if star_arg and isinstance(star_arg, cst.Param):
            existing_names.add(star_arg.name.value)
        if star_kwarg and isinstance(star_kwarg, cst.Param):
            existing_names.add(star_kwarg.name.value)

        # Remove parameters
        new_posonly = [
            p for p in posonly_params if not isinstance(p, cst.Param) or p.name.value not in self.remove_params
        ]
        new_params = [p for p in params if not isinstance(p, cst.Param) or p.name.value not in self.remove_params]
        new_kwonly = [
            p for p in kwonly_params if not isinstance(p, cst.Param) or p.name.value not in self.remove_params
        ]

        if star_arg and isinstance(star_arg, cst.Param) and star_arg.name.value in self.remove_params:
            star_arg = cst.MaybeSentinel.DEFAULT
        if star_kwarg and isinstance(star_kwarg, cst.Param) and star_kwarg.name.value in self.remove_params:
            star_kwarg = None

        # Add new parameters
        if self.add_params:
            new_param_infos = parse_params(self.add_params)
            for pi in new_param_infos:
                if pi.name in existing_names:
                    continue  # Skip duplicates

                param_node = cst.Param(
                    name=cst.Name(value=pi.name),
                    annotation=(
                        cst.Annotation(annotation=cst.parse_expression(pi.annotation)) if pi.annotation else None
                    ),
                    default=cst.parse_expression(pi.default) if pi.default else None,
                )

                # Add to appropriate position based on kind
                if pi.kind == ParamKind.POSITIONAL_OR_KEYWORD:
                    new_params.append(param_node)
                elif pi.kind == ParamKind.KEYWORD_ONLY:
                    new_kwonly.append(param_node)
                elif pi.kind == ParamKind.VAR_POSITIONAL:
                    star_arg = param_node
                elif pi.kind == ParamKind.VAR_KEYWORD:
                    star_kwarg = param_node

        return cst.Parameters(
            posonly_params=new_posonly,
            params=new_params,
            star_arg=star_arg,
            kwonly_params=new_kwonly,
            star_kwarg=star_kwarg,
        )

    def _update_decorators(self, old_decorators: list[cst.Decorator]) -> list[cst.Decorator]:
        """Update decorators by adding/removing."""
        new_decorators = []
        existing_names = set()

        # Keep existing decorators that aren't being removed
        for dec in old_decorators:
            dec_name = self._get_decorator_name(dec)
            existing_names.add(dec_name)

            if dec_name not in self.remove_decorators:
                new_decorators.append(dec)

        # Add new decorators
        for dec_str in self.add_decorators:
            dec_str = dec_str.strip()
            if dec_str.startswith("@"):
                dec_str = dec_str[1:]

            # Check if already exists
            if dec_str in existing_names:
                continue

            try:
                dec_expr = cst.parse_expression(dec_str)
                new_decorators.append(cst.Decorator(decorator=dec_expr))
            except Exception:
                new_decorators.append(cst.Decorator(decorator=cst.Name(value=dec_str)))

        return new_decorators

    def _get_decorator_name(self, dec: cst.Decorator) -> str:
        """Get the name of a decorator."""
        if isinstance(dec.decorator, cst.Name):
            return dec.decorator.value
        elif isinstance(dec.decorator, cst.Call):
            if isinstance(dec.decorator.func, cst.Name):
                return dec.decorator.func.value
            elif isinstance(dec.decorator.func, cst.Attribute):
                return self._get_expr_name(dec.decorator.func)
        elif isinstance(dec.decorator, cst.Attribute):
            return self._get_expr_name(dec.decorator)
        return ""

    def _get_expr_name(self, node: cst.CSTNode) -> str:
        """Get name from expression node."""
        if isinstance(node, cst.Name):
            return node.value
        elif isinstance(node, cst.Attribute):
            return f"{self._get_expr_name(node.value)}.{node.attr.value}"
        return ""

    def _update_docstring(self, old_body: cst.BaseSuite) -> cst.BaseSuite:
        """Update docstring in function body."""
        new_statements: list[cst.BaseStatement] = []
        docstring_inserted = False

        # Handle both IndentedBlock and SimpleBlockSuite
        body_stmts: Sequence[cst.BaseStatement] = []
        if isinstance(old_body, cst.IndentedBlock):
            body_stmts = old_body.body

        for stmt in body_stmts:
            # Check if this is a docstring
            is_docstring = False
            if isinstance(stmt, cst.SimpleStatementLine):
                if len(stmt.body) == 1 and isinstance(stmt.body[0], cst.Expr):
                    if isinstance(stmt.body[0].value, cst.SimpleString):
                        is_docstring = True

            if is_docstring:
                if self.new_docstring:
                    # Replace docstring
                    new_doc = cst.SimpleStatementLine(
                        body=[cst.Expr(value=cst.SimpleString(value=f'"""{self.new_docstring}"""'))]
                    )
                    new_statements.append(new_doc)
                    docstring_inserted = True
                # If new_docstring is empty string, remove docstring
            else:
                new_statements.append(stmt)

        # Add docstring at beginning if not inserted yet
        if self.new_docstring and not docstring_inserted:
            new_doc = cst.SimpleStatementLine(
                body=[cst.Expr(value=cst.SimpleString(value=f'"""{self.new_docstring}"""'))]
            )
            new_statements.insert(0, new_doc)

        return cst.IndentedBlock(body=new_statements)


def update_function(
    module_path: Path,
    function_name: str,
    class_name: Optional[str] = None,
    new_body: Optional[str] = None,
    params: Optional[str] = None,
    add_params: Optional[str] = None,
    remove_params: Optional[list[str]] = None,
    new_return_type: Optional[str] = None,
    add_decorators: Optional[list[str]] = None,
    remove_decorators: Optional[list[str]] = None,
    new_docstring: Optional[str] = None,
) -> dict[str, Any]:
    """Update a function definition.

    Args:
        module_path: Path to the Python module
        function_name: Name of the function to update
        class_name: Target class name (for methods)
        new_body: New function body
        params: Complete replacement of parameters (same format as insert-function)
        add_params: Parameters to add (same format as insert-function)
        remove_params: Parameter names to remove
        new_return_type: New return type (empty string to remove)
        add_decorators: Decorators to add
        remove_decorators: Decorator names to remove
        new_docstring: New docstring

    Returns:
        Result dict with operation details
    """
    source = module_path.read_text()

    # Create transformer
    transformer = UpdateFunctionTransformer(
        function_name=function_name,
        class_name=class_name,
        new_body=new_body,
        params=params,
        add_params=add_params,
        remove_params=remove_params,
        new_return_type=new_return_type,
        add_decorators=add_decorators,
        remove_decorators=remove_decorators,
        new_docstring=new_docstring,
    )

    # Parse and transform
    tree = cst.parse_module(source)
    new_tree = tree.visit(transformer)

    if not transformer.found:
        raise ValueError(f"Function '{function_name}' not found" + (f" in class '{class_name}'" if class_name else ""))

    if not transformer.updated:
        return {
            "operation": "update_function",
            "target": {
                "module": str(module_path),
                "class": class_name,
                "function": function_name,
            },
            "modified": False,
            "message": "No changes specified",
        }

    # Write back
    new_source = new_tree.code
    module_path.write_text(new_source)

    return {
        "operation": "update_function",
        "target": {
            "module": str(module_path),
            "class": class_name,
            "function": function_name,
        },
        "modified": True,
    }
