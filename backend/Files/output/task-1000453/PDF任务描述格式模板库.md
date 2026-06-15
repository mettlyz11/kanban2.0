# PDF任务描述格式模板库

> 任务: PDF#503 任务描述格式模板库
> 附件类型: 模板库
> 生成时间: 2026-05-13 07:18

# PDF#503 任务描述格式模板库

## 一、概述与使用说明

### 1.1 目的与适用范围
本模板库旨在为PDF相关处理任务（编号体系：PDF-5xx系列）提供标准化的任务描述格式。通过统一的字段定义、填写规范和典型场景模板，降低任务创建与执行过程中的沟通成本，提升自动化任务链路的可复现性。适用于以下场景：
- 内部团队（数据运维、研发、测试）之间的任务交接；
- 与第三方服务（OCR引擎、格式转换服务、质量检测API）的对接需求描述；
- 自动化工作流中任务生成模块的输入标准。

### 1.2 模板结构总览
每个任务描述模板由固定字段和可选字段组成，整体分为三个层级：
- **头部**：任务唯一标识、标题、类型、优先级、创建时间等元信息。
- **主体**：任务目标、输入/输出规范、处理参数、约束条件。
- **尾部**：依赖项、风险提示、变更记录。

### 1.3 使用流程
1. **选择场景**：根据任务性质从第二章的三个模板中选择最接近的模板。
2. **填写字段**：按照第三章的字段定义逐项填写，标注为`[必填]`的字段不可缺失，`[条件必填]`字段视情况填写。
3. **验证完整性**：对照附录中的变量说明，确保所有占位符被替换为真实值。
4. **格式化检查**：确认Markdown文档符合以下规范（详见第三章）。

---

## 二、模板编写规范与字段定义

### 2.1 Markdown语法强制规范
- 头部元数据使用YAML格式，位于文档最顶部，以`---`包裹。
- 主体内容使用标题层级：`##`（一级标题用于模板名称）、`###`（二级标题用于字段组）、`####`（三级标题用于字段说明）。
- 所有变量占位符用`{花括号}`表示，变量名称使用全大写单词，单词间下划线连接，如`{FILE_PATH}`。
- 列表采用`-`或`1.`，表格使用标准Markdown表格，对齐方式左对齐。
- 代码块（含示例参数）使用三个反引号并注明语言（如`json`、`yaml`或`text`）。

### 2.2 字段定义总表（所有模板通用）

| 字段组 | 字段名 | 类型 | 必填 | 说明 |
|--------|--------|------|------|------|
| `task_id` | 任务编号 | 字符串 | 是 | 格式：`PDF-{数字}`，如`PDF-503-20250315-001` |
| `title` | 任务标题 | 字符串 | 是 | 简明扼要，不超过50字 |
| `type` | 任务类型 | 枚举 | 是 | 当前支持：`extract_metadata`, `format_conversion`, `quality_check` |
| `priority` | 优先级 | 枚举 | 是 | `P0`(阻塞), `P1`(高), `P2`(中), `P3`(低) |
| `created_by` | 创建人 | 字符串 | 是 | 工号或姓名 |
| `created_at` | 创建时间 | 日期 | 是 | ISO 8601格式：`YYYY-MM-DDTHH:mm:ssZ` |
| `description` | 任务描述 | 文本 | 是 | 概述任务目的和预期成果 |
| `input_source` | 输入来源 | 对象 | 是 | 包括`source_type`(文件/URL/流)和`source_path`(路径或链接) |
| `output_spec` | 输出规范 | 对象 | 是 | 包括`output_dir`(目录)、`output_format`(格式)、`naming_rule`(命名规则) |
| `params` | 处理参数 | 对象 | 条件 | 依场景不同而异，详见场景模板 |
| `constraints` | 约束条件 | 对象 | 否 | 包括`batch_size`、`timeout`、`file_size_limit`、`resource_limit`等 |
| `dependencies` | 依赖项 | 列表 | 否 | 前置任务编号或外部服务名称 |
| `risk_notes` | 风险提示 | 文本 | 否 | 预估的失败场景和降级方案 |
| `change_log` | 变更记录 | 列表 | 否 | 每次修改的时间、修改人、变更内容 |

### 2.3 填写要求
- 所有字符串字段必须去掉首尾空白，特殊字符（如引号、反斜杠）需转义。
- 路径分隔符统一使用正斜杠`/`，绝对路径以根目录开始（如`/data/input/`）。
- 枚举值严格匹配定义列表，不可自定义。

---

## 三、场景模板

### 场景一：PDF元数据提取任务描述模板

```yaml
---
task_id: PDF-503-{YYYYMMDD}-{SEQ}
title: 元数据提取 - {描述性标题}
type: extract_metadata
priority: P2
created_by: {创建人}
created_at: {ISO时间戳}
---
```

#### 3.1.1 任务目标
从指定PDF文件中提取所有可读取的元数据字段，包括但不限于：标题、作者、主题、关键字、创建日期、修改日期、PDF版本、页面数量、文件大小、加密状态、表单字段信息（需保留结构）。

