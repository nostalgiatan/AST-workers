#!/usr/bin/env python3
"""AST Workers Python CLI - Unified AST operations for Python code.

This CLI provides AST-level operations for Python code manipulation,
including inserting, deleting, querying, and renaming code elements.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .operations import (
    delete_class,
    delete_function,
    execute_batch,
    find_symbol,
    insert_class,
    insert_class_variable,
    insert_dunder_all,
    insert_function,
    insert_import,
    insert_slots,
    list_classes,
    list_functions,
    list_imports,
    parse_operations,
    rename_symbol,
    update_function,
)
from .utils import validate_syntax


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ast-py",
        description="AST-level operations for Python code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List functions in a module
  ast-py list-functions --module src/auth.py

  # List methods in a class
  ast-py list-functions --module src/auth.py --class AuthService

  # Insert a function
  ast-py insert-function -m src/auth.py -n validate_token -p "token:str" -r bool -b "return len(token) > 10"

  # Insert a method into a class
  ast-py insert-function -m src/auth.py -c AuthService -n check_permissions -p "user:User, action:str" -r bool

  # Insert with advanced parameters (positional-only, keyword-only, *args, **kwargs)
  ast-py insert-function -m src/utils.py -n process -p "data, /, strict:bool=True, *, encoding:str='utf-8', **kwargs"

  # Insert with decorators
  ast-py insert-function -m src/api.py -n get_user -p "user_id:int" -d "@route('/users/<int:user_id>'), @login_required"

  # Insert async function
  ast-py insert-function -m src/async_ops.py -n fetch_data --is-async -p "url:str" -r "dict"

  # Insert a class with docstring and class variables
  ast-py insert-class -m src/models.py -n User -b "BaseModel" --docstring "User model" --class-vars "id:int, name:str"

  # Insert a class variable
  ast-py insert-class-variable -m src/models.py -c User -n count -t int -v 0

  # Insert __slots__
  ast-py insert-slots -m src/models.py -c User --slots id name email

  # Insert __all__
  ast-py insert-dunder-all -m src/auth.py --names login logout authenticate

  # Update a function body
  ast-py update-function -m src/auth.py -n validate_token --body "return token is not None"

  # Add parameters to a function
  ast-py update-function -m src/auth.py -n login --add-params "remember:bool=False"

  # Remove parameters from a function
  ast-py update-function -m src/auth.py -n login --remove-params deprecated_param

  # Change return type
  ast-py update-function -m src/auth.py -n get_user --return-type "Optional[User]"

  # Add decorators
  ast-py update-function -m src/api.py -n endpoint --add-decorators "@cache(3600)"

  # Remove decorators
  ast-py update-function -m src/api.py -n endpoint --remove-decorators old_decorator

  # Update docstring
  ast-py update-function -m src/auth.py -n login --docstring "Authenticate user"

  # Insert an import
  ast-py insert-import -m src/auth.py --from typing --name Optional

  # Delete a function
  ast-py delete-function -m src/auth.py -n old_function

  # Rename a symbol
  ast-py rename-symbol -m src/auth.py -o old_name -n new_name -t function
""",
    )

    subparsers = parser.add_subparsers(dest="operation", required=True, help="Operation to perform")

    # ========== INSERT FUNCTION ==========
    p_func = subparsers.add_parser("insert-function", help="Insert a function", aliases=["if"])
    p_func.add_argument("--module", "-m", required=True, help="Target module path")
    p_func.add_argument("--class", "-c", dest="class_name", help="Target class name (for methods)")
    p_func.add_argument("--name", "-n", required=True, help="Function name")
    p_func.add_argument(
        "--params",
        "-p",
        default="",
        help="""Parameters (supports all Python syntax):
  - Basic: x, y:int, z=1
  - With annotation and default: x:int=1
  - Positional-only: a, /, b
  - Keyword-only: *, c, d=1
  - *args: *args:str
  - **kwargs: **kwargs:dict
Example: "a, b, /, c:int, d:int=1, *, e:str, **kwargs" """,
    )
    p_func.add_argument("--return-type", "-r", help="Return type annotation")
    p_func.add_argument("--body", "-b", default="pass", help="Function body")
    p_func.add_argument("--decorators", "-d", help="Decorators (comma-separated, with or without @)")
    p_func.add_argument("--is-async", action="store_true", help="Make function async")
    p_func.add_argument("--docstring", help="Function docstring")
    p_func.add_argument("--after", help="Insert after this function/class name")
    p_func.add_argument("--before", help="Insert before this function/class name")

    # ========== UPDATE FUNCTION ==========
    p_ufunc = subparsers.add_parser("update-function", help="Update a function", aliases=["uf"])
    p_ufunc.add_argument("--module", "-m", required=True, help="Target module path")
    p_ufunc.add_argument("--class", "-c", dest="class_name", help="Target class name (for methods)")
    p_ufunc.add_argument("--name", "-n", required=True, help="Function name")
    p_ufunc.add_argument("--body", "-b", help="New function body")
    p_ufunc.add_argument(
        "--params",
        "-p",
        help="Complete replacement of parameters (same format as insert-function)",
    )
    p_ufunc.add_argument("--add-params", help="Parameters to add (same format as insert-function)")
    p_ufunc.add_argument("--remove-params", nargs="+", help="Parameter names to remove")
    p_ufunc.add_argument("--return-type", "-r", help="New return type (empty string to remove)")
    p_ufunc.add_argument("--add-decorators", nargs="+", help="Decorators to add")
    p_ufunc.add_argument("--remove-decorators", nargs="+", help="Decorator names to remove")
    p_ufunc.add_argument("--docstring", help="New docstring")

    # ========== INSERT CLASS ==========
    p_class = subparsers.add_parser("insert-class", help="Insert a class", aliases=["ic"])
    p_class.add_argument("--module", "-m", required=True, help="Target module path")
    p_class.add_argument("--name", "-n", required=True, help="Class name")
    p_class.add_argument("--bases", help="Base classes (comma-separated)")
    p_class.add_argument("--decorators", "-d", help="Decorators (comma-separated)")
    p_class.add_argument("--docstring", help="Class docstring")
    p_class.add_argument("--class-vars", help="Class variables (e.g., 'count:int=0, name:str')")
    p_class.add_argument("--after", help="Insert after this function/class name")
    p_class.add_argument("--before", help="Insert before this function/class name")

    # ========== INSERT CLASS VARIABLE ==========
    p_cvar = subparsers.add_parser("insert-class-variable", help="Insert a class variable", aliases=["icv"])
    p_cvar.add_argument("--module", "-m", required=True, help="Target module path")
    p_cvar.add_argument("--class", "-c", dest="class_name", required=True, help="Target class name")
    p_cvar.add_argument("--name", "-n", required=True, help="Variable name")
    p_cvar.add_argument("--type", "-t", dest="var_type", help="Type annotation")
    p_cvar.add_argument("--value", "-v", dest="var_value", help="Initial value")

    # ========== INSERT SLOTS ==========
    p_slots = subparsers.add_parser("insert-slots", help="Insert __slots__ into a class", aliases=["is"])
    p_slots.add_argument("--module", "-m", required=True, help="Target module path")
    p_slots.add_argument("--class", "-c", dest="class_name", required=True, help="Target class name")
    p_slots.add_argument("--slots", "-s", nargs="+", required=True, help="Slot names")

    # ========== INSERT __ALL__ ==========
    p_all = subparsers.add_parser("insert-dunder-all", help="Insert or update __all__", aliases=["iall"])
    p_all.add_argument("--module", "-m", required=True, help="Target module path")
    p_all.add_argument("--names", "-n", nargs="+", required=True, help="Names to export")
    p_all.add_argument(
        "--mode",
        choices=["replace", "append", "prepend"],
        default="replace",
        help="How to handle existing __all__",
    )

    # ========== INSERT IMPORT ==========
    p_import = subparsers.add_parser("insert-import", help="Insert an import statement", aliases=["ii"])
    p_import.add_argument("--module", "-m", required=True, help="Target module path")
    p_import.add_argument("--name", "-n", help="Import name (for 'import X' or 'from Y import X')")
    p_import.add_argument("--from", "-f", dest="from_module", help="Module to import from")
    p_import.add_argument("--alias", "-a", help="Import alias (as ...)")
    p_import.add_argument("--no-check-duplicate", action="store_true", help="Skip duplicate check")

    # ========== LIST FUNCTIONS ==========
    p_lfunc = subparsers.add_parser("list-functions", help="List functions in a module/class", aliases=["lf"])
    p_lfunc.add_argument("--module", "-m", required=True, help="Target module path")
    p_lfunc.add_argument("--class", "-c", dest="class_name", help="Filter by class name")
    p_lfunc.add_argument(
        "--include-private",
        action="store_true",
        help="Include private functions (_name)",
    )

    # ========== LIST CLASSES ==========
    p_lclass = subparsers.add_parser("list-classes", help="List classes in a module", aliases=["lc"])
    p_lclass.add_argument("--module", "-m", required=True, help="Target module path")

    # ========== LIST IMPORTS ==========
    p_limport = subparsers.add_parser("list-imports", help="List imports in a module", aliases=["li"])
    p_limport.add_argument("--module", "-m", required=True, help="Target module path")

    # ========== FIND SYMBOL ==========
    p_find = subparsers.add_parser("find-symbol", help="Find a symbol in a module", aliases=["fs"])
    p_find.add_argument("--module", "-m", required=True, help="Target module path")
    p_find.add_argument("--name", "-n", required=True, help="Symbol name")
    p_find.add_argument("--type", "-t", choices=["function", "class", "variable"], help="Symbol type")

    # ========== DELETE FUNCTION ==========
    p_dfunc = subparsers.add_parser("delete-function", help="Delete a function", aliases=["df"])
    p_dfunc.add_argument("--module", "-m", required=True, help="Target module path")
    p_dfunc.add_argument("--name", "-n", required=True, help="Function name")
    p_dfunc.add_argument("--class", "-c", dest="class_name", help="Class name (if method)")

    # ========== DELETE CLASS ==========
    p_dclass = subparsers.add_parser("delete-class", help="Delete a class", aliases=["dc"])
    p_dclass.add_argument("--module", "-m", required=True, help="Target module path")
    p_dclass.add_argument("--name", "-n", required=True, help="Class name")

    # ========== RENAME SYMBOL ==========
    p_rename = subparsers.add_parser("rename-symbol", help="Rename a symbol", aliases=["rn"])
    p_rename.add_argument("--module", "-m", required=True, help="Target module path")
    p_rename.add_argument("--old", "-o", required=True, help="Current name")
    p_rename.add_argument("--new", "-n", required=True, help="New name")
    p_rename.add_argument(
        "--type",
        "-t",
        choices=["function", "class", "variable", "all"],
        default="function",
        help="Symbol type",
    )

    # ========== SHOW SYMBOL ==========
    p_show = subparsers.add_parser("show", help="Show symbol with context", aliases=["s"])
    p_show.add_argument("--module", "-m", required=True, help="Target module path")
    p_show.add_argument(
        "--name",
        "-n",
        required=True,
        help="""Symbol name (supports scoped naming):
  - Simple: my_function, MyClass
  - Scoped: MyClass.method, MyClass.InnerClass.method""",
    )
    p_show.add_argument(
        "--type",
        "-t",
        choices=["function", "class", "variable", "import"],
        help="Symbol type filter (auto-detected if not specified)",
    )
    p_show.add_argument("--context", "-C", type=int, default=3, help="Context lines around symbol")

    # ========== VALIDATE ==========
    p_validate = subparsers.add_parser("validate", help="Validate Python syntax", aliases=["v"])
    p_validate.add_argument("--module", "-m", required=True, help="Target module path")

    # ========== FORMAT ==========
    p_format = subparsers.add_parser("format", help="Format Python code", aliases=["fmt"])
    p_format.add_argument("--module", "-m", required=True, help="Target module path")
    p_format.add_argument(
        "--formatter",
        choices=["black", "autopep8", "yapf", "auto"],
        default="auto",
        help="Formatter to use",
    )
    p_format.add_argument("--line-length", type=int, default=88, help="Maximum line length")

    # ========== BATCH ==========
    p_batch = subparsers.add_parser("batch", help="Execute multiple operations from JSON", aliases=["b"])
    p_batch.add_argument("--module", "-m", required=True, help="Target module path")
    p_batch.add_argument("--ops", "-o", help="JSON string of operations")
    p_batch.add_argument("--file", "-f", help="JSON file containing operations")
    p_batch.add_argument("--continue-on-error", action="store_true", help="Continue on errors")

    return parser


