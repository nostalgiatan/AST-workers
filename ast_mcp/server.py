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

# Language capabilities matrix
# Defines which features are supported by each language
LANGUAGE_CAPABILITIES = {
    "python": {
        "insert_function": True,
        "insert_class": True,
        "insert_import": True,
        "insert_variable": True,
        "insert_interface": False,  # Python uses Protocol/ABC, not native interface
        "insert_type_alias": False,  # Python has TypeAlias but not commonly used as separate construct
        "insert_enum": False,  # Python has Enum class, not language-level enum
        "insert_namespace": False,  # Python uses modules/packages
        "insert_property": True,  # Python has @property decorator
        "insert_accessor": True,  # Python has @property for getters/setters
        "update_function": True,
        "delete_function": True,
        "delete_class": True,
        "delete_variable": True,
        "delete_interface": False,
        "delete_enum": False,
        "delete_type_alias": False,
        "rename_symbol": True,
        "list_functions": True,
        "list_classes": True,
        "list_imports": True,
        "list_variables": True,
        "list_interfaces": False,
        "list_enums": False,
        "list_type_aliases": False,
        "show_symbol": True,
        "find_symbol": True,
        "validate_syntax": True,
        "format_code": True,
        "batch_operations": True,
    },
    "typescript": {
        "insert_function": True,
        "insert_class": True,
        "insert_import": True,
        "insert_variable": True,
        "insert_interface": True,  # TypeScript native feature
        "insert_type_alias": True,  # TypeScript native feature
        "insert_enum": True,  # TypeScript native feature
        "insert_namespace": True,  # TypeScript native feature
        "insert_property": True,
        "insert_accessor": True,  # TypeScript getters/setters
        "update_function": True,
        "delete_function": True,
        "delete_class": True,
        "delete_variable": True,
        "delete_interface": True,
        "delete_enum": True,
        "delete_type_alias": True,
        "rename_symbol": True,
        "list_functions": True,
        "list_classes": True,
        "list_imports": True,
        "list_variables": True,
        "list_interfaces": True,
        "list_enums": True,
        "list_type_aliases": True,
        "show_symbol": True,
        "find_symbol": True,
        "validate_syntax": True,
        "format_code": True,
        "batch_operations": True,
    },
    "go": {
        # Go AST operations
        "insert_function": True,
        "insert_class": False,  # Go uses structs, not classes
        "insert_struct": True,  # Go-specific: insert struct
        "insert_import": True,
        "insert_variable": False,
        "insert_interface": False,  # TODO: implement
        "insert_type_alias": False,
        "insert_enum": False,  # Go has iota, not enum
        "insert_namespace": False,  # Go uses packages
        "update_function": True,
        "delete_function": True,
        "delete_class": False,  # Use delete_struct
        "delete_struct": True,  # Go-specific: delete struct
        "rename_symbol": False,  # TODO: implement
        "list_functions": True,
        "list_classes": False,  # Use list_structs
        "list_structs": True,  # Go-specific: list structs
        "list_imports": True,
        "show_symbol": True,
        "find_symbol": False,  # TODO: implement
        "validate_syntax": True,
        "format_code": False,  # Go uses gofmt
        "batch_operations": False,  # TODO: implement
    },
    "rust": {
        # Placeholder - will be implemented later
        "insert_function": False,
        "insert_class": False,  # Rust has structs, not classes
        "insert_import": False,
        "insert_variable": False,
        "insert_interface": False,  # Rust has traits
        "insert_type_alias": False,
        "insert_enum": True,  # Rust has native enums
        "insert_namespace": False,  # Rust uses modules
        "update_function": False,
        "delete_function": False,
        "delete_class": False,
        "rename_symbol": False,
        "list_functions": False,
        "list_classes": False,
        "list_imports": False,
        "show_symbol": False,
        "find_symbol": False,
        "validate_syntax": False,
        "format_code": False,
        "batch_operations": False,
    },
}


def get_language_from_file(file_path: str) -> Optional[str]:
    """Get language name from file extension."""
    ext = Path(file_path).suffix.lower()
    for lang, info in SUPPORTED_LANGUAGES.items():
        if ext in info["extensions"]:
            return lang
    return None


def check_capability(language: str, operation: str) -> bool:
    """Check if a language supports a specific operation."""
    capabilities = LANGUAGE_CAPABILITIES.get(language, {})
    return capabilities.get(operation, False)


def check_capability_or_error(module: str, language: Optional[str], operation: str) -> tuple[bool, Optional[str], Optional[str]]:
    """Check if the language supports an operation, return error info if not.

    Returns:
        (success, cli, error_message)
        - success=True, cli=cli_name, error=None: Operation is supported
        - success=False, cli=None, error=error_message: Operation not supported
    """
    lang = language or get_language_from_file(module)
    if not lang:
        return False, None, f"Cannot determine language for file: {module}"

    cli = get_cli(module, language)
    if not cli:
        lang_info = f" (language={language})" if language else ""
        return False, None, f"No CLI available for file: {module}{lang_info}. Supported: python, typescript"

    if not check_capability(lang, operation):
        return False, None, f"Operation '{operation}' is not supported for language '{lang}'. Check get_language_capabilities for supported operations."

    return True, cli, None


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
        if cli:
            cli_path = find_cli(cli)
            if cli_path:
                return cli_path
        return None

    # Fall back to file extension detection
    ext = Path(file_path).suffix.lower()
    cli = CLI_MAP.get(ext)
    if not cli:
        return None
    # Check if CLI is installed
    return find_cli(cli)


