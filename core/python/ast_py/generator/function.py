"""Function code generation using libcst.

Provides both CST node generation (for precise manipulation)
and string generation (for simple insertion).
"""

from typing import Any, Optional, Sequence

import libcst as cst

from ..parser.params import ParamInfo, ParamKind


def generate_function_node(
    name: str,
    params: list[ParamInfo],
    body: str | list[str | tuple] = "pass",
    return_type: Optional[str] = None,
    decorators: Optional[list[str]] = None,
    is_async: bool = False,
    docstring: Optional[str] = None,
) -> cst.FunctionDef:
    """Generate a libcst FunctionDef node.

    Args:
        name: Function name
        params: List of parameter info
        body: Function body as string
        return_type: Return type annotation
        decorators: List of decorator strings (with or without @)
        is_async: Whether this is an async function
        docstring: Optional docstring

    Returns:
        libcst.FunctionDef node
    """
    # Parse decorators
    decorator_nodes = []
    if decorators:
        for dec in decorators:
            dec = dec.strip()
            if dec.startswith("@"):
                dec = dec[1:]
            # Parse decorator as expression
            try:
                dec_expr = cst.parse_expression(dec)
                decorator_nodes.append(cst.Decorator(decorator=dec_expr))
            except Exception:
                # Fallback: treat as simple name
                decorator_nodes.append(cst.Decorator(decorator=cst.Name(value=dec)))

    # Build parameters
    parameters = _build_parameters(params)

    # Build return annotation
    returns = None
    if return_type:
        returns = cst.Annotation(annotation=cst.parse_expression(return_type))

    # Build body - support both str and structured list format
    body_lines: Any
    if isinstance(body, list):
        # Structured format: list of strings/tuples
        body_lines = list(body)  # Make a copy
    else:
        # String format: split into lines
        body_lines = body.strip().split("\n") if body.strip() else ["pass"]

    if docstring:
        body_lines = [f'"""{docstring}"""'] + body_lines

    body_node = _build_body(body_lines, is_method=_is_method(params))

    # Build function def
    func = cst.FunctionDef(
        name=cst.Name(value=name),
        params=parameters,
        body=body_node,
        returns=returns,
        asynchronous=cst.Asynchronous() if is_async else None,
        decorators=decorator_nodes,
    )

    return func


def generate_function(
    name: str,
    params: list[ParamInfo],
    body: str = "pass",
    return_type: Optional[str] = None,
    decorators: Optional[list[str]] = None,
    is_async: bool = False,
    docstring: Optional[str] = None,
    indent: str = "",
) -> str:
    """Generate function code as a string.

    Args:
        name: Function name
        params: List of parameter info
        body: Function body as string
        return_type: Return type annotation
        decorators: List of decorator strings
        is_async: Whether this is an async function
        docstring: Optional docstring
        indent: Base indentation for the function

    Returns:
        Formatted function code string
    """
    node = generate_function_node(
        name=name,
        params=params,
        body=body,
        return_type=return_type,
        decorators=decorators,
        is_async=is_async,
        docstring=docstring,
    )

    # Generate code and apply indentation
    code = cst.Module(body=[node]).code

    # Apply indentation to each line
    lines = code.split("\n")
    indented_lines = []
    for i, line in enumerate(lines):
        if i == 0 or not line.strip():
            indented_lines.append(indent + line if line.strip() else line)
        else:
            # libcst adds its own indentation, we need to adjust
            indented_lines.append(indent + line)

    return "\n".join(indented_lines)


