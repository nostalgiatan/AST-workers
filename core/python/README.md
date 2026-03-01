# ast-workers-py

[中文文档](README_zh.md)

Python AST manipulation CLI tool. Edit Python code at the Abstract Syntax Tree level with guaranteed syntax correctness.

## Installation

```bash
pip install ast-workers-py
```

## Usage

```bash
ast-py <operation> [options]
```

### Operations

| Command | Alias | Description |
|---------|-------|-------------|
| `insert-function` | `if` | Insert a function |
| `update-function` | `uf` | Update a function |
| `insert-class` | `ic` | Insert a class |
| `insert-class-variable` | `icv` | Insert a class variable |
| `insert-slots` | `is` | Insert `__slots__` into a class |
| `insert-dunder-all` | `iall` | Insert or update `__all__` |
| `insert-import` | `ii` | Insert an import statement |
| `list-functions` | `lf` | List functions in a module/class |
| `list-classes` | `lc` | List classes in a module |
| `list-imports` | `li` | List imports in a module |
| `find-symbol` | `fs` | Find a symbol in a module |
| `delete-function` | `df` | Delete a function |
| `delete-class` | `dc` | Delete a class |
| `rename-symbol` | `rn` | Rename a symbol |
| `show` | `s` | Show symbol with context |
| `validate` | `v` | Validate Python syntax |
| `format` | `fmt` | Format Python code |
| `batch` | `b` | Execute multiple operations from JSON |

## Examples

### Query Operations

```bash
# List functions in a module
ast-py list-functions -m src/auth.py

# List methods in a class
ast-py list-functions -m src/auth.py -c AuthService

# List classes in a module
ast-py list-classes -m src/models.py

# Show a symbol with context (supports scoped naming)
ast-py show -m src/auth.py -n AuthService.login

# Find a symbol
ast-py find-symbol -m src/auth.py -n validate_token -t function
```

### Insert Operations

```bash
# Insert a simple function
ast-py insert-function -m src/auth.py -n validate_token -p "token:str" -r bool -b "return len(token) > 10"

# Insert a method into a class
ast-py insert-function -m src/auth.py -c AuthService -n check_permissions -p "user:User, action:str" -r bool

# Insert with advanced parameters
ast-py insert-function -m src/utils.py -n process -p "data, /, strict:bool=True, *, encoding:str='utf-8', **kwargs"

# Insert with decorators
ast-py insert-function -m src/api.py -n get_user -p "user_id:int" -d "@route('/users/<int:user_id>'), @login_required"

# Insert async function
ast-py insert-function -m src/async_ops.py -n fetch_data --is-async -p "url:str" -r "dict"

# Insert with docstring
ast-py insert-function -m src/auth.py -n login -p "user:str, password:str" --docstring "Authenticate user and return session"

# Insert a class
ast-py insert-class -m src/models.py -n User -b "BaseModel" --docstring "User model" --class-vars "id:int, name:str"

# Insert a class variable
ast-py insert-class-variable -m src/models.py -c User -n count -t int -v 0

# Insert __slots__
ast-py insert-slots -m src/models.py -c User --slots id name email

# Insert __all__
ast-py insert-dunder-all -m src/auth.py --names login logout authenticate

# Insert an import
ast-py insert-import -m src/auth.py --from typing --name "Optional, Dict"
```

### Update Operations

```bash
# Update function body
ast-py update-function -m src/auth.py -n validate_token -b "return token is not None"

# Replace entire parameter list
ast-py update-function -m src/auth.py -n login -p "self, user_id:int, timeout:int=30"

# Add parameters
ast-py update-function -m src/auth.py -n login --add-params "remember:bool=False"

# Remove parameters
ast-py update-function -m src/auth.py -n login --remove-params deprecated_param

# Change return type
ast-py update-function -m src/auth.py -n get_user --return-type "Optional[User]"

# Add decorators
ast-py update-function -m src/api.py -n endpoint --add-decorators "@cache(3600)"

# Remove decorators
ast-py update-function -m src/api.py -n endpoint --remove-decorators old_decorator

# Update docstring
ast-py update-function -m src/auth.py -n login --docstring "Authenticate user"
```

### Delete Operations

```bash
# Delete a function
ast-py delete-function -m src/auth.py -n old_function

# Delete a class
ast-py delete-class -m src/models.py -n DeprecatedModel
```

### Rename Operations

```bash
# Rename a function
ast-py rename-symbol -m src/auth.py -o old_name -n new_name -t function

# Rename a class
ast-py rename-symbol -m src/models.py -o OldUser -n User -t class
```

### Utility Operations

```bash
# Validate syntax
ast-py validate -m src/auth.py

# Format code
ast-py format -m src/auth.py

# Batch operations from JSON
ast-py batch -m src/auth.py --json ops.json
```

## Parameter Syntax

The `-p/--params` argument supports full Python parameter syntax:

```
positional, /, pos_or_kw, *, kw_only, **kwargs
```

Examples:
- Basic: `-p "x, y, z"`
- With types: `-p "x:int, y:str, z:float"`
- With defaults: `-p "x:int=0, y:str='hello'"`
- Positional-only: `-p "a, b, /, c, d"` (a, b are positional-only)
- Keyword-only: `-p "*, c, d=1"` (c, d must be keyword args)
- *args/**kwargs: `-p "*args:int, **kwargs:dict"`

## Structured Body Format

For multi-line code with proper indentation, use JSON arrays:

```bash
# Nested lists represent indentation levels
ast-py insert-function -m src/auth.py -n process -p "data:dict" -b '["if data:", ["result = process(data)", "return result"], "return None"]'
```

Result:
```python
def process(data: dict):
    if data:
        result = process(data)
        return result
    return None
```

## Scoped Naming

Use dot notation for nested symbols:

```bash
# Class method
ast-py show -m src/auth.py -n AuthService.login

# Nested class
ast-py show -m src/models.py -n OuterClass.InnerClass
```

## License

Apache 2.0
