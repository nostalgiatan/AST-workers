"""Import statement generation using libcst."""

from typing import Optional, Union, Tuple, List

import libcst as cst


def _parse_module(module: str) -> tuple[Union[cst.Attribute, cst.Name, None], list[cst.Dot]]:
    """Parse module string to module node and relative dots.

    Returns:
        Tuple of (module_node, relative_dots)
        - module_node: Attribute or Name node for the module path (None if only dots)
        - relative_dots: List of Dot nodes for relative import level

    Examples:
        "os" -> (Name("os"), [])
        "os.path" -> (Attribute(Name("os"), "path"), [])
        ".module" -> (Name("module"), [Dot()])
        "..db.storage" -> (Attribute(Name("db"), "storage"), [Dot(), Dot()])
        "..." -> (None, [Dot(), Dot(), Dot()])
    """
    # Count leading dots for relative import
    leading_dots = 0
    for char in module:
        if char == ".":
            leading_dots += 1
        else:
            break

    # Create the relative dots
    relative_dots = [cst.Dot() for _ in range(leading_dots)]

    # Get the actual module path after leading dots
    module_path = module[leading_dots:]

    if not module_path:
        # Only dots, no module path (e.g., "from .. import something")
        return None, relative_dots

    # Parse the module path
    parts = module_path.split(".")
    if len(parts) == 1:
        return cst.Name(value=parts[0]), relative_dots

    # Build nested Attribute: a.b.c -> Attribute(Attribute(Name('a'), Name('b')), Name('c'))
    result: Union[cst.Attribute, cst.Name] = cst.Name(value=parts[0])
    for part in parts[1:]:
        result = cst.Attribute(value=result, attr=cst.Name(value=part))
    return result, relative_dots


def generate_import_node(
    name: Optional[str] = None,
    from_module: Optional[str] = None,
    alias: Optional[str] = None,
) -> cst.Import | cst.ImportFrom:
    """Generate a libcst import node.

    Args:
        name: Import name (for 'import X' or 'from Y import X')
              Can be comma-separated for multiple names: "Dict, List"
        from_module: Module to import from (for 'from Y import X')
        alias: Import alias (for 'import X as Y' or 'from M import X as Y')
               Note: alias only works with single name imports

    Returns:
        libcst.Import or libcst.ImportFrom node
    """
    if from_module:
        # from X import Y
        module_node, relative_dots = _parse_module(from_module)
        if name == "*" or name is None:
            # from X import *
            return cst.ImportFrom(
                module=module_node,
                names=cst.ImportStar(),
                relative=relative_dots,
            )
        else:
            # Parse multiple names: "Dict, List" or "Dict as D, List"
            names_list = _parse_import_names(name)
            import_aliases: list[cst.ImportAlias] = []
            for n, a in names_list:
                import_aliases.append(
                    cst.ImportAlias(
                        name=cst.Name(value=n),
                        asname=cst.AsName(name=cst.Name(value=a)) if a else None,
                    )
                )
            return cst.ImportFrom(
                module=module_node,
                names=import_aliases,
                relative=relative_dots,
            )
    else:
        # import X [as Y]
        names_list = _parse_import_names(name or "")
        import_aliases2: list[cst.ImportAlias] = []
        for n, a in names_list:
            # For absolute imports with dots, parse the module
            module_node, _ = _parse_module(n)
            import_aliases2.append(
                cst.ImportAlias(
                    name=module_node if isinstance(module_node, cst.Attribute) else cst.Name(value=n),
                    asname=cst.AsName(name=cst.Name(value=a)) if a else None,
                )
            )
        return cst.Import(names=import_aliases2)


def _parse_import_names(name_str: str) -> list[tuple[str, Optional[str]]]:
    """Parse import names string into list of (name, alias) tuples.

    Examples:
        "Dict" -> [("Dict", None)]
        "Dict, List" -> [("Dict", None), ("List", None)]
        "Dict as D, List as L" -> [("Dict", "D"), ("List", "L")]
    """
    if not name_str:
        return []

    result: list[tuple[str, str | None]] = []
    parts = name_str.split(",")

    for part in parts:
        part = part.strip()
        if " as " in part:
            name, alias = part.split(" as ")
            result.append((name.strip(), alias.strip()))
        else:
            result.append((part, None))

    return result


def generate_import(
    name: Optional[str] = None,
    from_module: Optional[str] = None,
    alias: Optional[str] = None,
) -> str:
    """Generate import statement as string.

    Args:
        name: Import name
        from_module: Module to import from
        alias: Import alias

    Returns:
        Import statement string
    """
    node = generate_import_node(name=name, from_module=from_module, alias=alias)
    # Wrap import in SimpleStatementLine for Module.body
    stmt = cst.SimpleStatementLine(body=[node])
    return cst.Module(body=[stmt]).code.strip()


def parse_import_string(import_str: str) -> dict:
    """Parse an import statement string into components.

    Args:
        import_str: Import statement like 'from X import Y as Z'

    Returns:
        dict with keys: type, module, name, alias
    """
    import_str = import_str.strip()

    # Remove 'import' and parse
    if import_str.startswith("from "):
        # from X import Y [as Z]
        match_import = import_str[5:]  # after 'from '
        parts = match_import.split(" import ")
        if len(parts) == 2:
            module = parts[0].strip()
            name_part = parts[1].strip()

            # Handle alias
            if " as " in name_part:
                name, alias = name_part.split(" as ")
                return {
                    "type": "from",
                    "module": module,
                    "name": name.strip(),
                    "alias": alias.strip(),
                }
            else:
                return {
                    "type": "from",
                    "module": module,
                    "name": name_part,
                    "alias": None,
                }
    elif import_str.startswith("import "):
        # import X [as Y]
        name_part = import_str[7:].strip()  # after 'import '

        if " as " in name_part:
            name, alias = name_part.split(" as ")
            return {
                "type": "import",
                "module": None,
                "name": name.strip(),
                "alias": alias.strip(),
            }
        else:
            return {
                "type": "import",
                "module": None,
                "name": name_part,
                "alias": None,
            }

    return {"type": "unknown", "module": None, "name": None, "alias": None}
