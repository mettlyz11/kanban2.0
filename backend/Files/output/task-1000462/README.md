# README

> 任务: PDF#514 组合筛选器
> 附件类型: 用户手册
> 生成时间: 2026-05-13 03:04

# PDF#514 组合筛选器 用户手册

## 1. 项目概述与背景

### 1.1 项目简介

**PDF#514 组合筛选器** 是一个基于 Python 的命令行工具，用于对大量 PDF 文件进行组合条件筛选。它支持用户定义多个筛选条件，并通过逻辑运算符（AND、OR）灵活组合，精确快速地定位目标 PDF 文件。该工具特别适用于需要按文件状态、创建日期、大小、含特定文本等多维属性进行批量检索的场景。

### 1.2 设计目标

- **降低使用门槛**：无需编程知识，通过简单的命令行参数即可执行复杂筛选。
- **高效精准**：利用正则表达式和条件组合，兼顾速度与准确性。
- **结果直观**：支持表格和 JSON 两种输出格式，便于人工审阅或程序化处理。

### 1.3 适用场景

- 法律/合同文档的批量归类（如按“已签署”“未签署”状态）。
- 学术文献管理（按发表年份、关键词筛选）。
- 企业文件归档（按文件大小、创建时间筛选）。
- 自动化工作流中作为预处理步骤。

---

## 2. 环境要求

### 2.1 操作系统

- Windows 10/11（64位）
- macOS 10.15+
- Linux（内核版本 4.0+，推荐 Ubuntu 20.04+）

### 2.2 Python 版本

- **Python 3.8 及以上**（推荐 3.10 或 3.12）
- 不支持 Python 2.x

### 2.3 依赖库

`PDF#514 组合筛选器` 依赖以下 Python 第三方库：

| 库名 | 最低版本 | 用途 |
|------|---------|------|
| `PyPDF2` | 3.0.0 | 读取 PDF 元数据和文本内容 |
| `tabulate` | 0.9.0 | 输出表格格式化 |
| `click` | 8.1.0 | 命令行界面参数解析 |
| `python-dateutil` | 2.8.0 | 日期解析与比较 |
| `json` | 标准库 | 序列化输出 |

建议使用 `virtualenv` 或 `conda` 创建独立环境以避免版本冲突。

---

## 3. 安装步骤

### 3.1 方法一：通过 requirements.txt 安装（推荐）

