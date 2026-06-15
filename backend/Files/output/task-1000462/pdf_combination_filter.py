# pdf_combination_filter

> 任务: PDF#514 组合筛选器
> 附件类型: 代码文件
> 生成时间: 2026-05-13 03:04

```python
#!/usr/bin/env python3
"""
PDF#514 组合筛选器
====================
功能：基于状态字段的多条件组合（AND/OR）筛选命令行工具。
      读取 PDF 元数据报告（CSV 格式），根据用户指定的条件表达式进行筛选，
      将符合条件的行输出到控制台。

用法示例：
    python pdf_filter.py --data metadata.csv --condition "Status == '已处理' AND (Type == '发票' OR Type == '收据')"

依赖：标准库（argparse, csv, re, copy, sys）
"""

import argparse
import csv
import re
import sys
from copy import deepcopy
from typing import List, Dict, Any, Union, Optional, Callable

# ----------------------------------------------------------------------
# 1. 模块导入与依赖声明（已通过 import 完成）
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
# 2. 数据加载函数（读取 PDF 元数据报告）
# ----------------------------------------------------------------------

def load_data(file_path: str) -> List[Dict[str, str]]:
    """
    从 CSV 文件加载 PDF 元数据报告。

    参数：
        file_path (str): CSV 文件路径，要求第一行为字段名（列标题）。

    返回：
        List[Dict[str, str]]: 每行数据转换为字典的列表。

    抛出：
        FileNotFoundError: 文件不存在时。
        csv.Error: 文件格式错误时。

    示例 CSV 文件内容（可存储为 metadata.csv）：
        File,Status,Type,Size,Creator,CreationDate
        report1.pdf,已处理,发票,1024KB,Alice,2024-01-15
        report2.pdf,待审核,收据,512KB,Bob,2024-02-20
        report3.pdf,已处理,合同,2048KB,Charlie,2024-03-10
        report4.pdf,已归档,发票,768KB,Alice,2024-01-30
        data.pdf,已处理,收据,256KB,David,2024-04-05
    """
    rows = []
    try:
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 去除键和值两侧空白（便于匹配）
                cleaned = {k.strip(): v.strip() if v else "" for k, v in row.items()}
                rows.append(cleaned)
    except FileNotFoundError:
        # print(f"错误：文件 '{file_path}' 未找到。", file=sys.stderr)
        sys.exit(1)
    except csv.Error as e:
        # print(f"CSV 解析错误：{e}", file=sys.stderr)
        sys.exit(1)
    return rows

# ----------------------------------------------------------------------
# 3. 筛选规则解析函数（支持多条件、AND/OR 逻辑）
# ----------------------------------------------------------------------

class Token:
    """
    词法单元类，用于条件表达式解析。
    """
    def __init__(self, type_: str, value: Any):
        self.type = type_
        self.value = value

    def __repr__(self):
        return f"Token({self.type}, {self.value!r})"

def tokenize(expr: str) -> List[Token]:
    """
    将条件表达式字符串转换为词法单元列表。

    支持：
        - 比较运算符：==, !=, <, >, <=, >=
        - 逻辑运算符：AND, OR, NOT（大小写不敏感，但推荐大写）
        - 括号：( )
        - 标识符（字段名）：字母数字下划线
        - 字符串字面量：单引号或双引号包围
        - 数字字面量：整数或浮点数

    参数：
        expr (str): 条件表达式字符串。

    返回：
        List[Token]: 词法单元列表。

    示例：
        tokenize("Status == '已处理' AND (Type == '发票' OR Type == '收据')")
    """
    tokens = []
    i = 0
    length = len(expr)
    while i < length:
        ch = expr[i]

        # 跳过空格
        if ch.isspace():
            i += 1
            continue

        # 字符串字面量
        if ch in ("'", '"'):
            quote = ch
            j = i + 1
            while j < length and expr[j] != quote:
                if expr[j] == '\\' and j + 1 < length:
                    j += 1  # 跳过转义字符
                j += 1
            if j >= length:
                raise ValueError(f"未闭合的字符串字面量，起始于位置 {i}")
            string_value = expr[i+1:j]  # 不包含引号（简化，不处理转义）
            # 实际转义处理：评估字符串
            # 使用 ast.literal_eval 可以处理转义，但为了无额外依赖，手动简单处理
            # 这里演示简化版本，实际可替换为：import ast; string_value = ast.literal_eval(expr[i:j+1])
            # 但我们自己实现常见转义：
            string_value = string_value.replace('\\"', '"').replace("\\'", "'").replace("\\\\", "\\")
            tokens.append(Token('STRING', string_value))
            i = j + 1
            continue

        # 数字字面量（整数或浮点数）
        if ch.isdigit() or (ch == '-' and i + 1 < length and expr[i+1].isdigit()):
            j = i
            if expr[j] == '-':
                j += 1
            while j < length and (expr[j].isdigit() or expr[j] == '.'):
                j += 1
            num_str = expr[i:j]
            if '.' in num_str:
                tokens.append(Token('NUMBER', float(num_str)))
            else:
                tokens.append(Token('NUMBER', int(num_str)))
            i = j
            continue

        # 比较运算符（多字符优先）
        two_char_ops = ['==', '!=', '<=', '>=']
        if i + 1 < length and expr[i:i+2] in two_char_ops:
            tokens.append(Token('OP', expr[i:i+2]))
            i += 2
            continue

        single_ops = ['<', '>']
        if ch in single_ops:
            tokens.append(Token('OP', ch))
            i += 1
            continue

        # 括号
        if ch in '()':
            tokens.append(Token('PAREN', ch))
            i += 1
            continue

        # 标识符（字段名）或逻辑关键字
        if ch.isalpha() or ch == '_':
            j = i
            while j < length and (expr[j].isalnum() or expr[j] == '_'):
                j += 1
            word = expr[i:j]
            # 逻辑关键字（不区分大小写）
            upper_word = word.upper()
            if upper_word == 'AND':
                tokens.append(Token('LOGIC', 'AND'))
            elif upper_word == 'OR':
                tokens.append(Token('LOGIC', 'OR'))
            elif upper_word == 'NOT':
                tokens.append(Token('LOGIC', 'NOT'))
            else:
                tokens.append(Token('IDENTIFIER', word))
            i = j
            continue

        raise ValueError(f"无法识别的字符 '{ch}' 在位置 {i}")

    return tokens

class Node:
    """抽象语法树节点基类"""
    pass

class Comparison(Node):
    """比较表达式节点，如 field op value"""
    def __init__(self, field: str, op: str, value: Any):
        self.field = field
        self.op = op
        self.value = value

    def evaluate(self, record: Dict[str, str]) -> bool:
        """
        对单条记录求值比较表达式。

        参数：
            record (Dict[str, str]): 一条元数据记录。

        返回：
            bool: 比较结果。
        """
        field_val = record.get(self.field)
        if field_val is None:
            # 字段不存在时视为 False
            return False
        # 尝试按数字比较，否则按字符串比较
        try:
            # 优先转换为数字（如果字段值和比较值都可转为数字）
            left = float(field_val) if '.' in field_val else int(field_val)
            right = float(self.value) if isinstance(self.value, (int, float)) else float(self.value)
        except (ValueError, TypeError):
            left = field_val
            right = self.value
        # 注意：当 left, right 类型不一致时，这里按字符串比较
        # 也可统一转为字符串比较，但可能失去数字顺序。此处理为启发式。
        if self.op == '==':
            return left == right
        elif self.op == '!=':
            return left != right
        elif self.op == '<':
            return left < right
        elif self.op == '>':
            return left > right
        elif self.op == '<=':
            return left <= right
        elif self.op == '>=':
            return left >= right
        else:
            raise ValueError(f"不支持的比较运算符: {self.op}")

class AndNode(Node):
    """AND 逻辑节点"""
    def __init__(self, left: Node, right: Node):
        self.left = left
        self.right = right

    def evaluate(self, record: Dict[str, str]) -> bool:
        return self.left.evaluate(record) and self.right.evaluate(record)

class OrNode(Node):
    """OR 逻辑节点"""
    def __init__(self, left: Node, right: Node):
        self.left = left
        self.right = right

    def evaluate(self, record: Dict[str, str]) -> bool:
        return self.left.evaluate(record) or self.right.evaluate(record)

class NotNode(Node):
    """NOT 逻辑节点"""
    def __init__(self, child: Node):
        self.child = child

    def evaluate(self, record: Dict[str, str]) -> bool:
        return not self.child.evaluate(record)

def parse(tokens: List[Token]) -> Node:
    """
    将词法单元列表解析为抽象语法树（AST）。

    语法（上下文无关文法）：
        expr     -> or_expr
        or_expr  -> and_expr ( 'OR' and_expr )*
        and_expr -> not_expr ( 'AND' not_expr )*
        not_expr -> 'NOT' not_expr | primary
        primary  -> '(' expr ')'
                 | IDENTIFIER OP ( STRING | NUMBER )

    参数：
        tokens (List[Token]): 词法单元列表。

    返回：
        Node: AST 根节点。

    抛出：
        ValueError: 语法错误或 token 不足。
    """
    index = [0]  # 使用列表模拟可变变量

    def current() -> Optional[Token]:
        return tokens[index[0]] if index[0] < len(tokens) else None

    def consume(expected_type: str = None, expected_value: Any = None) -> Token:
        """消耗当前 token，并可选择检查类型和值。"""
        tok = current()
        if tok is None:
            raise ValueError("表达式未完成，需要更多 token")
        if expected_type and tok.type != expected_type:
            raise ValueError(f"期望 {expected_type}，但得到 {tok.type} ({tok.value})")
        if expected_value is not None and tok.value != expected_value:
            raise ValueError(f"期望值为 {expected_value}，但得到 {tok.value}")
        index[0] += 1
        return tok

    def parse_primary() -> Node:
        """解析 primary：括号表达式或比较"""
        tok = current()
        if tok is None:
            raise ValueError("需要表达式，但输入结束")
        if tok.type == 'PAREN' and tok.value == '(':
            consume('PAREN', '(')
            node = parse_or_expr()
            consume('PAREN', ')')
            return node
        elif tok.type == 'IDENTIFIER':
            field_token = consume('IDENTIFIER')
            # 注意：IDENTIFIER 后应紧跟 OP
            op_token = consume('OP')
            # 之后是值（STRING 或 NUMBER）
            val_token = current()
            if val_token is None or val_token.type not in ('STRING', 'NUMBER'):
                raise ValueError(f"需要在运算符 {op_token.value} 之后提供值")
            consume(val_token.type)
            value = val_token.value
            return Comparison(field_token.value, op_token.value, value)
        else:
            raise ValueError(f"意外的 token: {tok}")

    def parse_not_expr() -> Node:
        """解析 not_expr"""
        tok = current()
        if tok and tok.type == 'LOGIC' and tok.value == 'NOT':
            consume('LOGIC', 'NOT')
            child = parse_not_expr()
            return NotNode(child)
        else:
            return parse_primary()

    def parse_and_expr() -> Node:
        """解析 and_expr"""
        left = parse_not_expr()
        while current() and current().type == 'LOGIC' and current().value == 'AND':
            consume('LOGIC', 'AND')
            right = parse_not_expr()
            left = AndNode(left, right)
        return left

    def parse_or_expr() -> Node:
        """解析 or_expr（起点）"""
        left = parse_and_expr()
        while current() and current().type == 'LOGIC' and current().value == 'OR':
            consume('LOGIC', 'OR')
            right = parse_and_expr()
            left = OrNode(left, right)
        return left

    ast = parse_or_expr()
    if current() is not None:
        raise ValueError(f"表达式后有额外 token: {current().value}")
    return ast

def parse_condition(condition_str: str) -> Node:
    """
    将条件表达式字符串解析为 AST。

    参数：
        condition_str (str): 条件表达式，如 "Status == '已处理' AND (Type == '发票' OR Type == '收据')"

    返回：
        Node: AST 根节点。
    """
    tokens = tokenize(condition_str)
    return parse(tokens)

# ----------------------------------------------------------------------
# 4. 主函数：解析命令行参数、加载数据、执行筛选、打印结果
# ----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='PDF#514 组合筛选器 —— 基于状态字段的多条件组合（AND/OR）筛选命令行工具。'
    )
    parser.add_argument(
        '--data', '-d',
        required=True,
        help='PDF 元数据 CSV 文件路径'
    )
    parser.add_argument(
        '--condition', '-c',
        required=True,
        help='筛选条件表达式，例如：Status == "已处理" AND (Type == "发票" OR Type == "收据")'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        default=0,
        help='限制输出行