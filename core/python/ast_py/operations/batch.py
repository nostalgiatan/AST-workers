"""Batch operations using JSON configuration."""

import json
from pathlib import Path
from typing import Any

from .delete import delete_class, delete_function
from .insert import (
    insert_class,
    insert_class_variable,
    insert_dunder_all,
    insert_function,
    insert_import,
    insert_slots,
)
from .rename import rename_symbol
from .update import update_function


def execute_batch(
    module_path: Path,
    operations: list[dict[str, Any]],
    stop_on_error: bool = True,
) -> dict[str, Any]:
    """Execute a batch of operations on a module.

    Args:
        module_path: Path to the Python module
        operations: List of operation dictionaries
        stop_on_error: Stop execution on first error

    Returns:
        Result dict with operation details
    """
    results = []
    success_count = 0
    error_count = 0

    for i, op in enumerate(operations):
        op_type = op.get("op") or op.get("operation")

        if not op_type:
            results.append(
                {
                    "index": i,
                    "success": False,
                    "error": "Missing 'op' or 'operation' field",
                }
            )
            error_count += 1
            if stop_on_error:
                break
            continue

        try:
            result = _execute_single_op(module_path, op_type, op)
            results.append(
                {
                    "index": i,
                    "operation": op_type,
                    "success": True,
                    "result": result,
                }
            )
            success_count += 1
        except Exception as e:
            results.append(
                {
                    "index": i,
                    "operation": op_type,
                    "success": False,
                    "error": str(e),
                }
            )
            error_count += 1
            if stop_on_error:
                break

    return {
        "operation": "batch",
        "module": str(module_path),
        "total": len(operations),
        "success_count": success_count,
        "error_count": error_count,
        "results": results,
        "modified": success_count > 0,
    }


def _execute_single_op(module_path: Path, op_type: str, op: dict) -> dict:
    if op_type in ("insert-function", "insert_function", "if"):
        name = op.get("name") or ""
        return insert_function(
            module_path=module_path,
            function_name=name,
            params_str=op.get("params", ""),
            return_type=op.get("return_type") or op.get("return-type"),
            body=op.get("body", "pass"),
            class_name=op.get("class") or op.get("class_name"),
            decorators=op.get("decorators"),
            is_async=op.get("is_async", False),
            docstring=op.get("docstring"),
            after=op.get("after"),
            before=op.get("before"),
        )
    if op_type in ("update-function", "update_function", "uf"):
        name = op.get("name") or ""
        return update_function(
            module_path=module_path,
            function_name=name,
            class_name=op.get("class") or op.get("class_name"),
            new_body=op.get("body"),
            add_params=op.get("add_params") or op.get("add-params"),
            remove_params=op.get("remove_params") or op.get("remove-params"),
            new_return_type=op.get("return_type") or op.get("return-type"),
            add_decorators=op.get("add_decorators") or op.get("add-decorators"),
            remove_decorators=op.get("remove_decorators") or op.get("remove-decorators"),
            new_docstring=op.get("docstring"),
        )
    if op_type in ("delete-function", "delete_function", "df"):
        name = op.get("name") or ""
        return delete_function(
            module_path=module_path,
            function_name=name,
            class_name=op.get("class") or op.get("class_name"),
        )
    if op_type in ("insert-class", "insert_class", "ic"):
        name = op.get("name") or ""
        return insert_class(
            module_path=module_path,
            class_name=name,
            bases=op.get("bases"),
            decorators=op.get("decorators"),
            docstring=op.get("docstring"),
            class_vars=op.get("class_vars") or op.get("class-vars"),
            after=op.get("after"),
            before=op.get("before"),
        )
    if op_type in ("delete-class", "delete_class", "dc"):
        name = op.get("name") or ""
        return delete_class(module_path=module_path, class_name=name)
    if op_type in ("insert-class-variable", "insert_class_variable", "icv"):
        cls = op.get("class") or op.get("class_name") or ""
        var = op.get("name") or ""
        return insert_class_variable(
            module_path=module_path,
            class_name=cls,
            var_name=var,
            var_type=op.get("type") or op.get("var_type"),
            var_value=op.get("value") or op.get("var_value"),
        )
    if op_type in ("insert-slots", "insert_slots", "is"):
        cls = op.get("class") or op.get("class_name") or ""
        slots = op.get("slots") or []
        if isinstance(slots, str):
            slots = slots.split(",")
        return insert_slots(module_path=module_path, class_name=cls, slots=slots)
    if op_type in ("insert-dunder-all", "insert_dunder_all", "iall"):
        names = op.get("names") or []
        if isinstance(names, str):
            names = names.split(",")
        return insert_dunder_all(module_path=module_path, names=names, mode=op.get("mode", "replace"))
    if op_type in ("insert-import", "insert_import", "ii"):
        return insert_import(
            module_path=module_path,
            name=op.get("name"),
            from_module=op.get("from") or op.get("from_module"),
            alias=op.get("alias"),
            check_duplicate=op.get("check_duplicate", True),
        )
    if op_type in ("rename-symbol", "rename_symbol", "rn"):
        old = op.get("old") or op.get("old_name") or ""
        new = op.get("new") or op.get("new_name") or ""
        return rename_symbol(
            module_path=module_path,
            old_name=old,
            new_name=new,
            symbol_type=op.get("type") or op.get("symbol_type", "function"),
        )
    raise ValueError(f"Unknown operation type: {op_type}")


def parse_operations(ops_str: str) -> list[dict]:
    """Parse operations from JSON string.

    Supports both single operation and array of operations.
    """
    data = json.loads(ops_str)

    if isinstance(data, dict):
        return [data]
    elif isinstance(data, list):
        return data
    else:
        raise ValueError("Operations must be a JSON object or array")
