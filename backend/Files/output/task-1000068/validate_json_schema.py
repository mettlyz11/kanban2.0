# validate_json_schema

> 任务: v3 #7 JSON schema校验
> 附件类型: Python脚本
> 生成时间: 2026-05-11 23:21

```python
#!/usr/bin/env python3
"""
nbformat.v3 JSON Schema 校验工具 (v3 #7)

本脚本用于根据指定的 JSON Schema 文件对给定的 JSON 数据进行校验，
特别针对 nbformat 的 v3 版本 schema (nbformat.v3.schema.json) 设计。
提供了完整的校验函数、错误收集与结构化输出，支持命令行参数，
可独立运行或作为模块导入。

主要功能：
    - 加载 JSON Schema 文件（本地路径或 URL）
    - 加载待校验的 JSON 数据文件
    - 使用 jsonschema 库进行校验，收集所有错误（非 lazy）
    - 结构化错误输出（包含路径、消息、模式、实例等关键信息）
    - 支持命令行参数：--schema, --data, --verbose, --output 等
    - 错误信息人性化，便于调试

依赖：
    - Python 3.7+
    - jsonschema (推荐 4.0+)   `pip install jsonschema`

使用示例：
    python nbformat_v3_validator.py --schema nbformat.v3.schema.json --data example_notebook.json
    python nbformat_v3_validator.py --schema path/to/schema.json --data data.json --verbose

本脚本也包含一个简化的示例 schema 和示例 JSON 数据，用于演示（在文件末尾）。
若需要实际校验 nbformat v3 notebook，请提供正确的 nbformat.v3.schema.json 文件。
"""

import json
import os
import sys
import argparse
from typing import List, Dict, Any, Optional
from pathlib import Path

# 尝试导入 jsonschema，若失败则给出安装提示
try:
    import jsonschema
    from jsonschema import validate, ValidationError, SchemaError
except ImportError:
    # print("错误: 需要 jsonschema 库。请执行: pip install jsonschema", file=sys.stderr)
    sys.exit(1)


def load_json_file(file_path: str) -> Dict[str, Any]:
    """
    从文件路径加载 JSON 数据。

    参数:
        file_path (str): JSON 文件路径（支持绝对/相对路径）

    返回:
        Dict[str, Any]: 解析后的 Python 字典

    异常:
        FileNotFoundError: 文件不存在
        json.JSONDecodeError: JSON 格式错误
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"JSON 文件不存在: {file_path}")
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def load_schema(schema_path: str) -> Dict[str, Any]:
    """
    加载 JSON Schema 文件（支持 .json 或 .json5 等）。

    参数:
        schema_path (str): Schema 文件路径

    返回:
        Dict[str, Any]: Schema 的 Python 字典表示

    异常:
        FileNotFoundError: 文件不存在
        json.JSONDecodeError: JSON 格式不正确
    """
    return load_json_file(schema_path)


def collect_errors(instance: Any, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    使用 jsonschema 的迭代验证器收集所有校验错误。

    参数:
        instance: 待校验的 JSON 数据（Python 对象）
        schema: JSON Schema 字典

    返回:
        List[Dict[str, Any]]: 错误列表，每个错误包含:
            - path: 错误发生的 JSON 路径（数组形式）
            - path_string: 可读的路径字符串（如 '$.cells[0].source'）
            - message: 错误描述
            - validator: 触发错误的校验关键词（如 'type', 'required'）
            - schema_path: Schema 中对应规则的路径（数组）
            - schema_value: Schema 中该规则的值
            - instance: 实际的数据片段（可能很大，截断处理）
    注意：
        使用 jsonschema.Draft4Validator 或自动检测。本函数采用 Draft7Validator。
    """
    # 创建校验器（自动根据 schema 的 $schema 字段选择版本）
    # 这里显式使用 Draft7Validator，兼容 nbformat.v3 schema（基于 draft-04 或 07）
    # 也可以使用 jsonschema.validators.validator_for(schema) 自动选择
    validator = jsonschema.Draft7Validator(schema)

    errors = []
    for error in sorted(validator.iter_errors(instance), key=lambda e: e.path):
        # 构建路径信息
        path = list(error.absolute_path)
        path_string = _path_to_string(path)

        # schema path
        schema_path = list(error.schema_path)
        schema_path_string = "/".join(str(p) for p in schema_path)

        # 提取 schema 中触发的规则值（尽量精简）
        schema_rule = error.schema
        # 如果 error.validator_value 存在，则使用它
        validator_value = getattr(error, 'validator_value', None)

        # 实例片段截断（避免输出过长）
        instance_part = error.instance
        if isinstance(instance_part, (str, list, dict)):
            instance_repr = repr(instance_part)[:200]  # 只取前200字符
        else:
            instance_repr = repr(instance_part)

        error_info = {
            'path': path,
            'path_string': path_string,
            'message': error.message,
            'validator': error.validator,
            'validator_value': validator_value,
            'schema_path': schema_path,
            'schema_path_string': schema_path_string,
            'schema_rule': schema_rule if isinstance(schema_rule, dict) else str(schema_rule)[:200],
            'instance': instance_repr,
        }
        errors.append(error_info)
    return errors


def _path_to_string(path: List) -> str:
    """
    将 JSON 路径数组转换为类 JSONPath 字符串。
    例如: ['cells', 0, 'source'] -> '$.cells[0].source'
    """
    parts = []
    for p in path:
        if isinstance(p, int):
            if parts:
                parts.append(f"[{p}]")
            else:
                parts.append(str(p))
        else:
            if parts:
                parts.append(f".{p}")
            else:
                parts.append(str(p))
    if not parts:
        return "$"
    return "$." + "".join(parts)


def format_errors(errors: List[Dict[str, Any]], verbose: bool = False) -> str:
    """
    将错误列表格式化为可读的字符串。

    参数:
        errors (List[Dict]): collect_errors 的输出
        verbose (bool): 是否输出详细信息（默认 False，只输出路径和消息）
                        当 verbose=True 时，输出 schema 规则和实例片段。

    返回:
        str: 格式化的错误报告
    """
    if not errors:
        return "校验通过，未发现错误。"

    lines = []
    lines.append(f"发现 {len(errors)} 个校验错误：")
    lines.append("=" * 60)
    for i, err in enumerate(errors, 1):
        lines.append(f"\n错误 #{i}")
        lines.append(f"  路径: {err['path_string']}")
        lines.append(f"  消息: {err['message']}")
        if verbose:
            lines.append(f"  校验器: {err['validator']}")
            if err['validator_value'] is not None:
                lines.append(f"  校验器值: {repr(err['validator_value'])[:200]}")
            lines.append(f"  Schema 路径: {err['schema_path_string']}")
            lines.append(f"  实例片段: {err['instance']}")
            lines.append(f"  Schema 规则: {err['schema_rule']}")
        lines.append("-" * 40)
    lines.append("=" * 60)
    return "\n".join(lines)


def validate_data(instance: Any, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    执行校验并返回错误列表。这是主校验函数，封装了 collect_errors。

    参数:
        instance: 待校验的 JSON 数据
        schema:   JSON Schema

    返回:
        List[Dict]: 错误列表（空列表表示无错误）

    异常:
        jsonschema.SchemaError: 如果 schema 本身无效
    """
    # 先检查 schema 是否有效（可选）
    # jsonschema 在创建 Validator 时也会校验 schema，如果 schema 格式不对会抛出 SchemaError
    try:
        jsonschema.Draft7Validator.check_schema(schema)
    except jsonschema.SchemaError as e:
        raise SchemaError(f"提供的 Schema 无效: {e.message}")

    return collect_errors(instance, schema)


def main():
    """
    命令行入口函数。解析参数，加载数据，执行校验，输出结果。
    """
    parser = argparse.ArgumentParser(
        description="JSON Schema 校验工具 (nbformat.v3 兼容)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python %(prog)s --schema nbformat.v3.schema.json --data notebook.json
  python %(prog)s --schema schema.json --data data.json --verbose
  python %(prog)s --schema schema.json --data data.json --output report.json
        """
    )
    parser.add_argument('--schema', '-s', required=True,
                        help='JSON Schema 文件路径 (必选)')
    parser.add_argument('--data', '-d', required=True,
                        help='待校验的 JSON 数据文件路径 (必选)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='输出详细信息（模式、实例片段等）')
    parser.add_argument('--output', '-o', default=None,
                        help='将校验报告输出到指定 JSON 文件 （可选）')
    args = parser.parse_args()

    # 加载 schema
    try:
        schema = load_schema(args.schema)
    except Exception as e:
        # print(f"加载 Schema 文件失败: {e}", file=sys.stderr)
        sys.exit(2)

    # 加载数据
    try:
        data = load_json_file(args.data)
    except Exception as e:
        # print(f"加载数据文件失败: {e}", file=sys.stderr)
        sys.exit(2)

    # 执行校验
    try:
        errors = validate_data(data, schema)
    except SchemaError as e:
        # print(f"Schema 无效: {e}", file=sys.stderr)
        sys.exit(3)
    except Exception as e:
        # print(f"校验过程发生异常: {e}", file=sys.stderr)
        sys.exit(4)

    # 格式化输出
    report = format_errors(errors, verbose=args.verbose)
    # print(report)

    # 写入文件（如果指定）
    if args.output:
        # 将错误列表转为 JSON 输出（更结构化的机器可读格式）
        output_data = {
            "valid": len(errors) == 0,
            "error_count": len(errors),
            "errors": errors
        }
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            # print(f"\n校验报告已保存至: {args.output}")
        except Exception as e:
            # print(f"写入输出文件失败: {e}", file=sys.stderr)

    sys.exit(0 if len(errors) == 0 else 1)


# ============================================================================
# 示例数据和演示（仅在脚本作为主程序运行时加载）
# 包含一个简化的 nbformat.v3 风格 schema 以及对应的有效/无效数据
# ============================================================================
def demonstrate():
    """
    提供内置的示例，用于快速测试脚本功能。
    使用一个自定义 schema，模拟 nbformat v3 的部分校验规则。

    此函数在 __main__ 中通过 --demo 参数调用。
    """
    # 示例 schema (简化版 nbformat v3)
    sample_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Notebook v3 (示例)",
        "type": "object",
        "required": ["nbformat", "nbformat_minor", "cells"],
        "properties": {
            "nbformat": {
                "type": "integer",
                "enum": [3]
            },
            "nbformat_minor": {
                "type": "integer",
                "minimum": 0,
                "maximum": 5
            },
            "cells": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["cell_type", "source"],
                    "properties": {
                        "cell_type": {
                            "type": "string",
                            "enum": ["code", "markdown", "raw"]
                        },
                        "source": {
                            "type": "string"
                        },
                        "metadata": {
                            "type": "object",
                            "properties": {
                                "trusted": {"type": "boolean"}
                            }
                        }
                    },
                    "additionalProperties": False
                }
            }
        },
        "additionalProperties": False
    }

    # 有效示例
    valid_data = {
        "nbformat": 3,
        "nbformat_minor": 3,
        "cells": [
            {
                "cell_type": "code",
                "source": "print('hello')",
                "metadata": {"trusted": True}
            },
            {
                "cell_type": "markdown",
                "source": "# Title"
            }
        ]
    }

    # 无效示例（多项错误）
    invalid_data = {
        "nbformat": 4,                    # 错误：不是3
        "nbformat_minor": -1,            # 错误：小于0
        "cells": [
            {
                "cell_type": "python",   # 错误：不是枚举值
                "source": 123,           # 错误：不是字符串
                "extra_field": "bad"     # 错误：额外属性被禁止
            },
            {
                "source": "only source", # 错误：缺少 cell_type
            }
        ],
        "unexpected": "test"             # 错误：额外顶层属性
    }

    # print("=" * 70)
    # print("内置示例演示（使用简化版 nbformat v3 schema）")
    # print("=" * 70)

    # 演示有效数据
    # print("\n[1] 校验有效数据:")
    errors = validate_data(valid_data, sample_schema)
    # print(format_errors(errors, verbose=True))
    # print()

    # 演示无效数据
    # print("\n[2] 校验无效数据:")
    errors = validate_data(invalid_data, sample_schema)
    # print(format_errors(errors, verbose=True))

    # print("\n[提示] 使用实际文件校验时，请指定 --schema 和 --data。")


if __name__ == "__main__":
    # 如果命令行包含 --demo 参数，则运行内置演示
    if "--demo" in sys.argv:
        demonstrate()
    else:
        main()
```