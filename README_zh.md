# AST Workers

[English](README.md)

修改文件时上下文丢失？行号不准确？文件修改导致代码混乱？**AST Workers** 来帮你！

基于 AST（抽象语法树）结构，我们提供代码查询、插入、删除和修改操作，保证语法正确性，避免传统基于文本的文件修改带来的问题。

## 为什么选择 AST Workers？

| 传统文件修改 | AST Workers |
|------------------------------|-------------|
| 文本替换，容易不匹配 | AST 级别精确定位 |
| 手动缩进和格式化 | 自动格式化 |
| 可能破坏语法 | 保证语法有效 |
| 需要大量上下文 | 声明式且简洁 |

## 架构

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
│ ✅    │   │ ✅       │   │ ✅      │   │ 计划中  │
└───────┘   └──────────┘   └─────────┘   └─────────┘
  .py        .ts/.tsx       .go          .rs
             .js/.jsx
```

每种语言使用自己的 AST 库和 CLI 工具，通过 subprocess 连接。MCP 服务器根据文件扩展名或显式语言参数路由请求。

## 安装

```bash
# 安装 MCP 服务器
pip install ast-workers-mcp

# 安装 Python AST CLI（.py 文件需要）
pip install ast-workers-py

# 安装 TypeScript AST CLI（.ts/.tsx/.js/.jsx 文件需要）
ast-workers-mcp install-ts

# 安装 Go AST CLI（.go 文件需要）
ast-workers-mcp install-go install
```

### 安装 TypeScript CLI

TypeScript CLI（`ast-ts`）已打包在 MCP 包中。安装 `ast-workers-mcp` 后：

```bash
# 安装 ast-ts
ast-workers-mcp install-ts

# 验证安装
ast-ts --help

# 卸载 ast-ts
ast-workers-mcp install-ts --uninstall
```

**系统要求：**
- Node.js 18.0.0 或更高版本
- npm

### 安装 Go CLI

Go CLI（`ast-go`）从源码编译。安装 `ast-workers-mcp` 后：

```bash
# 检查依赖和安装状态
ast-workers-mcp install-go check

# 安装 ast-go（需要 Go 工具链）
ast-workers-mcp install-go install

# 验证安装
ast-go version

# 卸载 ast-go
ast-workers-mcp install-go uninstall
```

**系统要求：**
- Go 1.18+（支持泛型类型）
- 系统需要安装 Go 工具链

## 使用方法

### MCP 服务器

```bash
# stdio 模式（默认，用于 Claude Desktop 等 MCP 客户端）
ast-workers-mcp

# HTTP/SSE 模式
ast-workers-mcp --transport http --port 8080
```

### CLI 使用 (ast-py)

```bash
# 插入函数
ast-py insert-function -m src/auth.py -n validate_token -p "token:str" -r bool -b "return len(token) > 10"

# 向类中插入方法
ast-py insert-function -m src/auth.py -c AuthService -n check_permissions -p "user:User, action:str" -r bool

# 更新函数签名
ast-py update-function -m src/auth.py -c AuthService -n login -p "self, user_id:int" -r "Optional[User]"

# 查看符号上下文
ast-py show -m src/auth.py -n AuthService.login

# 通过 JSON 批量操作
ast-py batch -m src/auth.py --json ops.json
```

### CLI 使用 (ast-ts)

```bash
# 插入函数
ast-ts insert-function -m src/auth.ts -n validateToken -p "token:string" -r boolean -b "return token.length > 10"

# 向类中插入方法
ast-ts insert-function -m src/auth.ts -c AuthService -n checkPermissions -p "user:User, action:string" -r boolean

# 插入接口
ast-ts insert-interface -m src/types.ts -n User -p "id:string, name:string, email:string"

# 插入类型别名
ast-ts insert-type-alias -m src/types.ts -n UserId -t "string | number"

# 插入枚举
ast-ts insert-enum -m src/types.ts -n Status -m "Pending, Active, Inactive"

# 查看符号上下文
ast-ts show -m src/auth.ts -n AuthService.login

# 列出函数
ast-ts list-functions -m src/auth.ts
```

### CLI 使用 (ast-go)

```bash
# 插入函数
ast-go insert-function -m auth.go -n ValidateToken -p "token string" -r bool -b "return len(token) > 10"