def _build_parameters(params: list[ParamInfo]) -> cst.Parameters:
    posonly_params: list[cst.Param] = []
    pos_or_kw_params: list[cst.Param] = []
    vararg: cst.Param | None = None
    kwonly_params: list[cst.Param] = []
    kwarg: cst.Param | None = None
    need_star_separator = False
    for p in params:
        param = _build_param(p)
        if p.kind == ParamKind.POSITIONAL_ONLY:
            posonly_params.append(param)
        elif p.kind == ParamKind.POSITIONAL_OR_KEYWORD:
            pos_or_kw_params.append(param)
        elif p.kind == ParamKind.VAR_POSITIONAL:
            vararg = param
        elif p.kind == ParamKind.KEYWORD_ONLY:
            kwonly_params.append(param)
            need_star_separator = True
        elif p.kind == ParamKind.VAR_KEYWORD:
            kwarg = param
    star_arg: cst.Param | cst.ParamStar | cst.MaybeSentinel = vararg or cst.MaybeSentinel.DEFAULT
    if isinstance(star_arg, cst.MaybeSentinel) and need_star_separator and kwonly_params:
        star_arg = cst.ParamStar()
    return cst.Parameters(
        params=pos_or_kw_params,
        star_arg=star_arg,
        kwonly_params=kwonly_params,
        star_kwarg=kwarg,
    )


def _build_param(p: ParamInfo) -> cst.Param:
    """Build a single libcst Param."""
    annotation = None
    if p.annotation:
        annotation = cst.Annotation(annotation=cst.parse_expression(p.annotation))

    default = None
    if p.default:
        default = cst.parse_expression(p.default)

    return cst.Param(
        name=cst.Name(value=p.name),
        annotation=annotation,
        default=default,
    )


def _build_body(body_lines: Sequence[str | tuple], is_method: bool = False) -> cst.BaseSuite:
    """Build function body from lines of code.

    Supports two formats:
    1. List of strings - each string is a line
    2. Structured format (list containing strings and/or tuples):
       - str: newline at base indent
       - tuple: one level deeper indent for each item
       - nested tuples: multiple levels of indent
    """
    # Check for structured format (contains tuples)
    has_tuples = any(isinstance(item, tuple) for item in body_lines)
    if has_tuples:
        return _build_structured_body_from_list(body_lines)

    # Join lines back together
    body_text = "\n".join(str(line) for line in body_lines)

    # Check for structured format as JSON string
    if body_text.strip().startswith("[") and body_text.strip().endswith("]"):
        return _build_structured_body(body_text)

    # If body is empty or just pass, use pass
    if not body_text.strip() or body_text.strip() == "pass":
        return cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])])

    # Try to parse the whole body as a module to get proper statements
    try:
        # Preserve relative indentation by adding base indent to each line
        lines = body_text.strip().split("\n")
        # Find minimum indentation (excluding empty lines)
        min_indent = -1
        for line in lines:
            if line.strip():  # non-empty line
                indent = len(line) - len(line.lstrip())
                if min_indent == -1 or indent < min_indent:
                    min_indent = indent

        # Remove common indentation and add 4 spaces
        indented_lines = []
        for line in lines:
            if line.strip():
                # Remove original indent and add 4 spaces
                if min_indent >= 0:
                    stripped = line[min_indent:]
                else:
                    stripped = line.lstrip()
                indented_lines.append("    " + stripped)
            else:
                indented_lines.append("")

        indented_body = "\n".join(indented_lines)
        dummy_func = f"def _dummy_():\n{indented_body}"
        module = cst.parse_module(dummy_func)

        # Extract the body from the dummy function
        for node in module.body:
            if isinstance(node, cst.FunctionDef) and node.name.value == "_dummy_":
                return node.body

        # Fallback: parse line by line
        return _parse_body_line_by_line(body_lines)
    except Exception:
        # Fallback: parse line by line
        return _parse_body_line_by_line(body_lines)


def _build_structured_body(body_text: str) -> cst.BaseSuite:
    """Build body from structured list format (JSON string)."""
    import ast

    try:
        body_list = ast.literal_eval(body_text.strip())
    except Exception:
        return cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])])

    if not isinstance(body_list, list):
        body_list = [body_list]

    return _build_structured_body_from_list(body_list)


