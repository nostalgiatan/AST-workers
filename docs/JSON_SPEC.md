# AST-CLI JSON 接口规范 v1.0

本文档定义了所有 AST-CLI 工具的统一 JSON 接口规范，适用于所有语言实现。

## 通用响应结构

### 成功响应
```json
{
  "success": true,
  "error": null,
  "result": {
    "operation": "<操作名称>",
    "target": { ... },
    "modified": true,
    ...
  }
}
```

### 错误响应
```json
{
  "success": false,
  "error": {
    "code": "<错误代码>",
    "message": "<错误描述>",
    "details": { ... }
  },
  "result": null
}
```

### 错误代码

| 代码 | 说明 |
|------|------|
| `FILE_NOT_FOUND` | 文件不存在 |
| `SYMBOL_NOT_FOUND` | 符号未找到 |
| `CLASS_NOT_FOUND` | 类未找到 |
| `FUNCTION_NOT_FOUND` | 函数未找到 |
| `SYNTAX_ERROR` | 语法错误 |
| `INVALID_PARAMS` | 参数无效 |
| `DUPLICATE_SYMBOL` | 符号已存在 |
| `INTERNAL_ERROR` | 内部错误 |

---

## 批量操作

### 输入结构
```json
{
  "op": "<操作类型>",
  ...
}
```

### 支持的操作类型

| op 值 | 别名 | 说明 |
|-------|------|------|
| `insert-function` | `if` | 插入函数 |
| `update-function` | `uf` | 修改函数 |
| `delete-function` | `df` | 删除函数 |
| `insert-class` | `ic` | 插入类 |
| `delete-class` | `dc` | 删除类 |
| `insert-class-variable` | `icv` | 插入类变量 |
| `insert-slots` | `is` | 插入 __slots__ |
| `insert-dunder-all` | `iall` | 插入 __all__ |
| `insert-import` | `ii` | 插入导入 |
| `rename-symbol` | `rn` | 重命名符号 |

---

## 操作详情

### 1. insert-function / if

**输入字段：**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `op` | string | ✅ | `insert-function` 或 `if` |
| `name` | string | ✅ | 函数名 |
| `params` | string | ❌ | 参数字符串，如 `"x:int, y:int=10"` |
| `body` | string | ❌ | 函数体（支持多行） |
| `return_type` | string | ❌ | 返回类型 |
| `decorators` | string | ❌ | 装饰器列表，逗号分隔 |
| `docstring` | string | ❌ | 文档字符串 |
| `is_async` | boolean | ❌ | 是否异步函数 |
| `class` | string | ❌ | 类名（插入方法时使用） |
| `after` | string | ❌ | 插入到此函数之后 |

**参数语法：**
```
positional_only, /, positional_or_keyword, *, keyword_only, *args, **kwargs
```

**示例：**
```json
{
  "op": "insert-function",
  "name": "process",
  "params": "data:dict, /, *, strict:bool=True, **kwargs",
  "return_type": "dict[str, any]",
  "body": "result = {'data': data}\nfor k, v in kwargs.items():\n    result[k] = v\nreturn result",
  "decorators": "@cache(3600)",
  "docstring": "处理数据"
}
```

**输出：**
```json
{
  "success": true,
  "error": null,
  "result": {
    "operation": "insert_function",
    "target": {
      "module": "file.py",
      "class": null,
      "function": "process"
    },
    "modified": true,
    "location": { "line": 42 }
  }
}
```

---

### 2. update-function / uf

**输入字段：**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `op` | string | ✅ | `update-function` 或 `uf` |
| `name` | string | ✅ | 函数名 |
| `class` | string | ❌ | 类名（修改方法时使用） |
| `body` | string | ❌ | 新函数体 |
| `add_params` | string | ❌ | 添加参数 |
| `remove_params` | string | ❌ | 删除参数（逗号分隔） |
| `return_type` | string | ❌ | 新返回类型（空字符串清除） |
| `add_decorators` | string | ❌ | 添加装饰器（逗号分隔） |
| `remove_decorators` | string | ❌ | 删除装饰器（逗号分隔） |
| `docstring` | string | ❌ | 新文档字符串 |

