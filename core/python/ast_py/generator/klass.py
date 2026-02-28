"""Class code generation using libcst."""

from typing import Optional, Sequence

import libcst as cst

from .function import generate_function_node


def generate_class_node(
    name: str,
    bases: Optional[list[str]] = None,
    decorators: Optional[list[str]] = None,
    body: Optional[Sequence[cst.BaseStatement]] = None,
) -> cst.ClassDef:
    """Generate a libcst ClassDef node.

    Args:
        name: Class name
        bases: List of base class names/expressions
        decorators: List of decorator strings
        body: List of class body nodes (methods, assignments, etc.)

    Returns:
        libcst.ClassDef node
    """
    # Parse decorators
    decorator_nodes = []
    if decorators:
        for dec in decorators:
            dec = dec.strip()
            if dec.startswith("@"):
                dec = dec[1:]
            try:
                dec_expr = cst.parse_expression(dec)
                decorator_nodes.append(cst.Decorator(decorator=dec_expr))
            except Exception:
                decorator_nodes.append(cst.Decorator(decorator=cst.Name(value=dec)))

    # Build arguments for bases
    arg_nodes = []
    if bases:
        for base in bases:
            base = base.strip()
            try:
                base_expr = cst.parse_expression(base)
                arg_nodes.append(cst.Arg(value=base_expr))
            except Exception:
                arg_nodes.append(cst.Arg(value=cst.Name(value=base)))

    # Build body
    if body is None:
        body = [cst.SimpleStatementLine(body=[cst.Pass()])]

    body_node = cst.IndentedBlock(body=body)

    return cst.ClassDef(
        name=cst.Name(value=name),
        bases=arg_nodes,
        body=body_node,
        decorators=decorator_nodes if decorator_nodes else [],
    )


def generate_class(
    name: str,
    bases: Optional[list[str]] = None,
    decorators: Optional[list[str]] = None,
    methods: Optional[list[dict]] = None,
    class_vars: Optional[list[dict]] = None,
    docstring: Optional[str] = None,
    indent: str = "",
) -> str:
    """Generate class code as a string.

    Args:
        name: Class name
        bases: List of base class names
        decorators: List of decorator strings
        methods: List of method definitions (dict with name, params, body, etc.)
        class_vars: List of class variable definitions
        docstring: Class docstring
        indent: Base indentation

    Returns:
        Formatted class code string
    """
    body_nodes: list[cst.BaseStatement] = []

    # Add docstring
    if docstring:
        body_nodes.append(cst.SimpleStatementLine(body=[cst.Expr(value=cst.SimpleString(value=f'"""{docstring}"""'))]))

    # Add class variables
    if class_vars:
        for var in class_vars:
            var_name = var.get("name", "")
            var_value = var.get("value", "None")
            var_annotation = var.get("annotation")

            if var_annotation:
                ann_assign = cst.AnnAssign(
                    target=cst.Name(value=var_name),
                    annotation=cst.Annotation(annotation=cst.parse_expression(var_annotation)),
                    value=cst.parse_expression(var_value),
                )
                body_nodes.append(cst.SimpleStatementLine(body=[ann_assign]))
            else:
                assign = cst.Assign(
                    targets=[cst.AssignTarget(target=cst.Name(value=var_name))],
                    value=cst.parse_expression(var_value),
                )
                body_nodes.append(cst.SimpleStatementLine(body=[assign]))

    # Add methods
    if methods:
        for method in methods:
            method_node = generate_function_node(
                name=method.get("name", ""),
                params=method.get("params", []),
                body=method.get("body", "pass"),
                return_type=method.get("return_type"),
                decorators=method.get("decorators"),
                is_async=method.get("is_async", False),
                docstring=method.get("docstring"),
            )
            body_nodes.append(method_node)

    # If no body, add pass
    if not body_nodes:
        body_nodes = [cst.SimpleStatementLine(body=[cst.Pass()])]

    node = generate_class_node(
        name=name,
        bases=bases,
        decorators=decorators,
        body=body_nodes,
    )

    code = cst.Module(body=[node]).code

    # Apply indentation
    lines = code.split("\n")
    indented_lines = []
    for i, line in enumerate(lines):
        if i == 0 or not line.strip():
            indented_lines.append(indent + line if line.strip() else line)
        else:
            indented_lines.append(indent + line)

    return "\n".join(indented_lines)
