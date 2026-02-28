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
pip install -e .

# Install Python AST CLI (required for .py files)
pip install -e ./core/python
```

## Usage

### MCP Server

```bash
# stdio mode (default, for MCP clients like Claude Desktop)
ast-workers-mcp

# HTTP/SSE mode
ast-workers-mcp --transport http --port 8080
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
| `validate_syntax` | Validate syntax of a module |
| `format_code` | Format code using formatters (black, etc.) |
| `batch_operations` | Execute multiple operations in batch |
| `list_supported_languages` | List supported languages and CLI status |
| `get_tools_info` | Get all available tools and their schemas |

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