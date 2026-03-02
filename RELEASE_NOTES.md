## v0.1.5 TypeScript/JavaScript 支持

### 🎉 新功能

#### TypeScript/JavaScript AST 操作支持

新增 `ast-ts` CLI 工具，完整支持 TypeScript 和 JavaScript 文件的 AST 操作：

- **基础操作**: `insert_function`, `insert_class`, `insert_import`, `update_function`, `delete_function`, `delete_class`, `rename_symbol`
- **查询操作**: `list_functions`, `list_classes`, `list_imports`, `find_symbol`, `show_symbol`
- **TypeScript 专用**: `insert_interface`, `insert_type_alias`, `insert_enum`, `list_interfaces`, `list_enums`, `list_type_aliases`

#### 打包安装方式

`ast-ts` 现已打包在 `ast-workers-mcp` 中，通过命令安装：

```bash
# 安装 ast-ts
ast-workers-mcp install-ts

# 卸载 ast-ts
ast-workers-mcp install-ts --uninstall
```

#### 语言能力查询

新增 `get_language_capabilities` 工具，查看每种语言支持的操作：

```python
get_language_capabilities(params={"language": "typescript"})
```

### 📦 涉及的文件

| 文件 | 修改内容 |
|------|----------|
| ast_mcp/server.py | 新增 TypeScript 工具定义，添加语言特定参数处理 |
| ast_mcp/install_ts.py | 新增 ast-ts 安装/卸载功能 |
| ast_mcp/ast-ts-dist.tar.gz | 打包的 TypeScript CLI |
| core/nodejs-ts/ | TypeScript AST CLI 源码 |

### 🔧 TypeScript 特有参数

| 操作 | 参数 | 说明 |
|------|------|------|
| insert_class | `type_params` | 泛型参数，如 `T, U extends string` |
| insert_class | `implements` | 实现接口，如 `Serializable, Comparable` |
| insert_class | `is_abstract` | 是否为抽象类 |
| insert_interface | `extends` | 继承接口 |
| insert_interface | `properties` | 属性定义，如 `id:string, name?:string` |

### ✅ 测试结果

- Python 操作 ✅ 正常
- TypeScript 操作 ✅ 正常
- `install-ts` 命令 ✅ 正常
- 语言能力查询 ✅ 正常

### 📝 升级指南

```bash
pip install --upgrade ast-workers-mcp
pip install --upgrade ast-workers-py
ast-workers-mcp install-ts
```

---

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