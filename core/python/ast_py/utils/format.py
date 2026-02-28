"""Code formatting utilities."""

import subprocess
from pathlib import Path
from typing import Any


def format_code(
    source: str,
    formatter: str = "auto",
    line_length: int = 88,
) -> dict[str, Any]:
    """Format Python code.

    Args:
        source: Python source code string
        formatter: Formatter to use ('black', 'autopep8', 'yapf', 'auto')
        line_length: Maximum line length

    Returns:
        Result dict with formatted code
    """
    result = {
        "formatted": source,
        "formatter": None,
        "success": True,
        "error": None,
    }

    # Try formatters in order
    formatters = ["black", "autopep8", "yapf"] if formatter == "auto" else [formatter]

    for fmt in formatters:
        try:
            if fmt == "black":
                formatted = _format_with_black(source, line_length)
            elif fmt == "autopep8":
                formatted = _format_with_autopep8(source, line_length)
            elif fmt == "yapf":
                formatted = _format_with_yapf(source)
            else:
                continue

            result["formatted"] = formatted
            result["formatter"] = fmt
            return result

        except Exception as e:
            result["error"] = str(e)
            continue

    # If no formatter available, return original
    result["success"] = False
    result["error"] = "No code formatter available"
    return result


def _format_with_black(source: str, line_length: int = 88) -> str:
    """Format code using black."""
    try:
        import black

        mode = black.FileMode(line_length=line_length)
        return black.format_str(source, mode=mode)
    except ImportError:
        # Try subprocess
        result = subprocess.run(
            ["black", "-", "--line-length", str(line_length)],
            input=source,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout
        raise RuntimeError(f"black failed: {result.stderr}")


def _format_with_autopep8(source: str, line_length: int = 88) -> str:
    """Format code using autopep8."""
    try:
        import autopep8

        return autopep8.fix_code(
            source,
            options={"max_line_length": line_length},
        )
    except ImportError:
        result = subprocess.run(
            ["autopep8", "-", "--max-line-length", str(line_length)],
            input=source,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout
        raise RuntimeError(f"autopep8 failed: {result.stderr}")


def _format_with_yapf(source: str) -> str:
    """Format code using yapf."""
    try:
        import yapf.yapflib.yapf_api

        return yapf.yapflib.yapf_api.FormatCode(source)[0]
    except ImportError:
        result = subprocess.run(
            ["yapf"],
            input=source,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout
        raise RuntimeError(f"yapf failed: {result.stderr}")


def format_module(
    module_path: Path,
    formatter: str = "auto",
    line_length: int = 88,
    in_place: bool = True,
) -> dict[str, Any]:
    """Format a Python module.

    Args:
        module_path: Path to the Python module
        formatter: Formatter to use
        line_length: Maximum line length
        in_place: Modify the file in place

    Returns:
        Result dict
    """
    source = module_path.read_text()
    result = format_code(source, formatter=formatter, line_length=line_length)

    if in_place and result["success"]:
        module_path.write_text(result["formatted"])

    result["module"] = str(module_path)
    return result
