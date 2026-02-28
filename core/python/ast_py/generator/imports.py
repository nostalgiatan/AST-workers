"""Import statement generation using libcst."""

from typing import Optional, Union

import libcst as cst


def _parse_module(module: str) -> Union[cst.Attribute, cst.Name]:
    """Parse module string to Attribute or Name node."""
    parts = module.split(".")
    if len(parts) == 1:
        return cst.Name(value=parts[0])

    # Build nested Attribute: a.b.c -> Attribute(Attribute(Name('a'), Name('b')), Name('c'))
    result: Union[cst.Attribute, cst.Name] = cst.Name(value=parts[0])
    for part in parts[1:]:
        result = cst.Attribute(value=result, attr=cst.Name(value=part))
    return result


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
        module_node = _parse_module(from_module)
        if name == "*" or name is None:
            # from X import *
            return cst.ImportFrom(
                module=module_node,
                names=cst.ImportStar(),
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
            )
    else:
        # import X [as Y]
        names_list = _parse_import_names(name or "")
        import_aliases2: list[cst.ImportAlias] = []
        for n, a in names_list:
            import_aliases2.append(
                cst.ImportAlias(
                    name=_parse_module(n) if "." in n else cst.Name(value=n),
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
