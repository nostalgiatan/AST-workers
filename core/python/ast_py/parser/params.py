"""Parameter parsing for function signatures.

Supports:
- Positional parameters: x, x:int
- Default values: x=1, x:int=1
- *args: *args, *args:str
- **kwargs: **kwargs, **kwargs:dict
- Positional-only separator: /
- Keyword-only separator: *
"""

from dataclasses import dataclass
from enum import Enum, auto


class ParamKind(Enum):
    POSITIONAL_ONLY = auto()  # before /
    POSITIONAL_OR_KEYWORD = auto()  # normal
    VAR_POSITIONAL = auto()  # *args
    KEYWORD_ONLY = auto()  # after *
    VAR_KEYWORD = auto()  # **kwargs


@dataclass
class ParamInfo:
    name: str
    annotation: str | None = None
    default: str | None = None
    kind: ParamKind = ParamKind.POSITIONAL_OR_KEYWORD


def parse_params(params_str: str) -> list[ParamInfo]:
    """Parse a parameter string into structured data.

    Examples:
        "x:int, y:str='default'"
        -> [ParamInfo(name='x', annotation='int'),
            ParamInfo(name='y', annotation='str', default="'default'")]

        "a, /, b, *, c, **kwargs"
        -> [ParamInfo(name='a', kind=POSITIONAL_ONLY),
            ParamInfo(name='b', kind=POSITIONAL_OR_KEYWORD),
            ParamInfo(name='c', kind=KEYWORD_ONLY),
            ParamInfo(name='kwargs', kind=VAR_KEYWORD)]
    """
    if not params_str or not params_str.strip():
        return []

    # Split by comma, respecting brackets, quotes, etc.
    parts = _split_params(params_str)

    params: list[ParamInfo] = []
    seen_star = False  # seen * (keyword-only separator)
    seen_slash = False  # seen / (positional-only separator)

    for part in parts:
        part = part.strip()

        # Handle / separator (positional-only)
        if part == "/":
            if seen_slash:
                raise ValueError("Multiple '/' separators in parameters")
            seen_slash = True
            # Mark previous params as positional-only
            for p in params:
                if p.kind == ParamKind.POSITIONAL_OR_KEYWORD:
                    p.kind = ParamKind.POSITIONAL_ONLY
            continue

        # Handle * separator (keyword-only)
        if part == "*":
            if seen_star:
                raise ValueError("Multiple '*' separators in parameters")
            seen_star = True
            continue

        param = _parse_single_param(part)

        # Determine kind based on separators seen
        if param.name.startswith("**"):
            param.name = param.name[2:]
            param.kind = ParamKind.VAR_KEYWORD
        elif param.name.startswith("*"):
            param.name = param.name[1:]
            param.kind = ParamKind.VAR_POSITIONAL
            # After *args, following params are keyword-only
            seen_star = True
        elif seen_star:
            param.kind = ParamKind.KEYWORD_ONLY
        elif seen_slash:
            param.kind = ParamKind.POSITIONAL_OR_KEYWORD
        # else: keep default POSITIONAL_OR_KEYWORD

        params.append(param)

    return params


def _split_params(params_str: str) -> list[str]:
    """Split parameters by comma, respecting nested structures."""
    parts = []
    current = ""
    depth = 0
    in_string = False
    string_char = None

    i = 0
    while i < len(params_str):
        char = params_str[i]

        # Handle string literals
        if char in ('"', "'") and not in_string:
            in_string = True
            string_char = char
            current += char
        elif char == string_char and in_string:
            # Check for escape
            if i > 0 and params_str[i - 1] == "\\":
                current += char
            else:
                in_string = False
                string_char = None
                current += char
        # Handle brackets
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

        i += 1

    if current.strip():
        parts.append(current.strip())

    return parts


def _parse_single_param(param_str: str) -> ParamInfo:
    """Parse a single parameter like 'x:int=1' or '**kwargs'."""
    param = ParamInfo(name="")

    # Check for default value first (from rightmost = outside brackets)
    eq_pos = _find_default_equals(param_str)

    if eq_pos >= 0:
        default_part = param_str[eq_pos + 1 :].strip()
        param.default = default_part
        name_annot = param_str[:eq_pos].strip()
    else:
        name_annot = param_str.strip()

    # Check for type annotation
    colon_pos = _find_annotation_colon(name_annot)

    if colon_pos >= 0:
        param.name = name_annot[:colon_pos].strip()
        param.annotation = name_annot[colon_pos + 1 :].strip()
    else:
        param.name = name_annot.strip()

    return param


def _find_default_equals(s: str) -> int:
    """Find the = that separates name and default value.

    Must be outside brackets and not in a string.
    """
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


def _find_annotation_colon(s: str) -> int:
    """Find the : that separates name and annotation.

    Must be outside brackets and not in a string.
    Only returns the first such colon.
    """
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


def format_params(params: list[ParamInfo]) -> str:
    """Format params back to a string for code generation."""
    if not params:
        return ""

    parts = []
    need_slash = False
    need_star = False

    # First pass: determine if we need separators
    for p in params:
        if p.kind == ParamKind.POSITIONAL_ONLY:
            need_slash = True

    # Check if there are positional-or-keyword followed by keyword-only
    has_pos_or_key = False
    has_kw_only = False
    for p in params:
        if p.kind == ParamKind.POSITIONAL_OR_KEYWORD:
            has_pos_or_key = True
        elif p.kind == ParamKind.KEYWORD_ONLY:
            has_kw_only = True

    if has_kw_only and has_pos_or_key:
        need_star = True

    # Build parts
    positional_only_done = False

    for p in params:
        if p.kind == ParamKind.POSITIONAL_ONLY:
            parts.append(_format_single_param(p))
            positional_only_done = True
        elif p.kind == ParamKind.POSITIONAL_OR_KEYWORD:
            if need_slash and positional_only_done and "/" not in parts:
                parts.append("/")
            parts.append(_format_single_param(p))
        elif p.kind == ParamKind.VAR_POSITIONAL:
            p.name = "*" + p.name
            parts.append(_format_single_param(p))
        elif p.kind == ParamKind.KEYWORD_ONLY:
            # Insert * before first keyword-only if needed
            if need_star and "*" not in parts and not any("*" in part for part in parts):
                parts.append("*")
            parts.append(_format_single_param(p))
        elif p.kind == ParamKind.VAR_KEYWORD:
            p.name = "**" + p.name
            parts.append(_format_single_param(p))

    return ", ".join(parts)


def _format_single_param(p: ParamInfo) -> str:
    """Format a single parameter."""
    s = p.name
    if p.annotation:
        s += f": {p.annotation}"
    if p.default:
        s += f" = {p.default}"
    return s