#### 3.1.2 输入与输出
- **输入来源**
  - `source_type`: `file`（文件批量处理）或 `url`（单文件下载）。
  - `source_path`: 文件路径或URL列表。若为批量，请提供文件列表（见示例）。
  - `file_filter`: 支持通配符，如`*.pdf`、`report_*.pdf`。

- **输出规范**
  - `output_dir`: `/data/output/metadata/{任务编号}/`
  - `output_format`: `JSON`（每个文件一个对应JSON文件）
  - `naming_rule`: `{原文件名}_metadata.json`
  - `output_content`: 需包含完整的元数据键值对，嵌套结构保持原样。若元数据为空，则输出`null`并附注`"empty_metadata": true`。

#### 3.1.3 处理参数（params）
| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `extract_custom_metadata` | bool | true | 是否提取PDF文档级自定义元数据（如Adobe XMP） |
| `extract_form_fields` | bool | false | 是否提取表单字段名称和值（仅AcroForm生效） |
| `extract_annotations` | bool | false | 是否提取注释对象元数据（作者、日期、类型） |
| `flatten_arrays` | bool | false | 是否将PDF数组类型的元数据（如Keywords）展平为逗号分隔字符串 |
| `encoding` | string | "utf-8" | 输出JSON的编码格式 |
| `timeout_per_file` | int | 60 | 单个文件处理超时（秒），超时任务标记为失败并跳过 |

#### 3.1.4 约束条件
- `batch_size`: 最大50个文件（并发数不超过5）。
- `file_size_limit`: 单个PDF不超过500MB。
- `resource_limit`: CPU<4核，内存<8GB。

#### 3.1.5 示例填写（使用真实数据）
```yaml
task_id: PDF-503-20250315-001
title: 元数据提取 - 2025年Q1销售报告PDF
type: extract_metadata
priority: P2
created_by: ZHANGSAN
created_at: 2025-03-15T10:30:00Z
description: 提取/data/input/2025Q1/目录下12份销售报告PDF的完整元数据，用于后续索引构建。
input_source:
  source_type: file
  source_path: /data/input/2025Q1/
  file_filter: "Sales_Report_2025Q1_*.pdf"
output_spec:
  output_dir: /data/output/metadata/PDF-503-20250315-001/
  output_format: JSON
  naming_rule: "{原文件名}_metadata.json"
params:
  extract_custom_metadata: true
  extract_form_fields: false
  extract_annotations: false
  flatten_arrays: true
  encoding: utf-8
  timeout_per_file: 120
constraints:
  batch_size: 12
  file_size_limit: 200MB
  resource_limit: "CPU:4核, 内存:8GB"
dependencies: []
risk_notes: "部分PDF可能包含XFA表单，元数据提取可能不完整，需人工复核"
change_log:
  - date: 2025-03-15T10:31:00Z
    author: ZHANGSAN
    change: 初始创建
```

#### 3.1.6 使用说明
- 根据实际情况替换`{创建人}`、`{ISO时间戳}`等占位符。
- 若输入为URL列表，则`source_type`设为`url`，`source_path`为数组：
  ```
  source_path:
    - "https://example.com/docs/file1.pdf"
    - "https://example.com/docs/file2.pdf"
  ```

---

### 场景二：PDF格式转换任务描述模板

```yaml
---
task_id: PDF-503-{YYYYMMDD}-{SEQ}
title: 格式转换 - {源格式}转{目标格式}
type: format_conversion
priority: P2
created_by: {创建人}
created_at: {ISO时间戳}
---
```

#### 3.2.1 任务目标
将指定PDF文件转换为目标格式（支持：TXT、HTML、DOCX、XLSX、PPTX、图片PNG/JPEG、SVG）。转换过程中需保留文档结构（段落、列表、表格）、字体信息（嵌入字体保持）、图像质量和超链接。对于可编辑格式（DOCX/XLSX/PPTX），需实现双向还原度不低于95%（与原PDF视觉对比）。

#### 3.2.2 输入与输出
- **输入来源**
  - `source_type`: `file`（本地文件）或 `stream`（从流读取，需提供流ID）。
  - `source_path`: 文件绝对路径或流标识。

- **输出规范**
  - `output_dir`: `/data/output/conversion/{任务编号}/`
  - `output_format`: 目标格式后缀列表，如`[".docx", ".html"]`（支持同时多种格式）
  - `naming_rule`: `{原文件名}_{目标格式}.{后缀}`（如`report.docx`、`report.html`）
  - 若转换失败，输出错误日志到`{任务编号}_error.log`，包含失败原因和栈追踪。

