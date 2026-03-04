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
│ ✅    │   │ ✅       │   │ ✅      │   │ Planned │
└───────┘   └──────────┘   └─────────┘   └─────────┘
  .py        .ts/.tsx       .go          .rs
             .js/.jsx
```

Each language uses its own AST library and CLI tool, connected via subprocess. The MCP server routes requests based on file extension or explicit language parameter.

## Installation

```bash
# Install the MCP server
pip install ast-workers-mcp

# Install Python AST CLI (required for .py files)
pip install ast-workers-py

# Install TypeScript AST CLI (required for .ts/.tsx/.js/.jsx files)
ast-workers-mcp install-ts

# Install Go AST CLI (required for .go files)
ast-workers-mcp install-go install
```

### Install TypeScript CLI

The TypeScript CLI (`ast-ts`) is bundled with the MCP package. After installing `ast-workers-mcp`:

```bash
# Install ast-ts
ast-workers-mcp install-ts

# Verify installation
ast-ts --help

# Uninstall ast-ts
ast-workers-mcp install-ts --uninstall
```

**Requirements:**
- Node.js 18.0.0 or higher
- npm

### Install Go CLI

The Go CLI (`ast-go`) is compiled from source. After installing `ast-workers-mcp`:

```bash
# Check requirements and installation status
ast-workers-mcp install-go check

# Install ast-go (requires Go toolchain)
ast-workers-mcp install-go install

# Verify installation
ast-go version

# Uninstall ast-go
ast-workers-mcp install-go uninstall
```

**Requirements:**
- Go 1.18+ (for generic type support)
- Go toolchain must be installed on your system

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

### CLI Usage (ast-ts)

```bash
# Insert a function
ast-ts insert-function -m src/auth.ts -n validateToken -p "token:string" -r boolean -b "return token.length > 10"

# Insert a method into a class
ast-ts insert-function -m src/auth.ts -c AuthService -n checkPermissions -p "user:User, action:string" -r boolean

# Insert an interface
ast-ts insert-interface -m src/types.ts -n User -p "id:string, name:string, email:string"

# Insert a type alias
ast-ts insert-type-alias -m src/types.ts -n UserId -t "string | number"

# Insert an enum
ast-ts insert-enum -m src/types.ts -n Status -m "Pending, Active, Inactive"

# Show symbol with context
ast-ts show -m src/auth.ts -n AuthService.login

# List functions
ast-ts list-functions -m src/auth.ts
```

### CLI Usage (ast-go)

```bash
# Insert a function
ast-go insert-function -m auth.go -n ValidateToken -p "token string" -r bool -b "return len(token) > 10"

# Insert a method with receiver
ast-go insert-function -m auth.go -n CheckPermissions --receiver "u *User" -p "action string" -r bool -b "return u.isAdmin()"

# Insert a struct
ast-go insert-struct -m models.go -n User -f "ID:int, Name:string, Email:string"

# Insert an import
ast-go insert-import -m auth.go -p "github.com/example/pkg"

# Show symbol with context
ast-go show -m auth.go -n User.CheckPermissions

# List functions with type information
ast-go list-functions -m auth.go

# List structs with methods
ast-go list-structs -m models.go --with-methods

# Validate syntax
ast-go validate -m auth.go
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

### TypeScript-Specific Tools

| Tool | Description |
|------|-------------|
| `insert_interface` | Insert a TypeScript interface |
| `insert_type_alias` | Insert a TypeScript type alias |
| `insert_enum` | Insert a TypeScript enum |
| `list_interfaces` | List interfaces in a TypeScript module |
| `list_enums` | List enums in a TypeScript module |
| `list_type_aliases` | List type aliases in a TypeScript module |

### Go-Specific Tools

| Tool | Description |
|------|-------------|
| `insert_struct` | Insert a Go struct |
| `list_structs` | List structs in a Go module |
| `delete_struct` | Delete a struct from a module |

**Note:** Go uses **receiver** parameter for methods instead of **class_name**:

```python
# Go method (use receiver)
insert_function(params={
    "module": "auth.go",
    "name": "CheckPermissions",
    "receiver": "u *User",  # Go method receiver
    "params": "action string",
    "return_type": "bool"
})

# Python/TypeScript method (use class_name)
insert_function(params={
    "module": "auth.py",
    "name": "check_permissions",
    "class_name": "AuthService",  # Python/TS class
    "params": "action: str"
})
```

### Language Capabilities

Check which operations are supported for each language:

```python
get_language_capabilities(params={"language": "typescript"})
```

## Key Features

### Scoped Naming Convention

Use dot notation to target nested symbols:

```python
# Module-level function
show_symbol(params={"module": "src/auth.py", "name": "validate_token"})

# Class method
show_symbol(params={"module": "src/auth.py", "name": "AuthService.login"})

# Nested class
show_symbol(params={"module": "src/models.py", "name": "OuterClass.InnerClass"})
```

### Structured Body Format

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

### Update Function Signature

Replace entire function signature with `params`:

```python
update_function(params={
    "module": "src/auth.py",
    "name": "AuthService.login",
    "params": "self, user_id: int, timeout: int = 30"
})
```

## Examples

### Python

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

### TypeScript

```python
# Insert a function
insert_function(params={
    "module": "src/auth.ts",
    "name": "validateToken",
    "params": "token: string, expiry?: number",
    "return_type": "boolean",
    "body": "return token.length > 10"
})

# Insert an interface
insert_interface(params={
    "module": "src/types.ts",
    "name": "User",
    "properties": "id: string, name: string, email?: string"
})

# Insert a type alias
insert_type_alias(params={
    "module": "src/types.ts",
    "name": "UserId",
    "type_definition": "string | number"
})

# Insert an enum
insert_enum(params={
    "module": "src/types.ts",
    "name": "Status",
    "members": "Pending, Active, Inactive"
})

# Insert a class with generic type parameters
insert_class(params={
    "module": "src/models.ts",
    "name": "Repository",
    "type_params": "T extends Entity",
    "implements": "Serializable, Comparable"
})

# List interfaces
list_interfaces(params={"module": "src/types.ts"})
```

### Go

```python
# Insert a function
insert_function(params={
    "module": "auth.go",
    "name": "ValidateToken",
    "params": "token string, expiry int",
    "return_type": "bool",
    "body": "return len(token) > 10"
})

# Insert a method with receiver
insert_function(params={
    "module": "auth.go",
    "name": "CheckPermissions",
    "receiver": "u *User",  # Go uses receiver for methods
    "params": "action string",
    "return_type": "bool",
    "body": "return u.isAdmin()"
})

# Insert a struct
insert_struct(params={
    "module": "models.go",
    "name": "User",
    "fields": "ID:int, Name:string, Email:string"
})

# Insert an import
insert_import(params={
    "module": "auth.go",
    "name": "fmt"
})

# Query structs with methods
list_structs(params={"module": "models.go"})

# Show symbol with context
show_symbol(params={"module": "auth.go", "name": "User.CheckPermissions"})
```

## Supported Languages

| Language | CLI | Status | Requirements |
|----------|-----|--------|--------------|
| Python | `ast-py` | ✅ Ready | `pip install ast-workers-py` |
| TypeScript/JavaScript | `ast-ts` | ✅ Ready | Node.js 18+ |
| Go | `ast-go` | ✅ Ready | Go 1.18+ |
| Rust | `ast-rust` | 📋 Planned | - |

## Project Structure

```
AST-workers/
├── pyproject.toml      # Project configuration
├── ast_mcp/            # MCP Server
│   ├── __init__.py
│   ├── server.py       # FastMCP server
│   ├── install_ts.py   # ast-ts installer
│   ├── install_go.py   # ast-go installer
│   └── ast-ts-dist.tar.gz  # Bundled TypeScript CLI
├── core/
│   ├── python/         # Python AST CLI (ast-py)
│   │   └── ast_py/
│   ├── nodejs-ts/      # TypeScript AST CLI (ast-ts)
│   │   └── src/
│   └── go/             # Go AST CLI (ast-go)
│       └── cmd/
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