# 插入带接收者的方法
ast-go insert-function -m auth.go -n CheckPermissions --receiver "u *User" -p "action string" -r bool -b "return u.isAdmin()"

# 插入结构体
ast-go insert-struct -m models.go -n User -f "ID:int, Name:string, Email:string"

# 插入导入
ast-go insert-import -m auth.go -p "github.com/example/pkg"

# 查看符号上下文
ast-go show -m auth.go -n User.CheckPermissions

# 列出函数（带类型信息）
ast-go list-functions -m auth.go

# 列出结构体（带方法）
ast-go list-structs -m models.go --with-methods

# 验证语法
ast-go validate -m auth.go
```

### 可用工具

| 工具 | 描述 |
|------|------|
| `insert_function` | 向模块或类中插入函数/方法 |
| `insert_class` | 向模块中插入类 |
| `insert_import` | 插入导入语句 |
| `insert_class_variable` | 插入类变量 |
| `update_function` | 更新函数的 body、params、decorators 等 |
| `delete_function` | 从模块或类中删除函数 |
| `delete_class` | 从模块中删除类 |
| `rename_symbol` | 重命名符号（函数/类/变量） |
| `list_functions` | 列出模块或类中的函数 |
| `list_classes` | 列出模块中的类 |
| `list_imports` | 列出模块中的导入 |
| `find_symbol` | 查找符号的位置和类型 |
| `show_symbol` | 显示符号及其上下文代码 |
| `validate_syntax` | 验证模块语法 |
| `format_code` | 使用格式化工具格式化代码 |
| `batch_operations` | 批量执行多个操作 |
| `list_supported_languages` | 列出支持的语言和 CLI 状态 |
| `get_tools_info` | 获取所有可用工具及其 schema |

### TypeScript 专用工具

| 工具 | 描述 |
|------|------|
| `insert_interface` | 插入 TypeScript 接口 |
| `insert_type_alias` | 插入 TypeScript 类型别名 |
| `insert_enum` | 插入 TypeScript 枚举 |
| `list_interfaces` | 列出 TypeScript 模块中的接口 |
| `list_enums` | 列出 TypeScript 模块中的枚举 |
| `list_type_aliases` | 列出 TypeScript 模块中的类型别名 |

### Go 专用工具

| 工具 | 描述 |
|------|------|
| `insert_struct` | 插入 Go 结构体 |
| `list_structs` | 列出 Go 模块中的结构体 |
| `delete_struct` | 从模块中删除结构体 |

**注意：** Go 使用 **receiver** 参数来定义方法，而不是 **class_name**：

```python
# Go 方法（使用 receiver）
insert_function(params={
    "module": "auth.go",
    "name": "CheckPermissions",
    "receiver": "u *User",  # Go 方法接收者
    "params": "action string",
    "return_type": "bool"
})

# Python/TypeScript 方法（使用 class_name）
insert_function(params={
    "module": "auth.py",
    "name": "check_permissions",
    "class_name": "AuthService",  # Python/TS 类名
    "params": "action: str"
})
```

### 语言能力查询

查看每种语言支持的操作：

```python
get_language_capabilities(params={"language": "go"})
```

## 核心特性

### 作用域式命名

使用点号定位嵌套符号：

```python
# 模块级函数
show_symbol(params={"module": "src/auth.py", "name": "validate_token"})

# 类方法
show_symbol(params={"module": "src/auth.py", "name": "AuthService.login"})

# 嵌套类
show_symbol(params={"module": "src/models.py", "name": "OuterClass.InnerClass"})
```

#### 结构化 Body 格式

多行代码需要正确的缩进时，使用结构化列表：

```python
# 字符串 body（简单）
insert_function(params={
    "module": "src/auth.py",
    "name": "validate",
    "body": "return True"
})

# 结构化 body（多行带缩进）
# 列表项 = 新行，元组 = 缩进块
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

#### 更新函数签名

使用 `params` 替换整个函数签名：

```python
update_function(params={
    "module": "src/auth.py",
    "name": "AuthService.login",
    "params": "self, user_id: int, timeout: int = 30"
})
```