def find_cli(cli_name: str) -> Optional[str]:
    """Find CLI executable in PATH or in installed locations.

    Checks:
    1. System PATH (shutil.which)
    2. ~/.local/bin (ast-workers-mcp install-ts location)

    Returns:
        Full path to CLI if found, None otherwise
    """
    # First check in PATH
    cli_path = shutil.which(cli_name)
    if cli_path:
        return cli_path

    # Check in ~/.local/bin (where ast-workers-mcp install-ts installs)
    local_bin = Path.home() / ".local" / "bin" / cli_name
    if local_bin.exists() and local_bin.is_file():
        return str(local_bin)

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
    """Universal parameters for insert-function operation.

    IMPORTANT - Language Differences:

    Python/TypeScript:
        - Module-level function: Provide only 'name' (e.g., name="validate_token")
        - Class method: MUST provide BOTH 'name' AND 'class_name'
          (e.g., name="login", class_name="AuthService")

    Go:
        - Go does NOT have classes, it has structs with methods
        - Function: Provide only 'name' (e.g., name="hello")
        - Method: MUST provide 'name' AND 'receiver'
          (e.g., name="GetName", receiver="u *User" or receiver="u User")
        - The 'receiver' parameter specifies the method receiver variable and type
        - Go methods are defined outside the struct, not inside

    Universal Parameters (supported by ALL languages):
        - module: Path to source file (required)
        - name: Function/method name (required)
        - params: Parameter string (optional, language-specific syntax)
        - return_type: Return type annotation (optional)
        - body: Function body (optional, default: "pass" for Python, empty for Go/TS)
        - docstring: Documentation comment (optional)

    Python-specific Parameters:
        - class_name: REQUIRED for methods (class that contains the method)
        - decorators: Comma-separated decorators
        - after/before: Position for insertion
        - is_async: Whether async function

    TypeScript-specific Parameters:
        - class_name: REQUIRED for methods
        - type_params: Generic type parameters (e.g., 'T, U extends string')
        - is_async: Whether async function
        - is_static: Static method
        - is_private: Private method
        - is_protected: Protected method

    Go-specific Parameters:
        - receiver: REQUIRED for methods. Format: "varName TypeName" or "varName *TypeName"
          Examples: "u User", "u *User", "s *Server"
        - Note: Go does NOT use 'class_name' - use 'receiver' instead

    Examples:
        # Python module-level function
        insert_function(module="auth.py", name="validate", body="return True")

        # Python class method
        insert_function(module="auth.py", name="login", class_name="AuthService", body="pass")

        # Go function
        insert_function(module="main.go", name="hello", params="name string", return_type="string")

        # Go method on struct
        insert_function(module="models.go", name="GetName", receiver="u *User", return_type="string")
    """

    module: str = Field(description="Path to source file (required)")
    name: str = Field(description="Function/method name to insert (required)")
    params: Optional[str] = Field(
        default=None,
        description="Parameter string (optional, language-specific syntax)",
    )
    return_type: Optional[str] = Field(
        default=None,
        description="Return type annotation (optional)",
    )
    body: Optional[str | list] = Field(
        default=None,
        description="Function body - string or structured list for multi-line code",
    )
    class_name: Optional[str] = Field(
        default=None,
        description="[Python/TypeScript only] REQUIRED for class methods. Omit for module-level functions. Go uses 'receiver' instead.",
    )
    type_params: Optional[str] = Field(
        default=None,
        description="[TypeScript only] Generic type parameters. E.g., 'T, U extends string'",
    )
    decorators: Optional[str] = Field(
        default=None,
        description="[Python only] Decorators, comma-separated.",
    )
    is_async: bool = Field(default=False, description="[Python/TypeScript] Whether this is an async function")
    is_static: bool = Field(default=False, description="[TypeScript only] Static method")
    is_private: bool = Field(default=False, description="[TypeScript only] Private method")
    is_protected: bool = Field(default=False, description="[TypeScript only] Protected method")
    docstring: Optional[str] = Field(
        default=None,
        description="Function docstring (Python) or JSDoc comment (TypeScript) or comment (Go)",
    )
    after: Optional[str] = Field(
        default=None,
        description="[Python only] Insert after this symbol name.",
    )
    before: Optional[str] = Field(
        default=None,
        description="[Python only] Insert before this symbol name.",
    )
    receiver: Optional[str] = Field(
        default=None,
        description="[Go only] REQUIRED for Go methods. Method receiver format: 'varName TypeName' or 'varName *TypeName'. Examples: 'u User', 'u *User', 's *Server'",
    )
    language: Optional[str] = Field(
        default=None,
        description="Explicit language override (python, typescript, go). Auto-detected from file extension if not provided.",
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
    if params.docstring:
        args.extend(["--docstring", params.docstring])

    # Detect language for language-specific parameters
    lang = params.language or get_language_from_file(params.module)

    if lang == "python":
        # Python-specific
        if params.decorators:
            args.extend(["-d", params.decorators])
        if params.after:
            args.extend(["--after", params.after])
        if params.before:
            args.extend(["--before", params.before])
        if params.is_async:
            args.append("--is-async")
    elif lang == "typescript":
        # TypeScript-specific
        if params.type_params:
            args.extend(["-t", params.type_params])
        if params.is_async:
            args.append("--is-async")
        if params.is_static:
            args.append("--is-static")
        if params.is_private:
            args.append("--is-private")
        if params.is_protected:
            args.append("--is-protected")
    elif lang == "go":
        # Go-specific
        if params.receiver:
            args.extend(["--receiver", params.receiver])
        elif params.class_name:
            # If class_name is provided, convert to receiver format
            args.extend(["--receiver", f"u *{params.class_name}"])

    return run_cli_command(cli, args)


class InsertClassParams(BaseModel):
    """Parameters for insert-class operation.

    IMPORTANT - Language Support:
        - Python: Full support for classes with inheritance, decorators, etc.
        - TypeScript: Full support for classes with interfaces, generics, etc.
        - Go: NOT SUPPORTED. Go does NOT have classes. Use 'insert_struct' instead.

    For Go, use insert_struct:
        insert_struct(module="models.go", name="User", fields="Name string, Age int")

    Universal Parameters (Python/TypeScript):
        - module: Path to source file
        - name: Class name
        - bases: Base classes (inheritance)
        - docstring: Class documentation

    Python-specific:
        - decorators: Class decorators (@dataclass, etc.)
        - class_vars: Class variables
        - after/before: Position control

    TypeScript-specific:
        - implements: Interface implementations
        - type_params: Generic type parameters
        - is_abstract: Abstract class modifier
    """

    # Universal Parameters
    module: str = Field(description="Path to the source file")
    name: str = Field(description="Class name to insert")
    bases: Optional[str] = Field(
        default=None,
        description="[Python/TypeScript] Base classes, comma-separated. Example: 'BaseModel, Serializable'",
    )
    docstring: Optional[str] = Field(default=None, description="Class docstring")
    after: Optional[str] = Field(default=None, description="[Python only] Insert after this symbol name")
    before: Optional[str] = Field(default=None, description="[Python only] Insert before this symbol name")
    language: Optional[str] = Field(default=None, description="Explicit language override")

    # Python-specific
    decorators: Optional[str] = Field(
        default=None,
        description="[Python only] Class decorators, comma-separated. Example: '@dataclass, @frozen'",
    )
    class_vars: Optional[str] = Field(
        default=None,
        description="[Python only] Class variables with types and defaults. Format: 'var1:Type=default1, var2:Type2'",
    )

    # TypeScript-specific
    implements: Optional[str] = Field(
        default=None,
        description="[TypeScript only] Interfaces to implement, comma-separated. Example: 'Serializable, Comparable'",
    )
    type_params: Optional[str] = Field(
        default=None,
        description="[TypeScript only] Generic type parameters. E.g., 'T, U extends BaseEntity'",
    )
    is_abstract: bool = Field(default=False, description="[TypeScript only] Whether this is an abstract class")


@mcp.tool
def insert_class(params: InsertClassParams) -> dict[str, Any]:
    """Insert a new class definition into a module.

    Creates a class with the specified name, optionally with:
    - Inheritance (bases)
    - Decorators (Python)
    - Interfaces (TypeScript implements)
    - Generic type parameters (TypeScript)
    - Abstract modifier (TypeScript)
    - Docstring
    - Class variables (Python)

    The class will have an empty body with just 'pass' unless class_vars are specified.
    Use insert_function to add methods after creating the class.

    Python Examples:
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

    TypeScript Examples:
        # Generic class with interface
        insert_class(
            module="src/models.ts",
            name="Repository",
            type_params="T extends Entity",
            implements="Serializable, Comparable"
        )

        # Abstract class
        insert_class(
            module="src/base.ts",
            name="BaseService",
            is_abstract=True,
            implements="IService"
        )

    Position Control:
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

    if params.docstring:
        args.extend(["--docstring", params.docstring])

    # Detect language for language-specific parameters
    lang = params.language or get_language_from_file(params.module)

    if lang == "python":
        # Python-specific
        if params.bases:
            args.extend(["--bases", params.bases])
        if params.decorators:
            args.extend(["-d", params.decorators])
        if params.class_vars:
            args.extend(["--class-vars", params.class_vars])
        if params.after:
            args.extend(["--after", params.after])
        if params.before:
            args.extend(["--before", params.before])
    elif lang == "typescript":
        # TypeScript-specific
        if params.bases:
            args.extend(["-e", params.bases])  # TypeScript uses --extends, not --bases
        if params.implements:
            args.extend(["-i", params.implements])
        if params.type_params:
            args.extend(["-t", params.type_params])
        if params.is_abstract:
            args.append("--is-abstract")

    return run_cli_command(cli, args)


class InsertStructParams(BaseModel):
    """Parameters for insert-struct operation (Go-only).

    IMPORTANT - Go Structs vs Python/TypeScript Classes:
        - Go does NOT have classes. It uses structs with methods.
        - Use 'insert_struct' for Go, NOT 'insert_class'.
        - Methods are defined separately using 'insert_function' with 'receiver' parameter.
        - Python/TypeScript: use 'insert_class'

    Parameters:
        - module: Path to Go source file (required)
        - name: Struct name (required, should be PascalCase for exported structs)
        - fields: Struct fields (optional)
        - docstring: Struct documentation (optional)

    Field Format:
        - Basic: "Name string, Age int"
        - With tags: 'Name string `json:"name"`, Age int `json:"age"`'
        - Pointer fields: "User *User, Children []*User"
        - Nested types: "Config map[string]interface{}, Data []byte"

    After creating a struct, add methods using insert_function with receiver:
        insert_function(module="models.go", name="GetName", receiver="u *User", return_type="string")
    """

    module: str = Field(description="Path to the Go source file")
    name: str = Field(description="Struct name to insert (PascalCase for exported structs)")
    fields: Optional[str] = Field(
        default=None,
        description="Struct fields. Format: 'Name string, Age int' or with tags: 'Name string `json:\"name\"`'",
    )
    docstring: Optional[str] = Field(default=None, description="Struct documentation comment")
    language: Optional[str] = Field(default=None, description="Explicit language override (default: go)")


@mcp.tool
def insert_struct(params: InsertStructParams) -> dict[str, Any]:
    """Insert a new struct definition into a Go module.

    Creates a struct with the specified name and fields.

    Examples:
        # Simple struct
        insert_struct(
            module="src/models.go",
            name="User",
            fields="Name string, Age int"
        )

        # Struct with documentation
        insert_struct(
            module="src/models.go",
            name="User",
            fields="Name string, Age int",
            docstring="User represents a user in the system."
        )

        # Struct with field tags
        insert_struct(
            module="src/models.go",
            name="User",
            fields='Name string `json:"name"`, Age int `json:"age"`'
        )
    """
    lang = params.language or "go"
    cli = get_cli(params.module, lang)
    if not cli:
        lang_info = f" (language={params.language})" if params.language else ""
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": f"No CLI available for file: {params.module}{lang_info}. Supported: go",
            },
            "result": None,
        }

    args = ["insert-struct", "-m", params.module, "-n", params.name]

    if params.fields:
        args.extend(["-f", params.fields])
    if params.docstring:
        args.extend(["--docstring", params.docstring])

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

    Import Styles (Python/TypeScript):
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

    Import Styles (Go):
        1. Simple import: import "fmt"
           insert_import(module="file.go", name="fmt")

        2. With alias: import f "fmt"
           insert_import(module="file.go", name="fmt", alias="f")

        3. External package: import "github.com/user/package"
           insert_import(module="file.go", name="github.com/user/package")

    Examples:
        # Simple import
        insert_import(module="src/utils.py", name="os")

        # From import
        insert_import(module="src/auth.py", from_module="typing", name="Optional, Dict")

        # Import with alias
        insert_import(module="src/data.py", name="numpy", alias="np")

        # From import with multiple names
        insert_import(module="src/models.py", from_module="dataclasses", name="dataclass, field")

        # Go import
        insert_import(module="src/main.go", name="fmt")

        # Go import with alias
        insert_import(module="src/main.go", name="github.com/user/pkg", alias="pkg")
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

    # Detect language for language-specific parameters
    lang = params.language or get_language_from_file(params.module)

    if lang == "go":
        # Go uses -p for path and -a for alias
        if params.name:
            args.extend(["-p", params.name])
        if params.alias:
            args.extend(["-a", params.alias])
    else:
        # Python/TypeScript use -n, -f, -a
        if params.name:
            args.extend(["-n", params.name])
        if params.from_module:
            args.extend(["-f", params.from_module])
        if params.alias:
            args.extend(["-a", params.alias])

    return run_cli_command(cli, args)


class InsertInterfaceParams(BaseModel):
    """Parameters for insert-interface operation (TypeScript only)."""

    module: str = Field(description="Path to the source file")
    name: str = Field(description="Interface name")
    extends: Optional[str] = Field(
        default=None,
        description="Interfaces to extend, comma-separated. Example: 'BaseEntity, Serializable'",
    )
    properties: Optional[str] = Field(
        default=None,
        description="Property definitions. Format: 'prop1:Type1, prop2:Type2, prop3?:OptionalType'",
    )
    type_params: Optional[str] = Field(
        default=None,
        description="Generic type parameters. E.g., 'T, U extends Base'",
    )
    language: Optional[str] = Field(default=None, description="Explicit language override")


@mcp.tool
def insert_interface(params: InsertInterfaceParams) -> dict[str, Any]:
    """Insert a TypeScript interface definition.

    TypeScript-only operation. Python uses Protocol or ABC instead.

    Creates an interface with:
    - Optional extends clause (interface inheritance)
    - Property definitions
    - Generic type parameters

    Property Syntax:
        - Required: "name:string, age:number"
        - Optional: "name:string, age?:number" (note the ?)
        - Readonly: "readonly id:string, name:string"

    Examples:
        # Simple interface
        insert_interface(
            module="src/types.ts",
            name="User",
            properties="id:string, name:string, email:string"
        )

        # Interface with extends
        insert_interface(
            module="src/types.ts",
            name="Admin",
            extends="User",
            properties="permissions:string[], role:string"
        )

        # Generic interface
        insert_interface(
            module="src/types.ts",
            name="Response",
            type_params="T",
            properties="data:T, status:number, message:string"
        )

        # Multiple extends
        insert_interface(
            module="src/types.ts",
            name="AdminUser",
            extends="User, Auditable",
            properties="role:Role"
        )
    """
    success, cli, error = check_capability_or_error(params.module, params.language, "insert_interface")
    if not success:
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_OPERATION",
                "message": error,
            },
            "result": None,
        }

    assert cli is not None  # Type guard - cli is guaranteed non-None when success is True

    args = ["insert-interface", "-m", params.module, "-n", params.name]

    if params.extends:
        args.extend(["-e", params.extends])
    if params.properties:
        args.extend(["--properties", params.properties])
    if params.type_params:
        args.extend(["-t", params.type_params])

    return run_cli_command(cli, args)


class InsertTypeAliasParams(BaseModel):
    """Parameters for insert-type-alias operation (TypeScript only)."""

    module: str = Field(description="Path to the source file")
    name: str = Field(description="Type alias name")
    type_definition: str = Field(description="The type definition. E.g., 'string | number', '{ name: string, age: number }'")
    type_params: Optional[str] = Field(
        default=None,
        description="Generic type parameters. E.g., 'T, U'",
    )
    language: Optional[str] = Field(default=None, description="Explicit language override")


@mcp.tool
def insert_type_alias(params: InsertTypeAliasParams) -> dict[str, Any]:
    """Insert a TypeScript type alias.

    TypeScript-only operation. Python uses TypeAlias or type hints directly.

    Creates a type alias for complex types:
    - Union types
    - Intersection types
    - Object types
    - Generic types

    Examples:
        # Simple type alias
        insert_type_alias(
            module="src/types.ts",
            name="UserId",
            type_definition="string | number"
        )

        # Object type
        insert_type_alias(
            module="src/types.ts",
            name="User",
            type_definition="{ id: string, name: string, email: string }"
        )

        # Generic type alias
        insert_type_alias(
            module="src/types.ts",
            name="Response",
            type_definition="{ data: T, status: number }",
            type_params="T"
        )

        # Union with literal types
        insert_type_alias(
            module="src/types.ts",
            name="Status",
            type_definition="'pending' | 'active' | 'inactive'"
        )
    """
    success, cli, error = check_capability_or_error(params.module, params.language, "insert_type_alias")
    if not success:
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_OPERATION",
                "message": error,
            },
            "result": None,
        }

    assert cli is not None  # Type guard - cli is guaranteed non-None when success is True

    args = ["insert-type-alias", "-m", params.module, "-n", params.name, "--type", params.type_definition]

    if params.type_params:
        args.extend(["-t", params.type_params])

    return run_cli_command(cli, args)


class InsertEnumParams(BaseModel):
    """Parameters for insert-enum operation (TypeScript only)."""

    module: str = Field(description="Path to the source file")
    name: str = Field(description="Enum name")
    members: str = Field(description="Enum members, comma-separated. E.g., 'Red, Green, Blue' or 'Red=1, Green=2'")
    is_const: bool = Field(default=False, description="Whether this is a const enum")
    language: Optional[str] = Field(default=None, description="Explicit language override")


@mcp.tool
def insert_enum(params: InsertEnumParams) -> dict[str, Any]:
    """Insert a TypeScript enum definition.

    TypeScript-only operation. Python uses Enum class instead.

    Creates an enum with:
    - Auto-incrementing values (default)
    - Explicit values
    - Const modifier

    Member Syntax:
        - Auto values: "Red, Green, Blue" (values: 0, 1, 2)
        - Explicit values: "Red=1, Green=2, Blue=3"
        - String values: 'Yes="yes", No="no"'

    Examples:
        # Simple enum (auto values)
        insert_enum(
            module="src/types.ts",
            name="Color",
            members="Red, Green, Blue"
        )

        # Enum with explicit values
        insert_enum(
            module="src/types.ts",
            name="HttpStatus",
            members="OK=200, BadRequest=400, NotFound=404"
        )

        # Const enum (inlined by compiler)
        insert_enum(
            module="src/types.ts",
            name="Direction",
            members="Up, Down, Left, Right",
            is_const=True
        )

        # String enum
        insert_enum(
            module="src/types.ts",
            name="Status",
            members='Pending="pending", Active="active", Inactive="inactive"'
        )
    """
    success, cli, error = check_capability_or_error(params.module, params.language, "insert_enum")
    if not success:
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_OPERATION",
                "message": error,
            },
            "result": None,
        }

    assert cli is not None  # Type guard - cli is guaranteed non-None when success is True

    args = ["insert-enum", "-m", params.module, "-n", params.name, "--members", params.members]

    if params.is_const:
        args.append("--is-const")

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

    IMPORTANT - Language Differences for Finding Methods:

    Python/TypeScript:
        - Use scoped naming: name="ClassName.method_name"
        - Example: name="AuthService.login"

    Go:
        - For functions: name="functionName"
        - For methods: name="MethodName" (just the method name, NOT "StructName.MethodName")
        - Go methods are identified by their receiver, not by being "inside" a struct

    Universal Parameters (all languages):
        - module: Path to source file
        - name: Function/method name
        - body: New function body
        - params: Complete parameter replacement
        - add_params/remove_params: Incremental parameter changes
        - return_type: New return type
        - docstring: New docstring

    Python-specific:
        - add_decorators/remove_decorators: Decorator management
    """

    # Universal Parameters
    module: str = Field(description="Path to the source file")
    name: str = Field(description="Function/method name. For Python/TS methods use 'ClassName.method'. For Go methods use just the method name.")
    body: Optional[str | list[str | tuple]] = Field(
        default=None,
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
    docstring: Optional[str] = Field(
        default=None,
        description="New docstring. Empty string '' removes the docstring.",
    )
    language: Optional[str] = Field(default=None, description="Explicit language override")

    # Deprecated
    class_name: Optional[str] = Field(
        default=None,
        description="DEPRECATED: Use scoped naming in 'name' instead (e.g., 'ClassName.method')",
    )

    # Python-specific
    add_decorators: Optional[list[str]] = Field(
        default=None, description="[Python only] Decorators to add (e.g., ['@cache', '@log'])"
    )
    remove_decorators: Optional[list[str]] = Field(
        default=None,
        description="[Python only] Decorator names to remove (just the name, e.g. ['cache', 'log'])",
    )


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

    # Note: TypeScript CLI does not support modifying type_params, is_async, is_static, is_private, is_protected
    # These parameters are kept for API consistency but won't be applied for TypeScript

    return run_cli_command(cli, args)


# ========== DELETE OPERATIONS ==========


class DeleteFunctionParams(BaseModel):
    """Parameters for delete-function operation.

    IMPORTANT - Language Differences for Finding Methods:

    Python/TypeScript:
        - Use scoped naming: name="ClassName.method_name"
        - Example: name="AuthService.login"

    Go:
        - For functions: name="functionName"
        - For methods: name="MethodName" (just the method name, NOT "StructName.MethodName")
    """

    module: str = Field(description="Path to the source file")
    name: str = Field(description="Function/method name. For Python/TS methods use 'ClassName.method'. For Go methods use just the method name.")
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


class DeleteStructParams(BaseModel):
    """Parameters for delete-struct operation (Go-specific)."""

    module: str = Field(description="Path to the source file")
    name: str = Field(description="Struct name to delete")
    language: Optional[str] = Field(default=None, description="Explicit language override (default: go)")


@mcp.tool
def delete_struct(params: DeleteStructParams) -> dict[str, Any]:
    """Delete a struct from a Go module.

    PERMANENTLY removes the struct definition.
    Note: Methods with this struct as receiver are NOT automatically deleted.

    Examples:
        delete_struct(module="src/models.go", name="DeprecatedModel")
    """
    lang = params.language or "go"
    cli = get_cli(params.module, lang)
    if not cli:
        lang_info = f" (language={params.language})" if params.language else ""
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": f"No CLI available for file: {params.module}{lang_info}. Supported: go",
            },
            "result": None,
        }

    args = ["delete-struct", "-m", params.module, "-n", params.name]

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
    """List all functions in a module or methods in a class/struct.

    IMPORTANT - Language Differences:
        - Python/TypeScript: Functions can be inside classes (methods) or at module level
        - Go: Functions are at package level. Methods have a receiver but are defined outside structs.

    Returns detailed information for each function including:
    - name: Function name
    - line, end_line: Location in file
    - params: List of parameters with name, type
    - return_type: Return type annotation (if any)
    - docstring: Function docstring (if any)
    - is_method: Whether it's a method (has receiver for Go, has class for Python/TS)
    - receiver: (Go only) The method receiver type

    Use Cases:
    - Discover available functions in a module
    - Find methods in a class/struct before modifying
    - Check function signatures
    - Identify functions needing documentation

    Examples:
        # List all functions (including methods)
        list_functions(module="src/auth.py")

        # List methods in a specific class (Python/TypeScript)
        list_functions(module="src/auth.py", class_name="AuthService")

        # List methods for a Go struct
        list_functions(module="src/models.go", class_name="User")

        # Include private functions
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

    IMPORTANT - Language Support:
        - Python: Full support for classes
        - TypeScript: Full support for classes
        - Go: NOT SUPPORTED. Go does NOT have classes. Use 'list_structs' instead.

    For Go files, use list_structs:
        list_structs(module="src/models.go")

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
def list_structs(params: QueryParams) -> dict[str, Any]:
    """List all structs in a Go module.

    IMPORTANT - Go Only:
        - Go uses structs instead of classes
        - Python/TypeScript: use 'list_classes' instead

    Returns detailed information for each struct including:
    - name: Struct name
    - line, end_line: Location in file
    - fields: List of field definitions
    - docstring: Struct docstring (if any)
    - exported: Whether the struct is exported (PascalCase)

    Examples:
        # List all structs in a module
        list_structs(module="src/models.go")

        # Include unexported structs (lowercase names)
        list_structs(module="src/internal.go", include_private=True)
    """
    lang = params.language or "go"
    cli = get_cli(params.module, lang)
    if not cli:
        lang_info = f" (language={params.language})" if params.language else ""
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": f"No CLI available for file: {params.module}{lang_info}. Supported: go",
            },
            "result": None,
        }

    args = ["list-structs", "-m", params.module]

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


@mcp.tool
def list_interfaces(params: QueryParams) -> dict[str, Any]:
    """List all interfaces in a TypeScript module.

    TypeScript-only operation. Python doesn't have native interfaces.

    Returns detailed information for each interface including:
    - name: Interface name
    - line, end_line: Location in file
    - extends: List of extended interfaces
    - properties: List of property definitions
    - type_params: Generic type parameters

    Examples:
        list_interfaces(module="src/types.ts")
        list_interfaces(module="src/api.ts", include_private=True)
    """
    success, cli, error = check_capability_or_error(params.module, params.language, "list_interfaces")
    if not success:
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_OPERATION",
                "message": error,
            },
            "result": None,
        }

    assert cli is not None  # Type guard - cli is guaranteed non-None when success is True

    args = ["list-interfaces", "-m", params.module]

    if params.include_private:
        args.append("--include-private")

    return run_cli_command(cli, args)


@mcp.tool
def list_enums(params: QueryParams) -> dict[str, Any]:
    """List all enums in a TypeScript module.

    TypeScript-only operation. Python uses Enum class instead.

    Returns detailed information for each enum including:
    - name: Enum name
    - line, end_line: Location in file
    - members: List of member names and values
    - is_const: Whether it's a const enum

    Examples:
        list_enums(module="src/types.ts")
        list_enums(module="src/constants.ts")
    """
    success, cli, error = check_capability_or_error(params.module, params.language, "list_enums")
    if not success:
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_OPERATION",
                "message": error,
            },
            "result": None,
        }

    assert cli is not None  # Type guard - cli is guaranteed non-None when success is True

    args = ["list-enums", "-m", params.module]

    return run_cli_command(cli, args)


@mcp.tool
def list_type_aliases(params: QueryParams) -> dict[str, Any]:
    """List all type aliases in a TypeScript module.

    TypeScript-only operation. Python uses TypeAlias or type hints directly.

    Returns detailed information for each type alias including:
    - name: Type alias name
    - line, end_line: Location in file
    - type_definition: The aliased type
    - type_params: Generic type parameters

    Examples:
        list_type_aliases(module="src/types.ts")
        list_type_aliases(module="src/models.ts")
    """
    success, cli, error = check_capability_or_error(params.module, params.language, "list_type_aliases")
    if not success:
        return {
            "success": False,
            "error": {
                "code": "UNSUPPORTED_OPERATION",
                "message": error,
            },
            "result": None,
        }

    assert cli is not None  # Type guard - cli is guaranteed non-None when success is True

    args = ["list-type-aliases", "-m", params.module]

    return run_cli_command(cli, args)


@mcp.tool
def list_variables(params: QueryParams) -> dict[str, Any]:
    """List all variables in a module.

    Returns detailed information for each variable including:
    - name: Variable name
    - line: Line number
    - var_type: Type annotation (if any)
    - value: Initial value (if any)
    - scope: 'module' or class name if class variable

    Examples:
        list_variables(module="src/config.py")
        list_variables(module="src/constants.ts")
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

    args = ["list-variables", "-m", params.module]

    if params.include_private:
        args.append("--include-private")

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


