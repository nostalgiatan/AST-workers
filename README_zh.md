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
│ ✅    │   │ 计划中   │   │ 计划中  │   │ 计划中  │
└───────┘   └──────────┘   └─────────┘   └─────────┘
  .py        .ts/.tsx       .go          .rs
```

每种语言使用自己的 AST 库和 CLI 工具，通过 subprocess 连接。MCP 服务器根据文件扩展名或显式语言参数路由请求。

## 安装

```bash
# 安装 MCP 服务器
pip install -e .

# 安装 Python AST CLI（.py 文件需要）
pip install -e ./core/python
```

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

### 核心特性

#### 作用域式命名

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

### 示例

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

## 支持的语言

| 语言 | CLI | 状态 |
|----------|-----|------|
| Python | `ast-py` | ✅ 就绪 |
| TypeScript/JavaScript | `ast-ts` | 📋 计划中 |
| Go | `ast-go` | 📋 计划中 |
| Rust | `ast-rust` | 📋 计划中 |

## 项目结构

```
AST-workers/
├── pyproject.toml      # 项目配置
├── ast_mcp/            # MCP 服务器
│   ├── __init__.py
│   └── server.py
├── core/
│   └── python/         # Python AST CLI (ast-py)
│       └── ast_py/
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