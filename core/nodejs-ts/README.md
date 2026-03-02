# AST Workers TS

TypeScript AST manipulation CLI tool using ts-morph.

## Installation

```bash
npm install -g ast-workers-ts
```

## Usage

```bash
ast-ts --help
```

### Commands

| Command | Alias | Description |
|---------|-------|-------------|
| `insert-function` | `if` | Insert a function |
| `insert-class` | `ic` | Insert a class |
| `insert-interface` | `ii` | Insert an interface |
| `insert-type-alias` | `ita` | Insert a type alias |
| `insert-enum` | `ie` | Insert an enum |
| `insert-variable` | `iv` | Insert a variable |
| `insert-import` | `im` | Insert an import |
| `update-function` | `uf` | Update a function |
| `delete-function` | `df` | Delete a function |
| `delete-class` | `dc` | Delete a class |
| `list-functions` | `lf` | List functions |
| `list-classes` | `lc` | List classes |
| `list-interfaces` | `li` | List interfaces |
| `show` | `s` | Show symbol with context |

### Examples

```bash
# Insert a function
ast-ts insert-function -m src/utils.ts -n greet -p "name: string" -r "string" -b 'return `Hello, ${name}!`'

# Insert a class with generics
ast-ts insert-class -m src/models.ts -n Repository -t "T" -i "Serializable"

# Insert an interface
ast-ts insert-interface -m src/types.ts -n User --properties "id:string, name:string, email?:string"

# List all classes
ast-ts list-classes -m src/models.ts

# Show a symbol
ast-ts show -m src/models.ts -n User
```

## License

Apache-2.0