#### 3.2.3 处理参数（params）
| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `target_formats` | string[] | ["docx"] | 目标格式列表，必须为支持的后缀 |
| `preserve_layout` | bool | true | 是否尽量保留原始布局（对docx有效） |
| `image_dpi` | int | 150 | 转换为图片时的DPI（仅当目标格式为图片时生效） |
| `embed_fonts` | bool | true | 是否嵌入PDF中使用的字体（docx/html有效） |
| `extract_links` | bool | true | 是否提取PDF中的超链接并保持（docx/html有效） |
| `table_detection` | string | "auto" | 表格检测模式：auto(自动), agressive(强行将分界线视为表格), off(忽略) |
| `optimize_for_editing` | bool | false | 是否优化输出为可编辑格式（牺牲部分视觉保真度） |
| `ocr_fallback` | bool | false | 若PDF为扫描件（无文本层），是否启用OCR（需依赖外部OCR服务） |
| `ocr_language` | string | "eng" | OCR语言，多个语言用`+`连接，如`eng+chi_sim` |
| `timeout_per_page` | int | 30 | 每页转换超时时间（秒），超过则跳过该页，记为警告 |

#### 3.2.4 约束条件
- `batch_size`: 单个任务最多处理10个PDF。
- `file_size_limit`: 单个PDF不超过1GB（扫描件含OCR时不超过500MB）。
- `resource_limit`: 转换任务使用CPU<8核，内存<16GB，磁盘临时空间<20GB。
- 不支持加密PDF（需先提供解密密钥）。

#### 3.2.5 示例填写
```yaml
task_id: PDF-503-20250315-002
title: 格式转换 - PDF转DOCX+HTML
type: format_conversion
priority: P1
created_by: LISI
created_at: 2025-03-15T14:00:00Z
description: 将用户上传的三份调查报告PDF转换为可编辑的DOCX和用于网页展示的HTML。
input_source:
  source_type: file
  source_path: /data/input/surveys/
  file_filter: "Survey_*.pdf"
output_spec:
  output_dir: /data/output/conversion/PDF-503-20250315-002/
  output_format:
    - ".docx"
    - ".html"
  naming_rule: "{原文件名}_{目标格式}{后缀}"
params:
  target_formats:
    - "docx"
    - "html"
  preserve_layout: true
  image_dpi: 200
  embed_fonts: true
  extract_links: true
  table_detection: auto
  optimize_for_editing: false
  ocr_fallback: false
  timeout_per_page: 60
constraints:
  batch_size: 3
  file_size_limit: 100MB
  resource_limit: "CPU:4核, 内存:8GB, 临时空间:5GB"
dependencies:
  - "OCR微服务状态正常（本任务未使用OCR，故此项可忽略）"
risk_notes: "用户PDF包含大量数学公式和复杂表格，HTML输出中公式可能呈现不准确，建议安排人工抽查前10页。"
change_log:
  - date: 2025-03-15T14:05:00Z
    author: LISI
    change: 初始创建
```

#### 3.2.6 使用说明
- 当目标格式为图片（PNG/JPEG）时，每个PDF页面生成一个图片文件，命名规则为`{原文件名}_page_{页码}.{后缀}`。
- 若`ocr_fallback=true`，需确保依赖的OCR服务可用，并提前填写`ocr_language`参数。

---

### 场景三：PDF质量检查任务描述模板

```yaml
---
task_id: PDF-503-{YYYYMMDD}-{SEQ}
title: 质量检查 - {检查类型}
type: quality_check
priority: P3
created_by: {创建人}
created_at: {ISO时间戳}
---
```

#### 3.3.1 任务目标
对指定PDF文件进行自动化质量检测，输出结构化质量报告。检查维度包括：文件完整性、文本层可读性（非扫描件）、文字/图像/表格的识别程度、颜色模式（CMYK/RGB）、字体嵌入率、元数据完整性、PDF/A合规性、链接有效性、页数校验。根据检查结果给出质量等级（Pass/Warning/Fail）并标注具体问题。

#### 3.3.2 输入与输出
- **输入来源**
  - `source_type`: `file`（批量）或 `directory`（递归扫描）
  - `source_path`: 目录路径或单一文件路径。
  - `recursive`: bool，是否递归处理子目录（默认true）。

- **输出规范**
  - `output_dir`: `/data/output/quality/{任务编号}/`
  - `output_format`: `JSON`（主报告） + `CSV`（汇总表）
  - `naming_rule`: 
    - 主报告：`{原文件名}_quality_report.json`
    - 汇总表：`quality_summary.csv`
  - 报告结构：
    ```json
    {
      "file": "文件名",
      "overall_grade": "Pass|Warning|Fail",
      "dimensions": {
        "integrity": {"grade": "Pass", "issue": null},
        "text_layer": {"grade": "Warning", "issue": "第3页缺失文本层"},
        "image_quality": {"grade": "Pass", "issue": null},
        "font_embedding": {"grade": "Fail", "issue": "未嵌入字体：Arial, TimesNewRoman"},
        "metadata": {"grade": "Pass", "issue": null},
        "pdfa_compliance": {"grade": "Warning", "issue": "不符合PDF/A-1b: 缺少XMP