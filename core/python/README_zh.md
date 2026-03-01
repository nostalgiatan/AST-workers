# ast-workers-py

[English](README.md)

Python AST 操作 CLI 工具。在抽象语法树级别编辑 Python 代码，保证语法正确性。

## 安装

```bash
pip install ast-workers-py
```

## 使用方法

```bash
ast-py <操作> [选项]
```

### 操作列表

| 命令 | 别名 | 描述 |
|---------|-------|-------------|
| `insert-function` | `if` | 插入函数 |
| `update-function` | `uf` | 更新函数 |
| `insert-class` | `ic` | 插入类 |
| `insert-class-variable` | `icv` | 插入类变量 |
| `insert-slots` | `is` | 插入 `__slots__` |
| `insert-dunder-all` | `iall` | 插入或更新 `__all__` |
| `insert-import` | `ii` | 插入导入语句 |
| `list-functions` | `lf` | 列出模块/类中的函数 |
| `list-classes` | `lc` | 列出模块中的类 |
| `list-imports` | `li` | 列出模块中的导入 |
| `find-symbol` | `fs` | 查找符号 |
| `delete-function` | `df` | 删除函数 |
| `delete-class` | `dc` | 删除类 |
| `rename-symbol` | `rn` | 重命名符号 |
| `show` | `s` | 显示符号及上下文 |
| `validate` | `v` | 验证 Python 语法 |
| `format` | `fmt` | 格式化 Python 代码 |
| `batch` | `b` | 从 JSON 执行多个操作 |

## 示例

### 查询操作

```bash
# 列出模块中的函数
ast-py list-functions -m src/auth.py

# 列出类中的方法
ast-py list-functions -m src/auth.py -c AuthService

# 列出模块中的类
ast-py list-classes -m src/models.py

# 显示符号上下文（支持作用域命名）
ast-py show -m src/auth.py -n AuthService.login

# 查找符号
ast-py find-symbol -m src/auth.py -n validate_token -t function
```

### 插入操作

```bash
# 插入简单函数
ast-py insert-function -m src/auth.py -n validate_token -p "token:str" -r bool -b "return len(token) > 10"

# 向类中插入方法
ast-py insert-function -m src/auth.py -c AuthService -n check_permissions -p "user:User, action:str" -r bool

# 高级参数语法
ast-py insert-function -m src/utils.py -n process -p "data, /, strict:bool=True, *, encoding:str='utf-8', **kwargs"

# 带装饰器
ast-py insert-function -m src/api.py -n get_user -p "user_id:int" -d "@route('/users/<int:user_id>'), @login_required"

# 异步函数
ast-py insert-function -m src/async_ops.py -n fetch_data --is-async -p "url:str" -r "dict"

# 带文档字符串
ast-py insert-function -m src/auth.py -n login -p "user:str, password:str" --docstring "认证用户并返回会话"

# 插入类
ast-py insert-class -m src/models.py -n User -b "BaseModel" --docstring "用户模型" --class-vars "id:int, name:str"

# 插入类变量
ast-py insert-class-variable -m src/models.py -c User -n count -t int -v 0

# 插入 __slots__
ast-py insert-slots -m src/models.py -c User --slots id name email

# 插入 __all__
ast-py insert-dunder-all -m src/auth.py --names login logout authenticate

# 插入导入
ast-py insert-import -m src/auth.py --from typing --name "Optional, Dict"
```

### 更新操作

```bash
# 更新函数体
ast-py update-function -m src/auth.py -n validate_token -b "return token is not None"

# 替换整个参数列表
ast-py update-function -m src/auth.py -n login -p "self, user_id:int, timeout:int=30"

# 添加参数
ast-py update-function -m src/auth.py -n login --add-params "remember:bool=False"

# 删除参数
ast-py update-function -m src/auth.py -n login --remove-params deprecated_param

# 修改返回类型
ast-py update-function -m src/auth.py -n get_user --return-type "Optional[User]"

# 添加装饰器
ast-py update-function -m src/api.py -n endpoint --add-decorators "@cache(3600)"

# 删除装饰器
ast-py update-function -m src/api.py -n endpoint --remove-decorators old_decorator

# 更新文档字符串
ast-py update-function -m src/auth.py -n login --docstring "认证用户"
```

### 删除操作

```bash
# 删除函数
ast-py delete-function -m src/auth.py -n old_function

# 删除类
ast-py delete-class -m src/models.py -n DeprecatedModel
```

### 重命名操作

```bash
# 重命名函数
ast-py rename-symbol -m src/auth.py -o old_name -n new_name -t function

# 重命名类
ast-py rename-symbol -m src/models.py -o OldUser -n User -t class
```

### 工具操作

```bash
# 验证语法
ast-py validate -m src/auth.py

# 格式化代码
ast-py format -m src/auth.py

# 从 JSON 批量操作
ast-py batch -m src/auth.py --json ops.json
```

## 参数语法

`-p/--params` 参数支持完整的 Python 参数语法：

```
位置参数, /, 位置或关键字参数, *, 仅关键字参数, **kwargs
```

示例：
- 基础：`-p "x, y, z"`
- 带类型：`-p "x:int, y:str, z:float"`
- 带默认值：`-p "x:int=0, y:str='hello'"`
- 仅位置参数：`-p "a, b, /, c, d"`（a, b 只能位置传递）
- 仅关键字参数：`-p "*, c, d=1"`（c, d 必须关键字传递）
- *args/**kwargs：`-p "*args:int, **kwargs:dict"`

## 结构化 Body 格式

多行代码需要正确的缩进时，使用 JSON 数组：

```bash
# 嵌套列表表示缩进层级
ast-py insert-function -m src/auth.py -n process -p "data:dict" -b '["if data:", ["result = process(data)", "return result"], "return None"]'
```

结果：
```python
def process(data: dict):
    if data:
        result = process(data)
        return result
    return None
```

## 作用域命名

使用点号定位嵌套符号：

```bash
# 类方法
ast-py show -m src/auth.py -n AuthService.login

# 嵌套类
ast-py show -m src/models.py -n OuterClass.InnerClass
```

## 许可证

Apache 2.0
