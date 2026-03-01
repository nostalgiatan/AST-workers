#!/usr/bin/env python3
"""MCP Server for AST Workers - Language-aware code manipulation at AST level.

This server provides tools for manipulating source code at the Abstract Syntax Tree (AST)
level, ensuring safe and precise modifications. Unlike text-based editing, AST operations:
- Preserve code formatting and structure
- Handle indentation automatically
- Support scoped symbol naming (e.g., 'ClassName.method_name')
- Work across multiple programming languages

Architecture:
- Each language has its own CLI tool (ast-py for Python, ast-ts for TypeScript, etc.)
- This MCP server routes operations to the appropriate CLI
- Language is auto-detected from file extension, or can be explicitly specified

Supported Operations:
- INSERT: Add functions, classes, imports, class variables
- UPDATE: Modify function body, parameters, return type, decorators, docstring
- DELETE: Remove functions, classes, imports
- QUERY: List symbols, find symbols, show symbol with context
- UTILITY: Validate syntax, format code

Scoped Naming:
- Module-level function: 'function_name'
- Class method: 'ClassName.method_name'
- Nested class method: 'OuterClass.InnerClass.method_name'

Structured Body Format (for multi-line code with indentation):
- String: Simple single-line or multi-line code
- List format for precise indentation control:
  ["line at base indent", ("indented line 1", "indented line 2"), "back to base"]
  - str: Line at base indent level
  - tuple: Each item indented one level deeper
  - Nested tuples: Multiple levels of indentation
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional

from fastmcp import FastMCP
from pydantic import BaseModel, Field

# Create MCP server
mcp = FastMCP("AST Workers 🔧")

# CLI mapping based on file extension
CLI_MAP = {
    ".py": "ast-py",
    ".ts": "ast-ts",
    ".tsx": "ast-ts",
    ".js": "ast-ts",
    ".jsx": "ast-ts",
    ".go": "ast-go",
    ".rs": "ast-rust",
}

# Language name to CLI mapping (for explicit language declaration)
LANGUAGE_MAP = {
    "python": "ast-py",
    "py": "ast-py",
    "typescript": "ast-ts",
    "ts": "ast-ts",
    "tsx": "ast-ts",
    "javascript": "ast-ts",
    "js": "ast-ts",
    "jsx": "ast-ts",
    "go": "ast-go",
    "golang": "ast-go",
    "rust": "ast-rust",
    "rs": "ast-rust",
}

# Supported languages with their display names
SUPPORTED_LANGUAGES = {
    "python": {"cli": "ast-py", "extensions": [".py"], "display": "Python"},
    "typescript": {
        "cli": "ast-ts",
        "extensions": [".ts", ".tsx", ".js", ".jsx"],
        "display": "TypeScript/JavaScript",
    },
    "go": {"cli": "ast-go", "extensions": [".go"], "display": "Go"},
    "rust": {"cli": "ast-rust", "extensions": [".rs"], "display": "Rust"},
}


def get_cli(file_path: str, language: Optional[str] = None) -> Optional[str]:
    """Get the appropriate CLI for a file.

    Args:
        file_path: Path to the source file
        language: Optional explicit language name (e.g., "python", "typescript", "go", "rust")
                  If provided, this takes precedence over file extension detection.

    Returns:
        CLI name if available, None otherwise
    """
    # If language is explicitly specified, use it
    if language:
        cli = LANGUAGE_MAP.get(language.lower())
        if cli and shutil.which(cli):
            return cli
        return None

    # Fall back to file extension detection
    ext = Path(file_path).suffix.lower()
    cli = CLI_MAP.get(ext)
    if not cli:
        return None
    # Check if CLI is installed
    if shutil.which(cli):
        return cli
    return None


def run_cli_command(cli: str, args: list[str]) -> dict[str, Any]:
    """Run a CLI command and return parsed JSON result."""
    try:
        result = subprocess.run(
            [cli] + args,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0 and not result.stdout.strip():
            return {
                "success": False,
                "error": {
                    "code": "CLI_ERROR",
                    "message": result.stderr or f"CLI exited with code {result.returncode}",
                },
                "result": None,
            }

        # Parse JSON output
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": {
                    "code": "JSON_PARSE_ERROR",
                    "message": f"Failed to parse CLI output: {result.stdout[:200]}",
                },
                "result": None,
            }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": {
                "code": "TIMEOUT",
                "message": "CLI command timed out",
            },
            "result": None,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error": {
                "code": "CLI_NOT_FOUND",
                "message": f"CLI '{cli}' not found. Please install it first.",
            },
            "result": None,
        }
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e),
            },
            "result": None,
        }


# ========== INSERT OPERATIONS ==========


class InsertFunctionParams(BaseModel):
    """Parameters for insert-function operation.

    The body parameter supports two formats for flexible code insertion:

    1. String format (simple):
       - Single line: "return True"
       - Multi-line: "x = 1\\ny = 2\\nreturn x + y"

    2. Structured list format (precise indentation control):
       - Each string is a line at base indent (4 spaces inside function)
       - Tuple items are indented one level deeper
       - Nested tuples add more indentation levels

       Example: ["if condition:", ("do_something()", "return True"), "return False"]
       Result:   if condition:
                   do_something()
                   return True
                 return False
    """

    module: str = Field(description="Path to the source file (e.g., 'src/auth.py')")
    name: str = Field(description="Function name to insert")
    params: str = Field(
        default="",
        description="Parameters in Python syntax. Supports: positional-only (a, /, b), keyword-only (*, c, d=1), *args, **kwargs, type annotations. Example: 'x:int, y:int=10, *args, **kwargs'",
    )
    return_type: Optional[str] = Field(
        default=None,
        description="Return type annotation (e.g., 'bool', 'Optional[str]', 'list[dict]')",
    )
    body: str | list[str | tuple] = Field(
        default="pass",
        description="Function body. String for simple cases, or structured list for multi-line with controlled indentation. See class docstring for format details.",
    )
    class_name: Optional[str] = Field(
        default=None,
        description="Class name if inserting a method. Use scoped naming for nested classes: 'OuterClass.InnerClass'",
    )
    decorators: Optional[str] = Field(
        default=None,
        description="Decorators, comma-separated. With or without @. Example: '@dataclass, @classmethod' or 'dataclass, classmethod'",
    )
    is_async: bool = Field(default=False, description="Whether this is an async function")
    docstring: Optional[str] = Field(
        default=None,
        description="Function docstring (will be added as first line of body)",
    )
    after: Optional[str] = Field(
        default=None,
        description="Insert after this symbol name. Useful for ordering functions within a module/class.",
    )
    before: Optional[str] = Field(
        default=None,
        description="Insert before this symbol name. Alternative positioning option.",
    )
    language: Optional[str] = Field(
        default=None,
        description="Explicit language: 'python', 'typescript', 'go', 'rust'. Auto-detected from file extension if not specified.",
    )


@mcp.tool
def insert_function(params: InsertFunctionParams) -> dict[str, Any]:
    """Insert a function into a module or class at the AST level.

    This operation parses the source file, creates a new function node, and inserts
    it at the appropriate location. Unlike text editing, this:
    - Preserves existing formatting and comments
    - Handles indentation automatically
    - Validates syntax before writing

    Parameter Syntax (Python):
        Basic:           "x, y, z"
        With types:      "x:int, y:str, z:float"
        With defaults:   "x:int=0, y:str='hello'"
        Positional-only: "a, b, /, c, d"  (a, b are positional-only)
        Keyword-only:    "*, c, d=1"      (c, d must be keyword args)
        *args/**kwargs:  "*args:int, **kwargs:dict"
        Combined:        "self, a:int, /, b:str='', *args, c:bool=True, **kwargs"

    Body Format Examples:
        Simple string:
            body="return x + y"

        Multi-line string:
            body="x = calculate()\\ny = transform(x)\\nreturn y"

        Structured list (recommended for complex code):
            body=[
                "if condition:",
                ("do_first()", "do_second()"),
                "else:",
                ("handle_else()",),
                "return result"
            ]

        Nested indentation:
            body=[
                "try:",
                ("result = risky_operation()",),
                "except ValueError as e:",
                ("log_error(e)", "return None"),
                "return result"
            ]

    Positioning with after/before:
        - after="existing_func": Insert after existing_func
        - before="another_func": Insert before another_func
        - Neither: Appends at end of module/class

    Examples:
        # Simple module-level function
        insert_function(
            module="src/utils.py",
            name="calculate",
            params="x:int, y:int=0",
            return_type="int",
            body="return x + y"
        )

        # Method with decorators
        insert_function(
            module="src/models.py",
            name="get_full_name",
            class_name="User",
            decorators="@property",
            body="return f'{self.first} {self.last}'"
        )

        # Async function with structured body
        insert_function(
            module="src/api.py",
            name="fetch_data",
            params="url:str, timeout:int=30",
            return_type="dict",
            is_async=True,
            body=[
                "async with aiohttp.ClientSession() as session:",
                ("response = await session.get(url, timeout=timeout)",),
                ("return await response.json()",)
            ]
        )
    """
    cli = get_cli(params.module, params.language)
    if not cli:
        lang_info = f" (language={params.language})" if params.language else ""
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": f"No CLI available for file: {params.module}{lang_info}. Supported: python, typescript, go, rust",
            },
            "result": None,
        }

    args = ["insert-function", "-m", params.module, "-n", params.name]

    if params.params:
        args.extend(["-p", params.params])
    if params.return_type:
        args.extend(["-r", params.return_type])
    if params.body:
        # Support both string and structured list format
        if isinstance(params.body, list):
            import json

            args.extend(["-b", json.dumps(params.body)])
        else:
            args.extend(["-b", params.body])
    if params.class_name:
        args.extend(["-c", params.class_name])
    if params.decorators:
        args.extend(["-d", params.decorators])
    if params.is_async:
        args.append("--is-async")
    if params.docstring:
        args.extend(["--docstring", params.docstring])
    if params.after:
        args.extend(["--after", params.after])
    if params.before:
        args.extend(["--before", params.before])

    return run_cli_command(cli, args)


class InsertClassParams(BaseModel):
    """Parameters for insert-class operation."""

    module: str = Field(description="Path to the source file")
    name: str = Field(description="Class name to insert")
    bases: Optional[str] = Field(
        default=None,
        description="Base classes, comma-separated. Example: 'BaseModel, Serializable'",
    )
    decorators: Optional[str] = Field(
        default=None,
        description="Class decorators, comma-separated. Example: '@dataclass, @frozen'",
    )
    docstring: Optional[str] = Field(default=None, description="Class docstring")
    class_vars: Optional[str] = Field(
        default=None,
        description="Class variables with types and defaults. Format: 'var1:Type=default1, var2:Type2'",
    )
    after: Optional[str] = Field(default=None, description="Insert after this symbol name")
    before: Optional[str] = Field(default=None, description="Insert before this symbol name")
    language: Optional[str] = Field(default=None, description="Explicit language override")


@mcp.tool
def insert_class(params: InsertClassParams) -> dict[str, Any]:
    """Insert a new class definition into a module.

    Creates a class with the specified name, optionally with:
    - Inheritance (bases)
    - Decorators
    - Docstring
    - Class variables

    The class will have an empty body with just 'pass' unless class_vars are specified.
    Use insert_function to add methods after creating the class.

    Examples:
        # Simple class
        insert_class(module="src/models.py", name="User")

        # Dataclass with base and variables
        insert_class(
            module="src/models.py",
            name="User",
            bases="BaseModel",
            decorators="@dataclass",
            docstring="Represents a user in the system.",
            class_vars="id:int, name:str, email:str=''"
        )

        # Multiple inheritance
        insert_class(
            module="src/handlers.py",
            name="ApiHandler",
            bases="BaseHandler, LoggingMixin",
            decorators="@injectable"
        )

        # Position control
        insert_class(
            module="src/models.py",
            name="Admin",
            bases="User",
            after="User"  # Insert after the User class
        )
    """
    cli = get_cli(params.module, params.language)
    if not cli:
        lang_info = f" (language={params.language})" if params.language else ""
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": f"No CLI available for file: {params.module}{lang_info}. Supported: python, typescript, go, rust",
            },
            "result": None,
        }

    args = ["insert-class", "-m", params.module, "-n", params.name]

    if params.bases:
        args.extend(["--bases", params.bases])
    if params.decorators:
        args.extend(["-d", params.decorators])
    if params.docstring:
        args.extend(["--docstring", params.docstring])
    if params.class_vars:
        args.extend(["--class-vars", params.class_vars])
    if params.after:
        args.extend(["--after", params.after])
    if params.before:
        args.extend(["--before", params.before])

    return run_cli_command(cli, args)


class InsertImportParams(BaseModel):
    """Parameters for insert-import operation."""

    module: str = Field(description="Path to the source file")
    name: Optional[str] = Field(default=None, description="Import name. For 'import X' or 'from Y import X, Z'")
    from_module: Optional[str] = Field(
        default=None,
        description="Module to import from. If set, creates 'from X import Y'",
    )
    alias: Optional[str] = Field(
        default=None,
        description="Import alias. 'import X as Y' or 'from X import Y as Z'",
    )
    language: Optional[str] = Field(default=None, description="Explicit language override")


@mcp.tool
def insert_import(params: InsertImportParams) -> dict[str, Any]:
    """Insert an import statement at the top of a module.

    Automatically handles:
    - Placement after existing imports
    - Avoiding duplicates (by default)
    - Both 'import X' and 'from X import Y' styles

    Import Styles:
        1. Direct import: import os
           insert_import(module="file.py", name="os")

        2. From import: from typing import Optional
           insert_import(module="file.py", from_module="typing", name="Optional")

        3. Multiple names: from typing import Optional, List
           insert_import(module="file.py", from_module="typing", name="Optional, List")

        4. With alias: import numpy as np
           insert_import(module="file.py", name="numpy", alias="np")

        5. From import with alias: from typing import Optional as Opt
           insert_import(module="file.py", from_module="typing", name="Optional", alias="Opt")

    Examples:
        # Simple import
        insert_import(module="src/utils.py", name="os")

        # From import
        insert_import(module="src/auth.py", from_module="typing", name="Optional, Dict")

        # Import with alias
        insert_import(module="src/data.py", name="numpy", alias="np")

        # From import with multiple names
        insert_import(module="src/models.py", from_module="dataclasses", name="dataclass, field")
    """
    cli = get_cli(params.module, params.language)
    if not cli:
        lang_info = f" (language={params.language})" if params.language else ""
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": f"No CLI available for file: {params.module}{lang_info}. Supported: python, typescript, go, rust",
            },
            "result": None,
        }

    args = ["insert-import", "-m", params.module]

    if params.name:
        args.extend(["-n", params.name])
    if params.from_module:
        args.extend(["-f", params.from_module])
    if params.alias:
        args.extend(["-a", params.alias])

    return run_cli_command(cli, args)


class InsertClassVariableParams(BaseModel):
    """Parameters for insert-class-variable operation."""

    module: str = Field(description="Path to the source file")
    class_name: str = Field(description="Target class name")
    name: str = Field(description="Variable name")
    var_type: Optional[str] = Field(default=None, description="Type annotation")
    var_value: Optional[str] = Field(default=None, description="Initial value")
    language: Optional[str] = Field(
        default=None,
        description="Language: python, typescript, go, rust (auto-detected from file extension if not specified)",
    )


@mcp.tool
def insert_class_variable(params: InsertClassVariableParams) -> dict[str, Any]:
    """Insert a class variable into a class.

    Example:
        insert_class_variable(
            module="src/models.py",
            class_name="User",
            name="count",
            var_type="int",
            var_value="0"
        )
    """
    cli = get_cli(params.module, params.language)
    if not cli:
        lang_info = f" (language={params.language})" if params.language else ""
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": f"No CLI available for file: {params.module}{lang_info}. Supported: python, typescript, go, rust",
            },
            "result": None,
        }

    args = [
        "insert-class-variable",
        "-m",
        params.module,
        "-c",
        params.class_name,
        "-n",
        params.name,
    ]

    if params.var_type:
        args.extend(["-t", params.var_type])
    if params.var_value:
        args.extend(["-v", params.var_value])

    return run_cli_command(cli, args)


# ========== UPDATE OPERATIONS ==========


class UpdateFunctionParams(BaseModel):
    """Parameters for update-function operation.

    Supports multiple ways to modify a function:
    - Complete replacement: 'params' replaces all parameters
    - Incremental changes: 'add_params' and 'remove_params' modify existing
    - Body replacement: 'body' with string or structured format
    - Decorator management: add or remove decorators
    - Docstring: update or remove (empty string removes)
    """

    module: str = Field(description="Path to the source file")
    name: str = Field(description="Function name to update. Use scoped naming for methods: 'ClassName.method_name'")
    class_name: Optional[str] = Field(
        default=None,
        description="DEPRECATED: Use scoped naming in 'name' instead (e.g., 'ClassName.method')",
    )
    body: Optional[str | list[str | tuple]] = Field(
        default=None,
        description="New function body. Supports string or structured list format like insert_function.",
        description="New function body. Supports string or structured list format like insert_function.",
    )
    params: Optional[str] = Field(
        default=None,
        description="COMPLETE REPLACEMENT of all parameters. Same syntax as insert-function. Use carefully - removes all existing params!",
    )
    add_params: Optional[str] = Field(
        default=None,
        description="Parameters to ADD to existing ones. Won't duplicate if name exists.",
    )
    remove_params: Optional[list[str]] = Field(
        default=None,
        description="Parameter NAMES to remove (just the name, not the full definition)",
    )
    return_type: Optional[str] = Field(
        default=None,
        description="New return type. Empty string '' removes the return type annotation.",
    )
    add_decorators: Optional[list[str]] = Field(
        default=None, description="Decorators to add (e.g., ['@cache', '@log'])"
    )
    remove_decorators: Optional[list[str]] = Field(
        default=None,
        description="Decorator names to remove (just the name, e.g. ['cache', 'log'])",
    )
    docstring: Optional[str] = Field(
        default=None,
        description="New docstring. Empty string '' removes the docstring.",
    )
    language: Optional[str] = Field(default=None, description="Explicit language override")


@mcp.tool
def update_function(params: UpdateFunctionParams) -> dict[str, Any]:
    """Update an existing function's signature, body, or metadata.

    This is the most versatile tool for modifying existing code. It can:
    - Replace the entire parameter list
    - Add or remove individual parameters
    - Replace the function body
    - Add or remove decorators
    - Update or remove the return type annotation
    - Update or remove the docstring

    IMPORTANT - Parameter Modes:
        1. Complete replacement (params):
           - Replaces ALL parameters with new ones
           - Use when you want to change the entire signature
           - Example: params="self, x:int, y:str=''"

        2. Incremental changes (add_params, remove_params):
           - Preserves existing parameters
           - add_params: Adds new params (skips if name exists)
           - remove_params: Removes by name

        DO NOT use both modes together - results may be unexpected.

    Finding Methods:
        Use scoped naming in the 'name' parameter:
        - Module function: name="my_function"
        - Class method: name="MyClass.my_method"
        - Nested class: name="OuterClass.InnerClass.method"

        The class_name parameter is DEPRECATED - use scoped naming instead.

    Examples:
        # Replace entire signature
        update_function(
            module="src/auth.py",
            name="validate_token",
            params="token:str, expiry:int=3600, *, strict:bool=True"
        )

        # Update method body with structured format
        update_function(
            module="src/models.py",
            name="User.get_full_name",
            body=[
                "if self.middle_name:",
                ("return f'{self.first} {self.middle_name} {self.last}'",),
                "return f'{self.first} {self.last}'"
            ]
        )

        # Add decorator and parameter
        update_function(
            module="src/api.py",
            name="get_user",
            add_decorators=["@cache(3600)"],
            add_params="include_deleted:bool=False"
        )

        # Remove parameter and decorator
        update_function(
            module="src/utils.py",
            name="process",
            remove_params=["deprecated_flag"],
            remove_decorators=["old_decorator"]
        )

        # Update return type and add docstring
        update_function(
            module="src/auth.py",
            name="login",
            return_type="Optional[User]",
            docstring="Authenticate user and return User object or None."
        )
    """
    cli = get_cli(params.module, params.language)
    if not cli:
        lang_info = f" (language={params.language})" if params.language else ""
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": f"No CLI available for file: {params.module}{lang_info}. Supported: python, typescript, go, rust",
            },
            "result": None,
        }

    args = ["update-function", "-m", params.module, "-n", params.name]

    if params.class_name:
        args.extend(["-c", params.class_name])
    if params.body:
        # Support both string and structured list format
        if isinstance(params.body, list):
            import json

            args.extend(["-b", json.dumps(params.body)])
        else:
            args.extend(["-b", params.body])
    if params.params:
        args.extend(["-p", params.params])
    if params.add_params:
        args.extend(["--add-params", params.add_params])
    if params.remove_params:
        args.extend(["--remove-params"] + params.remove_params)
    if params.return_type is not None:
        args.extend(["-r", params.return_type])
    if params.add_decorators:
        args.extend(["--add-decorators"] + params.add_decorators)
    if params.remove_decorators:
        args.extend(["--remove-decorators"] + params.remove_decorators)
    if params.docstring:
        args.extend(["--docstring", params.docstring])

    return run_cli_command(cli, args)


# ========== DELETE OPERATIONS ==========


class DeleteFunctionParams(BaseModel):
    """Parameters for delete-function operation."""

    module: str = Field(description="Path to the source file")
    name: str = Field(description="Function name to delete. Use scoped naming for methods: 'ClassName.method'")
    class_name: Optional[str] = Field(default=None, description="DEPRECATED: Use scoped naming in 'name' instead")
    language: Optional[str] = Field(default=None, description="Explicit language override")


@mcp.tool
def delete_function(params: DeleteFunctionParams) -> dict[str, Any]:
    """Delete a function from a module or class.

    PERMANENTLY removes the function and all its code.
    Use with caution - consider backing up or using version control.

    Examples:
        # Delete module-level function
        delete_function(module="src/auth.py", name="deprecated_func")

        # Delete class method
        delete_function(module="src/auth.py", name="AuthService.old_method")
    """
    cli = get_cli(params.module, params.language)
    if not cli:
        lang_info = f" (language={params.language})" if params.language else ""
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": f"No CLI available for file: {params.module}{lang_info}. Supported: python, typescript, go, rust",
            },
            "result": None,
        }

    args = ["delete-function", "-m", params.module, "-n", params.name]

    if params.class_name:
        args.extend(["-c", params.class_name])

    return run_cli_command(cli, args)


class DeleteClassParams(BaseModel):
    """Parameters for delete-class operation."""

    module: str = Field(description="Path to the source file")
    name: str = Field(description="Class name to delete")
    language: Optional[str] = Field(default=None, description="Explicit language override")


@mcp.tool
def delete_class(params: DeleteClassParams) -> dict[str, Any]:
    """Delete a class from a module.

    PERMANENTLY removes the class and ALL its methods/contents.
    Use with caution - consider backing up or using version control.

    Examples:
        delete_class(module="src/models.py", name="DeprecatedModel")
        delete_class(module="src/old_code.py", name="LegacyHandler")
    """
    cli = get_cli(params.module, params.language)
    if not cli:
        lang_info = f" (language={params.language})" if params.language else ""
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": f"No CLI available for file: {params.module}{lang_info}. Supported: python, typescript, go, rust",
            },
            "result": None,
        }

    args = ["delete-class", "-m", params.module, "-n", params.name]

    return run_cli_command(cli, args)


# ========== RENAME OPERATIONS ==========


class RenameSymbolParams(BaseModel):
    """Parameters for rename-symbol operation."""

    module: str = Field(description="Path to the source file")
    old_name: str = Field(description="Current symbol name")
    new_name: str = Field(description="New symbol name")
    symbol_type: str = Field(
        default="function",
        description="Symbol type: 'function', 'class', 'variable', or 'all'",
    )
    language: Optional[str] = Field(default=None, description="Explicit language override")


@mcp.tool
def rename_symbol(params: RenameSymbolParams) -> dict[str, Any]:
    """Rename a symbol throughout a module.

    Renames all occurrences of the symbol in the module:
    - The definition itself
    - All references to it
    - Comments and strings may also be updated depending on context

    Symbol Types:
        - 'function': Rename a function (default)
        - 'class': Rename a class
        - 'variable': Rename a variable/assignment
        - 'all': Rename any symbol with matching name

    NOTE: This only renames within a single file. For cross-file renaming,
    you would need to rename in each file separately or use an IDE refactoring tool.

    Examples:
        # Rename a function
        rename_symbol(
            module="src/auth.py",
            old_name="old_validate",
            new_name="validate_token",
            symbol_type="function"
        )

        # Rename a class
        rename_symbol(
            module="src/models.py",
            old_name="OldUser",
            new_name="User",
            symbol_type="class"
        )

        # Rename a variable
        rename_symbol(
            module="src/config.py",
            old_name="DEBUG_MODE",
            new_name="ENABLE_DEBUG",
            symbol_type="variable"
        )
    """
    cli = get_cli(params.module, params.language)
    if not cli:
        lang_info = f" (language={params.language})" if params.language else ""
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": f"No CLI available for file: {params.module}{lang_info}. Supported: python, typescript, go, rust",
            },
            "result": None,
        }

    args = [
        "rename-symbol",
        "-m",
        params.module,
        "-o",
        params.old_name,
        "-n",
        params.new_name,
        "-t",
        params.symbol_type,
    ]

    return run_cli_command(cli, args)


# ========== QUERY OPERATIONS ==========


class QueryParams(BaseModel):
    """Parameters for query operations."""

    module: str = Field(description="Path to the source file")
    class_name: Optional[str] = Field(
        default=None,
        description="Filter by class name (for list_functions to show only methods)",
    )
    include_private: bool = Field(default=False, description="Include private members (starting with _)")
    language: Optional[str] = Field(default=None, description="Explicit language override")


@mcp.tool
def list_functions(params: QueryParams) -> dict[str, Any]:
    """List all functions in a module or methods in a class.

    Returns detailed information for each function including:
    - name: Function name
    - line, end_line: Location in file
    - params: List of parameters with name, type, default, kind
    - return_type: Return type annotation (if any)
    - decorators: List of decorators
    - docstring: Function docstring (if any)
    - is_async: Whether it's an async function
    - is_method: Whether it's a class method

    Use Cases:
    - Discover available functions in a module
    - Find methods in a class before modifying
    - Check function signatures
    - Identify functions needing documentation

    Examples:
        # List all module-level functions
        list_functions(module="src/auth.py")

        # List methods in a specific class
        list_functions(module="src/auth.py", class_name="AuthService")

        # Include private methods (those starting with _)
        list_functions(module="src/utils.py", include_private=True)
    """
    cli = get_cli(params.module, params.language)
    if not cli:
        lang_info = f" (language={params.language})" if params.language else ""
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": f"No CLI available for file: {params.module}{lang_info}. Supported: python, typescript, go, rust",
            },
            "result": None,
        }

    args = ["list-functions", "-m", params.module]

    if params.class_name:
        args.extend(["-c", params.class_name])
    if params.include_private:
        args.append("--include-private")

    return run_cli_command(cli, args)


@mcp.tool
def list_classes(params: QueryParams) -> dict[str, Any]:
    """List all classes in a module with their structure.

    Returns detailed information for each class including:
    - name: Class name
    - line, end_line: Location in file
    - bases: List of base classes
    - decorators: List of class decorators
    - methods: List of method names
    - class_vars: List of class variable names
    - docstring: Class docstring (if any)

    Use Cases:
    - Understand class hierarchy
    - Find available classes for instantiation
    - Check class structure before modification
    - Identify classes needing documentation

    Examples:
        # List all classes in a module
        list_classes(module="src/models.py")

        # Include private classes (those starting with _)
        list_classes(module="src/internal.py", include_private=True)
    """
    cli = get_cli(params.module, params.language)
    if not cli:
        lang_info = f" (language={params.language})" if params.language else ""
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": f"No CLI available for file: {params.module}{lang_info}. Supported: python, typescript, go, rust",
            },
            "result": None,
        }

    args = ["list-classes", "-m", params.module]

    return run_cli_command(cli, args)


@mcp.tool
def list_imports(params: QueryParams) -> dict[str, Any]:
    """List all import statements in a module.

    Returns detailed information for each import including:
    - type: 'import' or 'from'
    - module: The module being imported
    - name: Specific name(s) imported (for 'from' imports)
    - alias: Import alias if used (as ...)
    - line: Line number

    Use Cases:
    - Check what a module depends on
    - Find unused imports (compare with usage)
    - Verify correct import style

    Examples:
        list_imports(module="src/auth.py")
        list_imports(module="src/models.py")
    """
    cli = get_cli(params.module, params.language)
    if not cli:
        lang_info = f" (language={params.language})" if params.language else ""
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": f"No CLI available for file: {params.module}{lang_info}. Supported: python, typescript, go, rust",
            },
            "result": None,
        }

    args = ["list-imports", "-m", params.module]

    return run_cli_command(cli, args)


class FindSymbolParams(BaseModel):
    """Parameters for find-symbol operation."""

    module: str = Field(description="Path to the source file")
    name: str = Field(description="Symbol name to find (exact match)")
    symbol_type: Optional[str] = Field(default=None, description="Filter by type: 'function', 'class', or 'variable'")
    language: Optional[str] = Field(default=None, description="Explicit language override")


@mcp.tool
def find_symbol(params: FindSymbolParams) -> dict[str, Any]:
    """Find a symbol's location in a module - simpler than show_symbol, returns just location info.

    Use this when you only need to know WHERE a symbol is defined, not its code.
    For viewing the actual code, use show_symbol instead.

    Returns:
        - found: Whether the symbol exists
        - symbols: List of matching symbols with type, line, end_line

    Differences from show_symbol:
        - find_symbol: Returns location only (line numbers)
        - show_symbol: Returns location AND the actual code

    Use Cases:
    - Check if a symbol exists before modifying
    - Get line numbers for navigation
    - Verify symbol type

    Examples:
        # Find a function
        find_symbol(module="src/auth.py", name="validate_token")

        # Find a class
        find_symbol(module="src/models.py", name="User", symbol_type="class")

        # Check if variable exists
        find_symbol(module="src/config.py", name="DEBUG", symbol_type="variable")
    """
    cli = get_cli(params.module, params.language)
    if not cli:
        lang_info = f" (language={params.language})" if params.language else ""
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": f"No CLI available for file: {params.module}{lang_info}. Supported: python, typescript, go, rust",
            },
            "result": None,
        }

    args = ["find-symbol", "-m", params.module, "-n", params.name]

    if params.symbol_type:
        args.extend(["-t", params.symbol_type])

    return run_cli_command(cli, args)


class ShowSymbolParams(BaseModel):
    """Parameters for show-symbol operation.

    Scoped Naming Convention:
        - Module-level function: "function_name"
        - Class: "ClassName"
        - Class method: "ClassName.method_name"
        - Nested class: "OuterClass.InnerClass"
        - Nested class method: "OuterClass.InnerClass.method_name"
        - Module variable: "VARIABLE_NAME"
        - Import: "import_name" or "alias_name"
    """

    module: str = Field(description="Path to the source file")
    name: str = Field(
        description="Symbol name with optional scope (e.g., 'function_name', 'ClassName.method', 'Outer.Inner.method')"
    )
    symbol_type: Optional[str] = Field(
        default=None,
        description="Optional type filter: 'function', 'class', 'variable', 'import'. Auto-detected if not specified.",
    )
    language: Optional[str] = Field(default=None, description="Explicit language override")


@mcp.tool
def show_symbol(params: ShowSymbolParams) -> dict[str, Any]:
    """Display a symbol with its surrounding context - the most useful tool for code exploration.

    This tool shows you the actual code of a symbol along with context lines before and after.
    Perfect for:
    - Understanding existing code before modifying it
    - Viewing function/class signatures
    - Checking docstrings and comments
    - Finding where a symbol is defined

    Returns:
        - found: Whether the symbol was found
        - line: Starting line number
        - end_line: Ending line number
        - symbol_type: Type of the symbol (function, class, variable, import, etc.)
        - code: The actual source code with surrounding context
        - docstring: If available, the symbol's docstring

    Scoped Naming (IMPORTANT):
        Use dot notation to specify exactly which symbol you want:

        Simple symbols:
            name="my_function"           # Module-level function
            name="MyClass"               # Class definition
            name="CONSTANT"              # Module variable

        Class members:
            name="MyClass.__init__"      # Constructor
            name="MyClass.method"        # Instance method
            name="MyClass._private"      # Private method

        Nested structures:
            name="OuterClass.InnerClass"           # Inner class
            name="OuterClass.InnerClass.method"    # Inner class method

    Type Filtering:
        Use symbol_type when there might be ambiguity:
            symbol_type="function"  # Only match functions
            symbol_type="class"     # Only match classes
            symbol_type="variable"  # Only match variables/assignments
            symbol_type="import"    # Only match import statements

    Examples:
        # Show a module-level function
        show_symbol(module="src/auth.py", name="validate_token")

        # Show a class method
        show_symbol(module="src/auth.py", name="AuthService.login")

        # Show a specific class
        show_symbol(module="src/models.py", name="User", symbol_type="class")

        # Show a private method
        show_symbol(module="src/utils.py", name="DataProcessor._validate")

        # Show a deeply nested method
        show_symbol(module="src/complex.py", name="App.Handler.Process.run")
    """
    cli = get_cli(params.module, params.language)
    if not cli:
        lang_info = f" (language={params.language})" if params.language else ""
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": f"No CLI available for file: {params.module}{lang_info}. Supported: python, typescript, go, rust",
            },
            "result": None,
        }

    args = ["show", "-m", params.module, "-n", params.name]

    if params.symbol_type:
        args.extend(["-t", params.symbol_type])

    return run_cli_command(cli, args)


# ========== UTILITY OPERATIONS ==========


class ValidateParams(BaseModel):
    """Parameters for validate operation."""

    module: str = Field(description="Path to the source file")
    language: Optional[str] = Field(default=None, description="Explicit language override")


@mcp.tool
def validate_syntax(params: ValidateParams) -> dict[str, Any]:
    """Validate syntax of a source file.

    Checks if the file has valid syntax without modifying anything.
    Use this BEFORE making changes to ensure the file is in a good state.

    Returns:
        - valid: Boolean indicating if syntax is valid
        - error: Error details if invalid (line, column, message)

    Use Cases:
        - Pre-check before modifications
        - Debug syntax errors
        - Validate generated code

    Examples:
        validate_syntax(module="src/auth.py")
        validate_syntax(module="src/types.ts", language="typescript")
    """
    cli = get_cli(params.module, params.language)
    if not cli:
        lang_info = f" (language={params.language})" if params.language else ""
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": f"No CLI available for file: {params.module}{lang_info}. Supported: python, typescript, go, rust",
            },
            "result": None,
        }

    args = ["validate", "-m", params.module]

    return run_cli_command(cli, args)


class FormatParams(BaseModel):
    """Parameters for format operation."""

    module: str = Field(description="Path to the source file")
    formatter: str = Field(
        default="auto",
        description="Formatter to use: 'black', 'autopep8', 'yapf', or 'auto' (uses available formatter)",
    )
    line_length: int = Field(default=88, description="Maximum line length (default: 88 for Black)")
    language: Optional[str] = Field(default=None, description="Explicit language override")


@mcp.tool
def format_code(params: FormatParams) -> dict[str, Any]:
    """Format code in a module using standard formatters.

    Reformats the entire file to follow style guidelines.
    Supported formatters (Python):
    - black: The uncompromising code formatter (recommended)
    - autopep8: Formats according to PEP 8
    - yapf: Yet Another Python Formatter

    NOTE: The specified formatter must be installed in the environment.

    Examples:
        # Auto-format with any available formatter
        format_code(module="src/auth.py")

        # Use specific formatter with custom line length
        format_code(module="src/auth.py", formatter="black", line_length=100)

    Example:
        format_code(module="src/auth.py", formatter="black")
    """
    cli = get_cli(params.module, params.language)
    if not cli:
        lang_info = f" (language={params.language})" if params.language else ""
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": f"No CLI available for file: {params.module}{lang_info}. Supported: python, typescript, go, rust",
            },
            "result": None,
        }

    args = [
        "format",
        "-m",
        params.module,
        "--formatter",
        params.formatter,
        "--line-length",
        str(params.line_length),
    ]

    return run_cli_command(cli, args)


# ========== BATCH OPERATIONS ==========


class BatchParams(BaseModel):
    """Parameters for batch operation.

    Each operation in the list is a dict with at minimum an 'op' field.
    Available operations:

    - {"op": "insert-import", "name": "...", "from": "...", "alias": "..."}
    - {"op": "insert-function", "name": "...", "params": "...", "body": "...", ...}
    - {"op": "insert-class", "name": "...", "bases": "...", ...}
    - {"op": "update-function", "name": "...", "body": "...", ...}
    - {"op": "delete-function", "name": "..."}
    - {"op": "delete-class", "name": "..."}
    - {"op": "rename-symbol", "old": "...", "new": "...", "type": "..."}
    """

    module: str = Field(description="Path to the source file")
    operations: list[dict[str, Any]] = Field(description="List of operations to execute in order")
    continue_on_error: bool = Field(
        default=False,
        description="If True, continue executing remaining operations even if one fails",
    )
    language: Optional[str] = Field(default=None, description="Explicit language override")


@mcp.tool
def batch_operations(params: BatchParams) -> dict[str, Any]:
    """Execute multiple AST operations in a single call.

    Efficient way to make multiple changes to a file in one operation.
    Operations are executed in order, and the file is written only once.

    Operation Types:
        - insert-import: Add an import
        - insert-function: Add a function
        - insert-class: Add a class
        - update-function: Modify a function
        - delete-function: Remove a function
        - delete-class: Remove a class
        - rename-symbol: Rename a symbol

    Example:
        batch_operations(
            module="src/auth.py",
            operations=[
                {"op": "insert-import", "from": "typing", "name": "Optional"},
                {"op": "insert-function", "name": "validate", "params": "token:str", "return_type": "bool", "body": "return bool(token)"},
                {"op": "insert-function", "name": "get_user", "class_name": "AuthService", "params": "self, user_id:int", "return_type": "Optional[User]"},
            ]
        )

    With continue_on_error=True, all operations are attempted even if some fail.
    Results include success/failure for each operation.
    """
    cli = get_cli(params.module, params.language)
    if not cli:
        lang_info = f" (language={params.language})" if params.language else ""
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": f"No CLI available for file: {params.module}{lang_info}. Supported: python, typescript, go, rust",
            },
            "result": None,
        }

    args = ["batch", "-m", params.module, "--ops", json.dumps(params.operations)]

    if params.continue_on_error:
        args.append("--continue-on-error")

    return run_cli_command(cli, args)


# ========== INFO TOOLS ==========


@mcp.tool
def list_supported_languages() -> dict[str, Any]:
    """List supported programming languages and their CLI tool status.

    Returns:
        - languages: Dict of supported languages with CLI name and file extensions
        - installed: List of CLI tools that are installed and available
        - not_installed: List of CLI tools that need to be installed

    Supported Languages:
        - Python: ast-py CLI
        - TypeScript/JavaScript: ast-ts CLI
        - Go: ast-go CLI
        - Rust: ast-rust CLI

    Language is auto-detected from file extension:
        - .py → Python
        - .ts, .tsx, .js, .jsx → TypeScript/JavaScript
        - .go → Go
        - .rs → Rust

    Example:
        list_supported_languages()
    """
    result: dict[str, Any] = {
        "languages": SUPPORTED_LANGUAGES,
        "installed": [],
        "not_installed": [],
    }

    for ext, cli in CLI_MAP.items():
        if shutil.which(cli):
            if cli not in result["installed"]:
                result["installed"].append(cli)
        else:
            if cli not in result["not_installed"]:
                result["not_installed"].append(cli)

    return {
        "success": True,
        "error": None,
        "result": result,
    }


@mcp.tool
async def get_tools_info() -> dict[str, Any]:
    """Get detailed information about all available AST Workers tools.

    Returns:
        - server_name: Name of this MCP server
        - tool_count: Number of available tools
        - tools: List of all tools with names, descriptions, and input schemas

    Use this to discover all available capabilities and their parameters.
    Each tool's inputSchema follows JSON Schema format.

    Example:
        get_tools_info()
    """
    from fastmcp.client import Client

    tools_info = []

    # Use FastMCP client to list tools from the server instance
    async with Client(mcp) as client:
        tools = await client.list_tools()

        for tool in tools:
            tool_info = {
                "name": tool.name,
                "description": tool.description or "",
            }

            # Get input schema if available
            if hasattr(tool, "inputSchema") and tool.inputSchema:
                tool_info["inputSchema"] = tool.inputSchema

            tools_info.append(tool_info)

    return {
        "success": True,
        "error": None,
        "result": {
            "server_name": "AST Workers",
            "tool_count": len(tools_info),
            "tools": tools_info,
        },
    }


def main():
    """Entry point for the CLI.

    Supports multiple transport modes:
    - stdio: Standard input/output (default, for MCP clients)
    - http: HTTP Server-Sent Events transport
    - sse: Server-Sent Events (alias for http)

    Usage:
        ast-workers-mcp                    # stdio mode (default)
        ast-workers-mcp --transport stdio  # stdio mode
        ast-workers-mcp --transport http   # HTTP mode on default port
        ast-workers-mcp --transport http --port 8080  # HTTP on port 8080
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="AST Workers MCP Server - Language-aware code manipulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--transport",
        "-t",
        choices=["stdio", "http", "sse"],
        default="stdio",
        help="Transport mode: stdio (default), http, or sse",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=8000,
        help="Port for HTTP/SSE mode (default: 8000)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for HTTP/SSE mode (default: 127.0.0.1)",
    )

    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport in ("http", "sse"):
        mcp.run(transport="sse", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
