## v0.1.2 Bug 修复版本

### 🐛 修复的问题

#### 1. 结构化 Body 格式问题

**问题**: JSON 序列化时 Python 的 `tuple` 会被转换为 `list`，导致结构化 body 格式无法正确识别缩进层级。

**影响**: 使用 MCP 工具传入结构化 body 时，缩进处理失败。

**修复**: 更新 `_build_structured_body_from_list` 函数，同时处理 `tuple` 和 `list` 类型。

#### 2. update_function 不支持结构化 Body

**问题**: `update_function` 的 `body` 参数类型为 `str`，不支持结构化列表格式。

**影响**: 无法通过 MCP 更新函数时使用结构化 body。

**修复**: 
- 更新 `UpdateFunctionParams.body` 类型
- 添加 JSON 解析逻辑处理字符串形式的列表
- 更新 `_build_new_body` 方法支持结构化输入

#### 3. update.py 语法错误

**问题**: 修改过程中引入了缩进错误，导致模块无法加载。

**修复**: 修正 docstring 和函数体的缩进。

### 📦 涉及的文件

| 文件 | 修改内容 |
|------|----------|
| generator/function.py | 修复结构化 body 同时处理 tuple/list |
| operations/update.py | 支持结构化 body，修复缩进错误 |
| ast_mcp/server.py | 更新 UpdateFunctionParams.body 类型 |

### ✅ 测试结果

- list_functions ✅ 正常
- show_symbol ✅ 作用域命名正常
- insert_function ✅ 结构化 body 正常
- update_function ✅ 结构化 body 正常
- delete_function ✅ 正常

### 📝 升级指南

```bash
pip install --upgrade ast-workers-mcp
pip install --upgrade ast-workers-py
```
