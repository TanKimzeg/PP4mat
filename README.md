# 论文格式检测工具（Paper4mat）

基于 `python-docx` + `pywin32(Word COM)` 的毕业论文（设计）格式检测与自动修复工具，支持 **命令行** 与 **Web 前后端** 两种使用方式。

> Windows-only：由于依赖 Word COM（`pywin32`），仅支持 Windows x64。

## 功能概览

### 1) 文档结构/完整性

- [x] 章节完整性检查：封面/摘要/关键词/目录/正文/参考文献/附录等（基于 `utils.get_sections()`）
- [x] 目录检查：目录只允许到二级标题（禁止 2.1.2 这类三级）
- [x] 章节数量检查：目录章节数量不少于配置值（默认 5）
- [x] 字数检查：总字数不少于配置值（默认 10000）
- [x] 引用数量检查：正文引用（`[n]`）不少于配置值（默认 5）
- [x] 参考文献数量检查：不少于 15，其中英文不少于 2
- [x] 文献综述检测：检测是否存在综述相关内容（关键词启发式）

### 2) 格式检查（字体/字号/对齐/行距）

- [x] 标题（1~3级）格式检查：中西文字体分离（eastAsia / ascii+hAnsi），字号、对齐、行距
- [x] 正文段落格式检查：会排除目录/标题/图题/表题/代码段等后再检查
- [x] 图题格式检查（图下标题）
- [x] 表题格式检查（表上标题）
- [x] 参考文献格式检查
- [x] 致谢格式检查

### 3) 自动修复（输出到 `fixed_docs/`）

- [x] 自动修复标题（1~3级）
- [x] 自动修复正文（含缩进/行距/对齐/中西字体/字号）
- [x] 自动修复致谢（新增）
- [x] 自动修复图题/表题
- [x] 自动修复参考文献

> 自动修复不会修改原文件，会生成修复后的 docx 到 `fixed_docs/`。

## 前端效果

![preview](/doc/preview.png)

## 安装

### 平台要求

- Windows x64
- 本机安装 Microsoft Word（用于 COM 能力：提取封面文本框、目录兜底、图与图题关联等）

### 安装依赖

Python 依赖（以 `uv` 为例） ：

```shell
uv sync
uv pip install -e .
```

前端依赖：

```shell
cd ./frontend
npm install
```

## 使用方式

### 方式 A：命令行（生成 Markdown 报告）

入口：`src/pp4mat/paper4mat.py`

参数：

- `--docx`：论文 docx 路径
- `--config`：规则文件路径（默认 `./rules.yaml`，仓库内建议用 `./configs/rules.yaml`）
- `--output`：报告输出目录（默认 `./reports`）
- `--log_dir`：日志目录（默认 `./error_logs`）
- `--debug`：开启调试日志

输出：

- `reports/<filename>.md`

### 方式 B：Web（前后端）

后端为 FastAPI（`app/main.py`），提供接口：

- `GET /`：健康检查
- `GET /stats/`：获取累计统计（检测次数/修复次数）
- `POST /upload/`：上传并检测，返回报告内容
- `POST /fix/`：上传并自动修复，返回修复信息
- `GET /download/fixed/{filename}`：下载修复后的 docx

前端会调用：

- 上传并检测（显示报告）
- 自动修复并下载（显示修复条目与统计）

## 配置说明（rules.yaml）

规则文件：`configs/rules.yaml`

关键点：

- 字体字段采用 **中西分离** ：
  - `font_chinese`：写入/比对 `w:rFonts/@w:eastAsia`
  - `font_western`：写入/比对 `w:rFonts/@w:ascii` + `w:hAnsi`
- 字号：`font_size`（pt）
- 对齐：`alignment`（LEFT/CENTER/RIGHT/JUSTIFY/DISTRIBUTE）
- 行距：`line_spacing`（倍数，如 1.5）
- 参考文献支持缩进字段：`left_indent_cm` / `first_line_indent_cm`

## 开发模式

1. 启动后端（仅本机） ：

```shell
npm run api:dev
```

默认 `http://localhost:8000`

1. 启动前端：

```shell
npm run web:dev
```

- 前端默认监听 `127.0.0.1:5174`
- Vite 已将 `/upload` 等请求代理到 `http://localhost:8000`

## 生产模式（简要）

```shell
npm run api:serve
npm run web:build
npm run web:start
```
