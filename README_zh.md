# AST Workers

[English](README.md)

修改文件时缺少上下文？行号不准确？文件修改导致代码混乱？**AST Workers** 来帮你！

基于 AST（抽象语法树）结构，我们提供代码查询、插入、删除和修改操作，保证语法正确性，避免传统文本文件修改带来的异常。

## 为什么选择 AST Workers？

| 传统文件修改方式 | AST Workers |
|-----------------|-------------|
| 文本替换，容易误匹配 | AST 级别精确定位 |
| 手动处理缩进和格式 | 自动格式化 |
| 可能破坏语法 | 保证语法正确 |
| 需要大量上下文 | 声明式，简洁 |

## 架构设计

```
┌─────────────────────────────────────────────┐
│           ast-workers-mcp                    │
│         (FastMCP 服务器)                     │
│    路由 → subprocess → 解析 JSON             │
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

每种语言使用自己的 AST 库和 CLI 工具，通过 subprocess 连接。MCP 服务器根据文件扩展名或显式的语言参数路由请求。

## 安装

```bash
# 安装 MCP 服务器
pip install -e .

# 安装 Python AST CLI（.py 文件必需）
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

### 可用工具

| 工具 | 描述 |
|------|------|
| `insert_function` | 向模块或类中插入函数/方法 |
| `insert_class` | 向模块中插入类 |
| `insert_import` | 插入导入语句 |
| `insert_class_variable` | 插入类变量 |
| `update_function` | 更新函数体、参数、装饰器等 |
| `delete_function` | 从模块或类中删除函数 |
| `delete_class` | 从模块中删除类 |
| `rename_symbol` | 重命名符号（函数/类/变量） |
| `list_functions` | 列出模块或类中的函数 |
| `list_classes` | 列出模块中的类 |
| `list_imports` | 列出模块中的导入 |
| `find_symbol` | 查找符号的位置和类型 |
| `validate_syntax` | 验证模块语法 |
| `format_code` | 使用格式化工具格式化代码 |
| `batch_operations` | 批量执行多个操作 |
| `list_supported_languages` | 列出支持的语言和 CLI 状态 |
| `get_tools_info` | 获取所有可用工具及其模式 |

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

# 显式指定语言（用于非标准扩展名的文件）
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
```

## 支持的语言

| 语言 | CLI | 状态 |
|------|-----|------|
| Python | `ast-py` | ✅ 已完成 |
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