def output_result(success: bool, result: Any = None, error: dict | None = None) -> None:
    """Output JSON result to stdout."""
    response = {"success": success, "error": error, "result": result}
    print(json.dumps(response, indent=2, ensure_ascii=False))


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()

    try:
        module_path = Path(args.module) if hasattr(args, "module") else None

        if module_path and not module_path.exists():
            output_result(
                False,
                error={
                    "code": "MODULE_NOT_FOUND",
                    "message": f"Module not found: {args.module}",
                    "details": {"path": str(module_path.absolute())},
                },
            )
            return 1

        # Assert module_path is not None for type checker
        assert module_path is not None

        # ========== INSERT OPERATIONS ==========
        if args.operation in ("insert-function", "if"):
            result = insert_function(
                module_path=module_path,
                function_name=args.name,
                params_str=args.params,
                return_type=args.return_type,
                body=args.body,
                class_name=args.class_name,
                decorators=args.decorators,
                is_async=args.is_async,
                docstring=args.docstring,
                after=args.after,
                before=args.before,
            )

        elif args.operation in ("insert-class", "ic"):
            result = insert_class(
                module_path=module_path,
                class_name=args.name,
                bases=args.bases,
                decorators=args.decorators,
                docstring=args.docstring,
                class_vars=args.class_vars,
                after=args.after,
                before=args.before,
            )

        elif args.operation in ("insert-class-variable", "icv"):
            result = insert_class_variable(
                module_path=module_path,
                class_name=args.class_name,
                var_name=args.name,
                var_type=args.var_type,
                var_value=args.var_value,
            )

        elif args.operation in ("insert-slots", "is"):
            result = insert_slots(
                module_path=module_path,
                class_name=args.class_name,
                slots=args.slots,
            )

        elif args.operation in ("insert-dunder-all", "iall"):
            result = insert_dunder_all(
                module_path=module_path,
                names=args.names,
                mode=args.mode,
            )

        elif args.operation in ("insert-import", "ii"):
            result = insert_import(
                module_path=module_path,
                name=args.name,
                from_module=args.from_module,
                alias=args.alias,
                check_duplicate=not args.no_check_duplicate,
            )

        # ========== UPDATE OPERATIONS ==========
        elif args.operation in ("update-function", "uf"):
            result = update_function(
                module_path=module_path,
                function_name=args.name,
                class_name=args.class_name,
                new_body=args.body,
                params=getattr(args, "params", None),
                add_params=args.add_params,
                remove_params=args.remove_params,
                new_return_type=args.return_type,
                add_decorators=args.add_decorators,
                remove_decorators=args.remove_decorators,
                new_docstring=args.docstring,
            )

        # ========== QUERY OPERATIONS ==========
        elif args.operation in ("list-functions", "lf"):
            result = list_functions(
                module_path=module_path,
                class_name=args.class_name,
                include_private=args.include_private,
            )

        elif args.operation in ("list-classes", "lc"):
            result = list_classes(module_path=module_path)

        elif args.operation in ("list-imports", "li"):
            result = list_imports(module_path=module_path)

        elif args.operation in ("find-symbol", "fs"):
            result = find_symbol(
                module_path=module_path,
                name=args.name,
                symbol_type=args.type,
            )

        # ========== DELETE OPERATIONS ==========
        elif args.operation in ("delete-function", "df"):
            result = delete_function(
                module_path=module_path,
                function_name=args.name,
                class_name=args.class_name,
            )

        elif args.operation in ("delete-class", "dc"):
            result = delete_class(
                module_path=module_path,
                class_name=args.name,
            )

        # ========== RENAME OPERATIONS ==========
        elif args.operation in ("rename-symbol", "rn"):
            result = rename_symbol(
                module_path=module_path,
                old_name=args.old,
                new_name=args.new,
                symbol_type=args.type,
            )

        # ========== SHOW OPERATIONS ==========
        elif args.operation in ("show", "s"):
            from .operations.query import show_symbol

            result = show_symbol(
                module_path=module_path,
                name=args.name,
                symbol_type=getattr(args, "type", None),
            )

        # ========== UTILITY OPERATIONS ==========
        elif args.operation in ("validate", "v"):
            source = module_path.read_text()
            result = validate_syntax(source)
            result["module"] = str(module_path)

        elif args.operation in ("format", "fmt"):
            from .utils import format_module

            result = format_module(
                module_path=module_path,
                formatter=args.formatter,
                line_length=args.line_length,
            )

        # ========== BATCH OPERATIONS ==========
        elif args.operation in ("batch", "b"):
            # Get operations from string or file
            if args.ops:
                ops = parse_operations(args.ops)
            elif args.file:
                with open(args.file, "r") as f:
                    ops = parse_operations(f.read())
            else:
                output_result(
                    False,
                    error={
                        "code": "MISSING_OPS",
                        "message": "Either --ops or --file must be provided",
                    },
                )
                return 1

            result = execute_batch(
                module_path=module_path,
                operations=ops,
                stop_on_error=not args.continue_on_error,
            )

        else:
            output_result(
                False,
                error={
                    "code": "UNKNOWN_OPERATION",
                    "message": f"Unknown operation: {args.operation}",
                },
            )
            return 1

        output_result(True, result=result)
        return 0

    except ValueError as e:
        output_result(
            False,
            error={
                "code": "OPERATION_FAILED",
                "message": str(e),
            },
        )
        return 1

    except Exception as e:
        output_result(
            False,
            error={
                "code": "INTERNAL_ERROR",
                "message": str(e),
                "details": {"type": type(e).__name__},
            },
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