1. 将 `PDF#514` 项目压缩包解压到本地目录。
2. 打开终端（命令提示符或 Shell），进入项目根目录。
3. 创建虚拟环境（可选但强烈推荐）：
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/macOS
   venv\Scripts\activate      # Windows
   ```
4. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
5. 验证安装成功：
   ```bash
   python pdf_filter.py --help
   ```

### 3.2 方法二：直接运行（依赖自动安装）

如果系统已安装 `pip` 且网络通畅，也可直接运行脚本，首次执行时自动安装缺失模块（需在脚本头部添加 `import pip; pip.main(["install", …])`，但本工具未内置自动安装逻辑。建议使用方法一）。

### 3.3 项目文件结构

```
PDF514_filter/
├── pdf_filter.py          # 主执行脚本
├── requirements.txt       # 依赖库清单
├── README.md              # 快速入门
├── examples/              # 示例输入/输出
│   ├── sample1.pdf
│   ├── sample2.pdf
│   └── sample_output.json
└── docs/                  # 用户手册（本文档）
```

### 3.4 `requirements.txt` 内容示例

```
PyPDF2>=3.0.0
tabulate>=0.9.0
click>=8.1.0
python-dateutil>=2.8.0
```

---

## 4. 命令行参数说明

`pdf_filter.py` 使用 `click` 库定义命令行接口，支持以下参数：

### 4.1 必选参数

| 参数 | 缩写 | 类型 | 说明 |
|------|------|------|------|
| `--path` | `-p` | TEXT | 待筛选 PDF 文件或目录路径（支持通配符 `*.pdf`）。一次只能指定一个路径。 |

### 4.2 筛选条件参数

| 参数 | 缩写 | 类型 | 说明 |
|------|------|------|------|
| `--status` | `-s` | TEXT | 基于 PDF 文件状态筛选。内置状态：`all`, `unscanned`, `scanned`。可自定义（需配合配置文件）。 |
| `--min-size` | `-z` | INTEGER（KB） | 文件最小大小（KB）。例如 `--min-size 100` 表示 ≥100KB。 |
| `--max-size` | `-Z` | INTEGER（KB） | 文件最大大小（KB）。 |
| `--before-date` | `-b` | TEXT | 创建日期在此日期之前（YYYY-MM-DD）。 |
| `--after-date` | `-a` | TEXT | 创建日期在此日期之后（YYYY-MM-DD）。 |
| `--contains` | `-c` | TEXT | PDF 文本内容包含此字符串（正则表达式，不区分大小写）。 |
| `--creator` | `-C` | TEXT | 元数据中作者/创建者包含此字符串。 |

### 4.3 逻辑与控制参数

| 参数 | 缩写 | 类型 | 说明 |
|------|------|------|------|
| `--logic` | `-l` | TEXT | 多条件组合逻辑。可选值：`AND`（默认）、`OR`。使用 `AND` 时所有条件均需满足；使用 `OR` 时满足任一条件即匹配。 |
| `--output` | `-o` | TEXT | 输出文件路径。若不指定，结果打印至标准输出。 |
| `--format` | `-f` | TEXT | 输出格式。可选值：`table`（默认）、`json`。 |
| `--include` | `-i` | TEXT | 额外筛选属性（键值对逗号分割，如 `--include "language=en, encrypted=false"`）。 |
| `--verbose` | `-v` | FLAG | 详细模式，显示处理进度和每个文件的判定细节。 |

### 4.4 全局参数

| 参数 | 缩写 | 说明 |
|------|------|------|
| `--help` | `-h` | 显示帮助信息并退出。 |
| `--version` | 无 | 显示版本号并退出。 |

> **提示**：若未指定任何筛选条件（即不使用 `--status`、`--contains` 等），则默认输出**所有** PDF 文件（等效于 `--status all`）。

---

## 5. 使用示例

### 5.1 基础用法：输出目录下所有 PDF 文件（表格形式）

```bash
python pdf_filter.py -p ./documents/
```

输出示例：

| File | Size (KB) | Pages | Creator | Created |
|------|-----------|-------|---------|---------|
| report_2023.pdf | 1245 | 15 | JohnDoe | 2023-06-01 |
| invoice_001.pdf | 234 | 2 | AcmeCorp | 2023-07-12 |
| contract_signed.pdf | 3872 | 48 | LegalDept | 2023-05-20 |

### 5.2 AND 组合筛选：寻找 2024 年创建、大小在 500KB 到 5MB 之间、且包含“signed”文本的文件

```bash
python pdf_filter.py -p ./docs/ --after-date 2024-01-01 --min-size 500 --max-size 5120 --contains "signed" --logic AND
```

命令执行过程：
1. 解析 `--after-date` 和 `--min-size`、`--max-size` 和 `--contains` 条件。
2. 遍历 `./docs/` 下所有 `.pdf` 文件。
3. 仅当所有条件同时满足时，文件才进入结果集。
4. 输出匹配文件列表（默认表格）。

### 5.3 OR 组合筛选：查找状态为“已扫描”或创建日期早于 2020 年 1 月 1 日的文件

```bash
python pdf_filter.py -p ~/PDFs/ --status scanned --before-date 2020-01-01 --logic OR
```

注意：`--status` 参数的值 `scanned` 是内置状态，可通过配置文件自定义。OR 逻辑下，只要文件满足“状态为 scanned”或“创建日期早于 2020-01-01”，即被选中。

### 5.4 输出 JSON 到文件

```bash
python pdf_filter.py -p ./invoices/ --contains "paid" --format json -o paid_invoices.json
```

生成的 `paid_invoices.json` 内容示例：

```json
[
  {
    "file": "./invoices/2023_10_15.pdf",
    "size_kb": 1024,
    "pages": 3,
    "creator": "BillingSys",
    "created": "2023-10-14",
    "status": "scanned",
    "contains_paid": true
  },
  {
    "file": "./invoices/2024_01_20.pdf",
    "size_kb": 789,
    "pages": 2,
    "creator": "BillingSys",
    "created": "2024-01-19",
    "status": "scanned",
    "contains_paid": true
  }
]
```

### 5.5 结合 `--include` 自定义属性筛选

假设 PDF 元数据中包含自定义字段（如 `company`），可通过 `--include` 传入筛选：

```bash
python pdf_filter.py -p ./client_docs/ --include "company=Acme Corp, revenue>1000"
```

> 注意：`--include` 暂仅支持字符串精确匹配和数字大于（`>`）比较。

### 5.6 详细模式（调试用）

```bash
python pdf_filter.py -p ./test/ --verbose -s scanned --contains "final"
```

详细输出示例：

```
[VERBOSE] Processing file: ./test/draft_v1.pdf
  - Status: unscanned → 跳过 (need 'scanned')
[VERBOSE] Processing file: ./test/report_final.pdf
  - Status: scanned → 通过
  - Text contains 'final' → 通过
  - Result: MATCH
