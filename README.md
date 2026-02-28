# AST Workers

[中文文档](README_zh.md)

Missing context when modifying files? Incorrect line numbers? Code chaos caused by file modifications? **AST Workers** are here to help!

Based on AST (Abstract Syntax Tree) structure, we provide code query, insertion, deletion, and modification operations that guarantee syntax correctness and avoid anomalies caused by traditional text-based file modifications.

## Why AST Workers?

| Traditional File Modification | AST Workers |
|------------------------------|-------------|
| Text replacement, prone to mismatches | AST-level precision targeting |
| Manual indentation and formatting | Automatic formatting |
| May break syntax | Guaranteed valid syntax |
| Requires extensive context | Declarative and concise |

## Architecture

```
┌─────────────────────────────────────────────┐
│           ast-workers-mcp                    │
│         (FastMCP Server)                     │
│    Route → subprocess → Parse JSON           │
└──────────────────┬──────────────────────────┘
                   │
    ┌──────────────┼──────────────┬─────────────┐
    ▼              ▼              ▼             ▼
┌───────┐   ┌──────────┐   ┌─────────┐   ┌─────────┐
│ast-py │   │ast-ts    │   │ast-go   │   │ast-rust │
│ ✅    │   │ Planned  │   │ Planned │   │ Planned │
└───────┘   └──────────┘   └─────────┘   └─────────┘
  .py        .ts/.tsx       .go          .rs
```

Each language uses its own AST library and CLI tool, connected via subprocess. The MCP server routes requests based on file extension or explicit language parameter.

## Installation

```bash
# Install the MCP server
pip install ast-workers-mcp

# Install Python AST CLI (required for .py files)
pip install ast-workers-py
```

## Usage

### MCP Server

```bash
# stdio mode (default, for MCP clients like Claude Desktop)
ast-workers-mcp

# HTTP/SSE mode
ast-workers-mcp --transport http --port 8080
```

### CLI Usage (ast-py)

```bash
# Insert a function
ast-py insert-function -m src/auth.py -n validate_token -p "token:str" -r bool -b "return len(token) > 10"

# Insert a method into a class
ast-py insert-function -m src/auth.py -c AuthService -n check_permissions -p "user:User, action:str" -r bool

# Update function signature
ast-py update-function -m src/auth.py -c AuthService -n login -p "self, user_id:int" -r "Optional[User]"

# Show symbol with context
ast-py show -m src/auth.py -n AuthService.login

# Batch operations via JSON
ast-py batch -m src/auth.py --json ops.json
```

### Available Tools

| Tool | Description |
|------|-------------|
| `insert_function` | Insert a function/method into a module or class |
| `insert_class` | Insert a class into a module |
| `insert_import` | Insert an import statement |
| `insert_class_variable` | Insert a class variable |
| `update_function` | Update a function's body, params, decorators, etc. |
| `delete_function` | Delete a function from a module or class |
| `delete_class` | Delete a class from a module |
| `rename_symbol` | Rename a symbol (function/class/variable) |
| `list_functions` | List functions in a module or class |
| `list_classes` | List classes in a module |
| `list_imports` | List imports in a module |
| `find_symbol` | Find a symbol's location and type |
| `show_symbol` | Show a symbol with surrounding context |
| `validate_syntax` | Validate syntax of a module |
| `format_code` | Format code using formatters (black, etc.) |
| `batch_operations` | Execute multiple operations in batch |
| `list_supported_languages` | List supported languages and CLI status |
| `get_tools_info` | Get all available tools and their schemas |

### Key Features

#### Scoped Naming Convention

Use dot notation to target nested symbols:

```python
# Module-level function
show_symbol(params={"module": "src/auth.py", "name": "validate_token"})

# Class method
show_symbol(params={"module": "src/auth.py", "name": "AuthService.login"})

# Nested class
show_symbol(params={"module": "src/models.py", "name": "OuterClass.InnerClass"})
```

#### Structured Body Format

For multi-line code with proper indentation, use structured lists:

```python
# String body (simple)
insert_function(params={
    "module": "src/auth.py",
    "name": "validate",
    "body": "return True"
})

# Structured body (multi-line with indentation)
# List items = new lines, Tuples = indented blocks
insert_function(params={
    "module": "src/auth.py",
    "name": "process",
    "body": [
        "if condition:",
        ("do_first()", "do_second()"),
        "return result"
    ]
})
```

#### Update Function Signature

Replace entire function signature with `params`:

```python
update_function(params={
    "module": "src/auth.py",
    "name": "AuthService.login",
    "params": "self, user_id: int, timeout: int = 30"
})
```

### Examples

```python
# Insert a function
insert_function(params={
    "module": "src/auth.py",
    "name": "validate_token",
    "params": "token: str, expiry: int = 3600",
    "return_type": "bool",
    "body": "return len(token) > 10"
})

# Insert with explicit language (for files without standard extension)
insert_function(params={
    "module": "src/auth",
    "name": "validate",
    "language": "python"
})

# Batch operations
batch_operations(params={
    "module": "src/auth.py",
    "operations": [
        {"op": "insert-import", "from": "typing", "name": "Optional"},
        {"op": "insert-function", "name": "validate", "params": "token: str", "body": "return bool(token)"}
    ]
})

# Query functions
list_functions(params={"module": "src/auth.py"})
list_classes(params={"module": "src/models.py"})

# Show symbol with context
show_symbol(params={"module": "src/auth.py", "name": "AuthService.login"})
```

## Supported Languages

| Language | CLI | Status |
|----------|-----|--------|
| Python | `ast-py` | ✅ Ready |
| TypeScript/JavaScript | `ast-ts` | 📋 Planned |
| Go | `ast-go` | 📋 Planned |
| Rust | `ast-rust` | 📋 Planned |

## Project Structure

```
AST-workers/
├── pyproject.toml      # Project configuration
├── ast_mcp/            # MCP Server
│   ├── __init__.py
│   └── server.py
├── core/
│   └── python/         # Python AST CLI (ast-py)
│       └── ast_py/
├── docs/
│   └── JSON_SPEC.md    # JSON specification
└── tests/
```

## JSON Response Format

All operations return a unified JSON format:

```json
{
    "success": true,
    "error": null,
    "result": {
        "operation": "insert_function",
        "target": {"module": "test.py", "function": "greet"},
        "modified": true,
        "location": {"line": 32}
    }
}
```

## License

Apache 2.0