**示例：**
```json
{
  "op": "update-function",
  "name": "process",
  "add_params": "timeout:int=30",
  "remove_params": "deprecated_flag",
  "return_type": "Optional[dict]",
  "add_decorators": "@log_execution",
  "remove_decorators": "old_decorator",
  "docstring": "更新后的描述"
}
```

---

### 3. delete-function / df

**输入字段：**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `op` | string | ✅ | `delete-function` 或 `df` |
| `name` | string | ✅ | 函数名 |
| `class` | string | ❌ | 类名（删除方法时使用） |

**示例：**
```json
{
  "op": "delete-function",
  "name": "old_func"
}
```

---

### 4. insert-class / ic

**输入字段：**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `op` | string | ✅ | `insert-class` 或 `ic` |
| `name` | string | ✅ | 类名 |
| `bases` | string | ❌ | 基类列表（逗号分隔） |
| `decorators` | string | ❌ | 装饰器列表（逗号分隔） |
| `docstring` | string | ❌ | 文档字符串 |
| `class_vars` | string | ❌ | 类变量定义（逗号分隔） |

**示例：**
```json
{
  "op": "insert-class",
  "name": "User",
  "bases": "BaseModel, Serializable",
  "decorators": "@dataclass(frozen=True)",
  "docstring": "用户模型",
  "class_vars": "id:int, name:str, created_at:datetime"
}
```

---

### 5. delete-class / dc

**输入字段：**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `op` | string | ✅ | `delete-class` 或 `dc` |
| `name` | string | ✅ | 类名 |

---

### 6. insert-class-variable / icv

**输入字段：**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `op` | string | ✅ | `insert-class-variable` 或 `icv` |
| `class` | string | ✅ | 类名 |
| `name` | string | ✅ | 变量名 |
| `type` | string | ❌ | 类型注解 |
| `value` | string | ❌ | 初始值 |

**示例：**
```json
{
  "op": "insert-class-variable",
  "class": "UserService",
  "name": "instance_count",
  "type": "int",
  "value": "0"
}
```

---

### 7. insert-slots / is

**输入字段：**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `op` | string | ✅ | `insert-slots` 或 `is` |
| `class` | string | ✅ | 类名 |
| `slots` | array | ✅ | 插槽名列表 |

**示例：**
```json
{
  "op": "insert-slots",
  "class": "User",
  "slots": ["id", "name", "email"]
}
```

---

### 8. insert-dunder-all / iall

**输入字段：**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `op` | string | ✅ | `insert-dunder-all` 或 `iall` |
| `names` | string/array | ✅ | 名称列表 |
| `mode` | string | ❌ | `replace`（默认）或 `append` |

**示例：**
```json
{
  "op": "insert-dunder-all",
  "names": ["UserService", "create_user", "get_user"],
  "mode": "append"
}
```

---

### 9. insert-import / ii

**输入字段：**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `op` | string | ✅ | `insert-import` 或 `ii` |
| `name` | string | ✅ | 导入名称或模块名 |
| `from` | string | ❌ | from 模块名 |
| `alias` | string | ❌ | 别名 (as) |

**示例：**
```json
{
  "op": "insert-import",
  "name": "Optional, List, Dict",
  "from": "typing"
}
```

---

### 10. rename-symbol / rn

**输入字段：**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `op` | string | ✅ | `rename-symbol` 或 `rn` |
| `old` | string | ✅ | 原名称 |
| `new` | string | ✅ | 新名称 |
| `type` | string | ❌ | 符号类型：`function`、`class`、`variable` |

**示例：**
```json
{
  "op": "rename-symbol",
  "old": "old_func",
  "new": "new_func",
  "type": "function"
}
```