class GetCapabilitiesParams(BaseModel):
    """Parameters for get-language-capabilities operation."""

    language: Optional[str] = Field(
        default=None,
        description="Language name to query (python, typescript, go, rust). If None, returns all languages.",
    )


@mcp.tool
def get_language_capabilities(params: GetCapabilitiesParams) -> dict[str, Any]:
    """Get supported operations for each programming language.

    This tool shows which AST operations are supported by each language.
    Use this to check if an operation is available before calling it,
    avoiding errors from unsupported operations.

    Returns:
        - capabilities: Dict mapping language names to their supported operations
        - For a specific language: returns only that language's capabilities

    Operation Categories:
        INSERT operations:
            - insert_function: Add functions/methods
            - insert_class: Add classes
            - insert_import: Add import statements
            - insert_variable: Add variables (module or class level)
            - insert_interface: Add interfaces (TypeScript only)
            - insert_type_alias: Add type aliases (TypeScript only)
            - insert_enum: Add enums (TypeScript only)
            - insert_namespace: Add namespaces (TypeScript only)

        UPDATE operations:
            - update_function: Modify function body, params, decorators

        DELETE operations:
            - delete_function: Remove functions
            - delete_class: Remove classes
            - delete_variable: Remove variables
            - delete_interface: Remove interfaces (TypeScript only)
            - delete_enum: Remove enums (TypeScript only)
            - delete_type_alias: Remove type aliases (TypeScript only)

        QUERY operations:
            - list_functions: List all functions/methods
            - list_classes: List all classes
            - list_imports: List all imports
            - list_variables: List all variables
            - list_interfaces: List interfaces (TypeScript only)
            - list_enums: List enums (TypeScript only)
            - list_type_aliases: List type aliases (TypeScript only)
            - show_symbol: Display symbol with context
            - find_symbol: Find symbol location

        UTILITY operations:
            - rename_symbol: Rename a symbol
            - validate_syntax: Check syntax validity
            - format_code: Format source code
            - batch_operations: Execute multiple operations

    Language-Specific Notes:
        Python:
            - Uses decorators (@property, @staticmethod, etc.)
            - No native interface/type alias/enum constructs
            - Uses modules/packages instead of namespaces

        TypeScript:
            - Full support for interfaces, type aliases, enums, namespaces
            - Has access modifiers: private, protected, public
            - Generic type parameters for functions and classes

        Go:
            - Not yet implemented (coming soon)

        Rust:
            - Not yet implemented (coming soon)

    Examples:
        # Get all language capabilities
        get_language_capabilities()

        # Check TypeScript-specific capabilities
        get_language_capabilities(language="typescript")

        # Check if Python supports interfaces (it doesn't)
        get_language_capabilities(language="python")
    """
    if params.language:
        lang = params.language.lower()
        if lang not in LANGUAGE_CAPABILITIES:
            return {
                "success": False,
                "error": {
                    "code": "UNKNOWN_LANGUAGE",
                    "message": f"Unknown language: {params.language}. Supported: python, typescript, go, rust",
                },
                "result": None,
            }
        return {
            "success": True,
            "error": None,
            "result": {
                "language": lang,
                "capabilities": LANGUAGE_CAPABILITIES[lang],
                "supported_operations": [op for op, supported in LANGUAGE_CAPABILITIES[lang].items() if supported],
                "unsupported_operations": [op for op, supported in LANGUAGE_CAPABILITIES[lang].items() if not supported],
            },
        }

    return {
        "success": True,
        "error": None,
        "result": {
            "languages": list(LANGUAGE_CAPABILITIES.keys()),
            "capabilities": LANGUAGE_CAPABILITIES,
        },
    }


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

    Subcommands:
    - install-ts: Install bundled ast-ts TypeScript CLI
    - install-go: Install bundled ast-go Go CLI (requires Go toolchain)

    Usage:
        ast-workers-mcp                    # stdio mode (default)
        ast-workers-mcp --transport stdio  # stdio mode
        ast-workers-mcp --transport http   # HTTP mode on default port
        ast-workers-mcp install-ts         # Install ast-ts CLI
        ast-workers-mcp install-ts --uninstall  # Uninstall ast-ts CLI
        ast-workers-mcp install-go         # Install ast-go CLI
        ast-workers-mcp install-go --uninstall  # Uninstall ast-go CLI
    """
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="AST Workers MCP Server - Language-aware code manipulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Install-ts subcommand
    install_ts_parser = subparsers.add_parser(
        "install-ts", help="Install bundled ast-ts TypeScript CLI"
    )
    install_ts_parser.add_argument(
        "--uninstall", "-u", action="store_true", help="Uninstall ast-ts CLI"
    )

    # Install-go subcommand
    install_go_parser = subparsers.add_parser(
        "install-go", help="Install bundled ast-go Go CLI (requires Go toolchain)"
    )
    install_go_parser.add_argument(
        "--uninstall", "-u", action="store_true", help="Uninstall ast-go CLI"
    )

    # Server options (when no subcommand)
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

    if args.command == "install-ts":
        from ast_mcp.install_ts import install_ts, uninstall_ts

        if args.uninstall:
            sys.exit(uninstall_ts())
        else:
            sys.exit(install_ts())
    elif args.command == "install-go":
        from ast_mcp.install_go import install_go, uninstall_go

        if args.uninstall:
            sys.exit(uninstall_go())
        else:
            sys.exit(install_go())
    elif args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport in ("http", "sse"):
        mcp.run(transport="sse", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