## 示例

### Python

```python
# 插入函数
insert_function(params={
    "module": "src/auth.py",
    "name": "validate_token",
    "params": "token: str, expiry: int = 3600",
    "return_type": "bool",
    "body": "return len(token) > 10"
})

# 显式指定语言（用于非标准扩展名文件）
insert_function(params={
    "module": "src/auth",
    "name": "validate",
    "language": "python"
})

# 批量操作
batch_operations(params={
    "module": "src/auth.py",
    "operations": [
        {"op": "insert-import", "from": "typing", "name": "Optional"},
        {"op": "insert-function", "name": "validate", "params": "token: str", "body": "return bool(token)"}
    ]
})

# 查询函数
list_functions(params={"module": "src/auth.py"})
list_classes(params={"module": "src/models.py"})

# 显示符号上下文
show_symbol(params={"module": "src/auth.py", "name": "AuthService.login"})
```

### TypeScript

```python
# 插入函数
insert_function(params={
    "module": "src/auth.ts",
    "name": "validateToken",
    "params": "token: string, expiry?: number",
    "return_type": "boolean",
    "body": "return token.length > 10"
})

# 插入接口
insert_interface(params={
    "module": "src/types.ts",
    "name": "User",
    "properties": "id: string, name: string, email?: string"
})

# 插入类型别名
insert_type_alias(params={
    "module": "src/types.ts",
    "name": "UserId",
    "type_definition": "string | number"
})

# 插入枚举
insert_enum(params={
    "module": "src/types.ts",
    "name": "Status",
    "members": "Pending, Active, Inactive"
})

# 插入带泛型参数的类
insert_class(params={
    "module": "src/models.ts",
    "name": "Repository",
    "type_params": "T extends Entity",
    "implements": "Serializable, Comparable"
})

# 列出接口
list_interfaces(params={"module": "src/types.ts"})
```

### Go

```python
# 插入函数
insert_function(params={
    "module": "auth.go",
    "name": "ValidateToken",
    "params": "token string, expiry int",
    "return_type": "bool",
    "body": "return len(token) > 10"
})

# 插入带接收者的方法
insert_function(params={
    "module": "auth.go",
    "name": "CheckPermissions",
    "receiver": "u *User",  # Go 使用 receiver 定义方法
    "params": "action string",
    "return_type": "bool",
    "body": "return u.isAdmin()"
})

# 插入结构体
insert_struct(params={
    "module": "models.go",
    "name": "User",
    "fields": "ID:int, Name:string, Email:string"
})

# 插入导入
insert_import(params={
    "module": "auth.go",
    "name": "fmt"
})

# 查询结构体（带方法）
list_structs(params={"module": "models.go"})

# 显示符号上下文
show_symbol(params={"module": "auth.go", "name": "User.CheckPermissions"})
```

## 支持的语言

| 语言 | CLI | 状态 | 系统要求 |
|----------|-----|------|----------|
| Python | `ast-py` | ✅ 就绪 | `pip install ast-workers-py` |
| TypeScript/JavaScript | `ast-ts` | ✅ 就绪 | Node.js 18+ |
| Go | `ast-go` | ✅ 就绪 | Go 1.18+ |
| Rust | `ast-rust` | 📋 计划中 | - |

## 项目结构

```
AST-workers/
├── pyproject.toml      # 项目配置
├── ast_mcp/            # MCP 服务器
│   ├── __init__.py
│   ├── server.py       # FastMCP 服务器
│   ├── install_ts.py   # ast-ts 安装器
│   ├── install_go.py   # ast-go 安装器
│   └── ast-ts-dist.tar.gz  # 打包的 TypeScript CLI
├── core/
│   ├── python/         # Python AST CLI (ast-py)
│   │   └── ast_py/
│   ├── nodejs-ts/      # TypeScript AST CLI (ast-ts)
│   │   └── src/
│   └── go/             # Go AST CLI (ast-go)
│       └── cmd/
├── docs/
│   └── JSON_SPEC.md    # JSON 规范
└── tests/
```

## JSON 响应格式

所有操作返回统一的 JSON 格式：

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

## 许可证

Apache 2.0