---

## 查询操作

### list-functions / lf

**输出：**
```json
{
  "success": true,
  "error": null,
  "result": {
    "operation": "list_functions",
    "target": {
      "module": "file.py",
      "class": null
    },
    "functions": [
      {
        "name": "func_name",
        "line": 10,
        "end_line": 20,
        "is_async": false,
        "is_method": false,
        "params": [
          {
            "name": "x",
            "annotation": "int",
            "default": null,
            "kind": "positional_or_keyword"
          }
        ],
        "return_type": "str",
        "decorators": ["@cache"],
        "docstring": "函数描述"
      }
    ]
  }
}
```

### list-classes / lc

**输出：**
```json
{
  "success": true,
  "error": null,
  "result": {
    "operation": "list_classes",
    "target": {
      "module": "file.py"
    },
    "classes": [
      {
        "name": "ClassName",
        "line": 5,
        "end_line": 50,
        "bases": ["BaseClass"],
        "decorators": ["@dataclass"],
        "methods": ["__init__", "process"],
        "class_vars": ["count", "name"],
        "docstring": "类描述"
      }
    ]
  }
}
```

### list-imports / li

**输出：**
```json
{
  "success": true,
  "error": null,
  "result": {
    "operation": "list_imports",
    "target": {
      "module": "file.py"
    },
    "imports": [
      {
        "type": "from",
        "module": "typing",
        "name": "Optional",
        "alias": null,
        "line": 1
      },
      {
        "type": "import",
        "module": "os",
        "alias": null,
        "line": 2
      }
    ]
  }
}
```

### find-symbol / fs

**输出：**
```json
{
  "success": true,
  "error": null,
  "result": {
    "operation": "find_symbol",
    "target": {
      "module": "file.py",
      "name": "func_name",
      "type": null
    },
    "found": true,
    "symbols": [
      {
        "type": "function",
        "name": "func_name",
        "line": 10,
        "end_line": 20,
        "is_async": false
      }
    ]
  }
}
```

---

## 工具操作

### validate / v

**输出：**
```json
{
  "success": true,
  "error": null,
  "result": {
    "valid": true,
    "error": null,
    "error_line": null,
    "error_column": null,
    "module": "file.py"
  }
}
```

### format / fmt

**输出：**
```json
{
  "success": true,
  "error": null,
  "result": {
    "formatted": "<格式化后的代码>",
    "formatter": "black",
    "success": true,
    "error": null,
    "module": "file.py"
  }
}
```

---

## CLI 使用

### 单命令
```bash
ast-py <command> -m <module> [options]

# 示例
ast-py insert-function -m file.py -n func -p "x:int" -b "return x"
ast-py list-functions -m file.py
```

### 批量操作（JSON字符串）
```bash
ast-py batch -m file.py --ops '[
  {"op": "insert-function", "name": "func1", "body": "pass"},
  {"op": "insert-function", "name": "func2", "body": "pass"}
]'
```

### 批量操作（JSON文件）
```bash
ast-py batch -m file.py --file operations.json
```

### 批量操作错误处理
```bash
# 默认：遇错停止
ast-py batch -m file.py --ops '[...]'

# 继续执行
ast-py batch -m file.py --continue-on-error --ops '[...]'
```

---

## 多语言规范

所有语言的 AST-CLI 实现（ast-py、ast-ts、ast-go、ast-rust）必须遵循此规范：

1. **统一的 JSON 结构** - 输入输出格式一致
2. **统一的操作名称** - op 字段值相同
3. **统一的错误代码** - error.code 值相同
4. **语言特定参数** - 根据语言特性扩展字段

### 语言特定扩展

| 语言 | 扩展字段示例 |
|------|-------------|
| TypeScript | `interface`、`type`、`enum` |
| Go | `receiver`、`exported` |
| Rust | `pub`、`trait`、`impl` |

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2026-02-28 | 初始版本 |