def _build_structured_body_from_list(body_list: Sequence[Any]) -> cst.BaseSuite:
    """Build body from structured list format (already parsed list).

    Format:
    - str at level 0: no extra indent
    - tuple: each item gets +1 indent level
    - nested tuple: +N indent levels

    Example:
        [
            "result = {",
            ("valid: True,", "error: None"),  # indented
            "}",
            "try:",
            ("do_something()",),  # indented
            "except Error:",
            (("handle_error()",),),  # double indented
        ]
    """

    def build_lines(items: Sequence[Any], base_indent: int = 0) -> list[str]:
        """Recursively build lines with proper indentation."""
        lines = []
        for item in items:
            if isinstance(item, tuple):
                # Each item in tuple gets one more indent
                nested_indent = base_indent + 4
                for sub_item in item:
                    if isinstance(sub_item, tuple):
                        # Nested tuple = more indent
                        lines.extend(build_lines([sub_item], nested_indent))
                    else:
                        lines.append(" " * nested_indent + str(sub_item))
            else:
                lines.append(" " * base_indent + str(item))
        return lines

    lines = build_lines(list(body_list), base_indent=4)  # Start with 4 spaces for function body
    code = "def _dummy_():\n" + "\n".join(lines)

    try:
        module = cst.parse_module(code)
        for node in module.body:
            if isinstance(node, cst.FunctionDef) and node.name.value == "_dummy_":
                return node.body
    except Exception:
        pass

    return cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])])


def _parse_body_line_by_line(body_lines: Sequence[str | tuple]) -> cst.BaseSuite:
    """Parse body line by line as fallback."""
    statements: list[cst.BaseStatement] = []

    for item in body_lines:
        # Skip tuples in structured format - they should be handled by _build_structured_body_from_list
        if isinstance(item, tuple):
            continue
        line = item.strip() if isinstance(item, str) else str(item)
        if not line:
            continue

        # Handle common cases - wrap in SimpleStatementLine
        if line.startswith("return "):
            expr_str = line[7:]  # after 'return '
            statements.append(
                cst.SimpleStatementLine(body=[cst.Return(value=cst.parse_expression(expr_str) if expr_str else None)])
            )
        elif line == "return":
            statements.append(cst.SimpleStatementLine(body=[cst.Return()]))
        elif line.startswith("yield "):
            expr_str = line[6:]
            statements.append(
                cst.SimpleStatementLine(
                    body=[cst.Expr(value=cst.Yield(value=(cst.parse_expression(expr_str) if expr_str else None)))]
                )
            )
        elif line.startswith("raise "):
            expr_str = line[6:]
            statements.append(cst.SimpleStatementLine(body=[cst.Raise(exc=cst.parse_expression(expr_str))]))
        elif line == "pass":
            statements.append(cst.SimpleStatementLine(body=[cst.Pass()]))
        elif line.startswith('"""') or line.startswith("'''"):
            # Docstring
            statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.SimpleString(value=line))]))
        elif line.startswith("#"):
            # Comment - skip for now
            continue
        else:
            # Try to parse as a complete statement
            try:
                parsed = cst.parse_statement(line)
                statements.append(parsed)
            except Exception:
                # Fallback: treat as expression
                try:
                    expr_node = cst.parse_expression(line)
                    statements.append(cst.SimpleStatementLine(body=[cst.Expr(value=expr_node)]))
                except Exception:
                    # Last resort: use pass
                    statements.append(cst.SimpleStatementLine(body=[cst.Pass()]))

    if not statements:
        statements = [cst.SimpleStatementLine(body=[cst.Pass()])]

    return cst.IndentedBlock(body=statements)


def _is_method(params: list[ParamInfo]) -> bool:
    """Check if this looks like a method (has 'self' or 'cls' as first param)."""
    if not params:
        return False
    first = params[0]
    return first.name in ("self", "cls")