```

---

## 6. 输出格式说明

### 6.1 表格格式（默认）

- 使用 `tabulate` 库，带表头的网格对齐输出。
- 列包括：`File`（相对路径）、`Size (KB)`（整数）、`Pages`（整数）、`Creator`（字符串）、`Created`（YYYY-MM-DD）、`Status`（预定义或自定义）。
- 在终端中自动适应列宽。

### 6.2 JSON 格式（`--format json`）

- 输出一个 JSON 数组，每个元素代表一个匹配文件。
- 字段包含 `file`、`size_kb`、`pages`、`creator`、`created`、`status`。
- 若使用了 `--contains` 或 `--include`，还会额外输出 `contains_<keyword>` 或自定义字段的匹配结果。
- 编码为 UTF-8。

### 6.3 无匹配结果

- 当不满足任何筛选条件时，表格输出仅显示列标题（无数据行）；JSON 输出则为空数组 `[]`。

### 6.4 统计摘要（自动附加）

- 在普通输出末尾，会显示一行摘要：
  ```
  Total files scanned: 150, Matched: 23, Skipped: 127
  ```

---

## 7. 常见问题与故障排除

### 7.1 安装问题

**Q: `pip install` 失败，提示找不到 PyPDF2。**  
**A:** 检查 Python 版本（应≥3.6）。若为旧版本，请升级 Python。也可尝试使用 `python -m pip install PyPDF2==3.0.0` 指定版本。

**Q: 在 macOS/Linux 上执行 `python pdf_filter.py` 报错 `ModuleNotFoundError: No module named 'PyPDF2'`。**  
**A:** 可能未激活虚拟环境，或虽已安装但安装到了系统级目录。请确认虚拟环境已激活，并执行 `pip list | grep PyPDF2` 检查。

### 7.2 运行问题

**Q: 工具运行缓慢，处理 1000 个 PDF 需要数分钟。**  
**A:** 原因可能为每个 PDF 都需要解析元数据及提取文本。建议：
- 使用 `--contains` 时尽量缩小搜索范围（如先按日期筛选）。
- 若仅需元数据筛选，避免使用 `--contains`（该参数需要提取全文）。
- 升级硬件或使用 SSD。

**Q: 某些 PDF 无法解析，报 `PyPDF2.errors.PdfReadError`。**  
**A:** 可能文件损坏或加密。本工具默认跳过无法解析的文件并打印警告。可通过 `--verbose` 查看具体错误。若文件受密码保护，本工具暂不支持解密。

**Q: `--before-date` 和 `--after-date` 不按预期工作。**  
**A:** 检查 PDF 元数据中 `CreationDate` 字段是否存在。有时 PDF 生成工具不写入创建日期，工具会以文件系统修改日期作为备选（请确认配置中 `FALLBACK_TO_MODIFIED_DATE` 是否为 `true`）。可在 `--verbose` 模式下查看实际读取的日期。

**Q: 使用 `--status scanned` 但没有任何结果。**  
**A:** 内置状态是通过 PDF 元数据中的自定义标记来识别的。确保您已通过某种方式为 PDF 标记了 `scanned` 状态（例如使用 `pdfstatus` 辅助工具）。我们提供 `pdf_status_tagger.py` 示例脚本（位于 `examples/` 目录下）。若想使用默认所有文件均匹配，可使用 `--status all`。

### 7.3 输出问题

**Q: JSON 输出中文乱码。**  
**A:** 可能因为终端或重定向文件未使用 UTF-8 编码。请确保您的环境变量 `LC_ALL=en_US.UTF-8`（Linux/macOS），或使用 `chcp 65001`（Windows）。输出 JSON 文件时默认以 UTF-8 写入。

**Q: 表格输出在终端中显示错位。**  
**A:** 可能是终端字体不支持空格等宽。请使用等宽字体（如 Courier New、Consolas、Monaco）。或切换为 JSON 格式。

### 7.4 进阶自定义

**Q: 我想增加新的筛选条件（如根据 PDF 标题长度筛选）。**  
**A:** 您可以直接修改 `pdf_filter.py` 中的 `add_custom_filter` 函数（位于文件末尾），或通过编写插件（参见 `docs/PLUGIN.md`）。欢迎提交 Pull Request。

**Q: 能否使用通配符 `*` 指定多个路径？**  
**A:** 当前版本仅支持单个路径（可为目录或带通配符的路径）。例如 `--path "*.pdf"` 会在当前目录下查找所有 PDF；不支持空格分割的多个路径。若需多个路径，请使用系统通配符：`./dir1/*.pdf ./dir2/*.pdf`（需要引号保护空格）。

---

## 8. 配置文件说明（进阶）

本工具支持通过 `config.yaml`（位于执行目录或用户配置目录 `~/.pdf514/`）自定义状态和默认参数。配置文件示例：

```yaml
# config.yaml
status:
  signed:
    metadata_field: "/Status"
    value: "signed"
  unsigned:
    metadata_field: "/Status"
    value: "unsigned"
  reviewed:
    metadata_field: "/ReviewStatus"
    value: "ok"

defaults:
  logic: AND
  format: table
  fallback_to_modified_date: true
  max_concurrent_files: 10  # 并发解析数量（实验性）
```

- 当通过 `--status signed` 时，工具会读取 PDF 元数据字段 `/Status` 并检查其值是否等于 `signed`。
- 若不配置，内置状态仅支持 `all`、`scanned`、`unscanned`（`scanned` 对应元数据存在标志）。

---

## 9. 卸载与清理

- 删除项目文件夹 `PDF514_filter/` 即可完全移除。
- 若使用了虚拟环境，删除 `venv/` 目录。
- 全局安装的依赖可通过 `pip uninstall -y -r requirements.txt`