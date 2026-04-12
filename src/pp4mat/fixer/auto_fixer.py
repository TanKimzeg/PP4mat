from __future__ import annotations

import os
from dataclasses import dataclass

from docx import Document
from docx.document import Document as DocumentObject
from docx.oxml.ns import qn

from pp4mat.config_converter.config_handle import Config, FormatConfig
from pp4mat.format_checker import utils
from pp4mat.logger import setup_logger
from pp4mat.skillhub.location import DocumentStructure

logger = setup_logger(__package__)


@dataclass
class FixResult:
    fixed_path: str
    fixed_count: int
    report_lines: list[str]


def _set_run_eastasia_font(run, font_name: str) -> None:
    """尽力设置东亚字体（不保证所有 run 都有 rPr/rFonts）。"""
    try:
        rPr = run._element.get_or_add_rPr()
        rFonts = rPr.get_or_add_rFonts()
        rFonts.set(qn('w:eastAsia'), font_name)
    except Exception:
        pass


def _set_run_western_font(run, font_name: str) -> None:
    """尽力设置西文字体（ascii/hAnsi）。"""
    try:
        rPr = run._element.get_or_add_rPr()
        rFonts = rPr.get_or_add_rFonts()
        rFonts.set(qn('w:ascii'), font_name)
        rFonts.set(qn('w:hAnsi'), font_name)
    except Exception:
        pass


def _set_alignment(paragraph, alignment) -> bool:
    if paragraph.alignment != alignment:
        paragraph.alignment = alignment
        return True
    return False


def _set_line_spacing_times(paragraph, times: float) -> bool:
    pf = paragraph.paragraph_format
    old = pf.line_spacing
    if old != times:
        pf.line_spacing = times
        return True
    return False


def _alignment_from_cfg(val):
    # val 已在 config_converter.align_converter 转为 WD_PARAGRAPH_ALIGNMENT
    return val


def _apply_run_font_and_size(p, cfg: dict) -> bool:
    """对段落中有内容的 runs 应用字体/字号。返回是否有修改。"""
    from docx.shared import Pt

    expected_cn = cfg.get('font_chinese') or cfg.get('font_name')
    expected_en = cfg.get('font_western')
    expected_size = cfg.get('font_size')

    changed = False
    if not (expected_cn or expected_en or expected_size):
        return False

    for run in p.runs:
        if not (run.text or '').strip():
            continue

        # 中文字体：优先写 eastAsia（同时把 run.font.name 设为中文字体，利于 Word UI 显示一致）
        if expected_cn:
            if run.font.name != expected_cn:
                run.font.name = expected_cn
                changed = True
            _set_run_eastasia_font(run, expected_cn)

        # 西文字体：写 ascii/hAnsi（不覆盖 run.font.name，以免把中文显示也改掉；仅在有期望时设置）
        if expected_en:
            _set_run_western_font(run, expected_en)

        if expected_size:
            if run.font.size is None or abs(run.font.size.pt - float(expected_size)) > 0.01:
                run.font.size = Pt(float(expected_size))
                changed = True

    return changed


def _set_indentation(paragraph, cfg: dict) -> bool:
    """根据配置设置段落缩进。

    支持字段（存在则应用）：
    - left_indent_cm: 左缩进（厘米）
    - first_line_indent_cm: 首行缩进（厘米）
    - left_indent_chars: 左缩进（按字符，近似换算为 cm；只作粗略修复）
    - first_line_indent_chars: 首行缩进（按字符，近似换算为 cm；只作粗略修复）

    说明：python-docx 底层是 Length（EMU）。这里用 docx.shared.Cm。
    """
    from docx.shared import Cm

    pf = paragraph.paragraph_format
    changed = False

    def _set_len(attr: str, cm_val: float) -> None:
        nonlocal changed
        cur = getattr(pf, attr)
        target = Cm(float(cm_val))
        if cur != target:
            setattr(pf, attr, target)
            changed = True

    # 优先 cm 配置
    if cfg.get("left_indent_cm") is not None:
        _set_len("left_indent", float(cfg["left_indent_cm"]))
    if cfg.get("first_line_indent_cm") is not None:
        _set_len("first_line_indent", float(cfg["first_line_indent_cm"]))

    # 字符配置兜底：按 1 字符≈0.37cm 粗略换算（常见宋体小四/五号量级）
    char_to_cm = 0.37
    if cfg.get("left_indent_chars") is not None and cfg.get("left_indent_cm") is None:
        _set_len("left_indent", float(cfg["left_indent_chars"]) * char_to_cm)
    if cfg.get("first_line_indent_chars") is not None and cfg.get("first_line_indent_cm") is None:
        _set_len("first_line_indent", float(cfg["first_line_indent_chars"]) * char_to_cm)

    return changed


def fix_document(config: Config, fixed_dir: str = "./fixed_docs") -> FixResult | None:
    """根据当前 rules.yaml 对可修复项进行自动修复。"""

    docx_path = config.docx
    format_config: FormatConfig = config.format_config

    os.makedirs(fixed_dir, exist_ok=True)

    doc: DocumentObject = Document(docx_path)
    utils.attach_paragraph_indices(doc)
    structure = DocumentStructure(doc)

    fixed_count = 0
    report_lines: list[str] = []

    def _skip_special(p_text: str) -> bool:
        return any(
            (p_text or "").strip().replace(" ", "").replace("\u3000", "").startswith(s)
            for s in ["参考文献", "致谢", "附录", "独创性声明", "摘要", "Abstract", "关键词", "Keywords"]
        )

    def _is_toc_idx(i: int) -> bool:
        try:
            loc = structure.get(i)
            return (loc.short() or "").strip() == "目录"
        except Exception:
            return False

    # 1) 标题修复（与 header_checker 对齐：1~3 级标题）
    for idx, p in enumerate(doc.paragraphs):
        if _is_toc_idx(idx):
            continue
        level = utils.match_heading_level(p)
        if level is None:
            continue
        cfg = utils.config_for_level(format_config, level)
        if not cfg:
            continue
        if _skip_special(p.text):
            continue

        changed = False
        if cfg.get('alignment') is not None:
            changed |= _set_alignment(p, _alignment_from_cfg(cfg.get('alignment')))
        if cfg.get('line_spacing') is not None:
            changed |= _set_line_spacing_times(p, float(cfg['line_spacing']))
        changed |= _apply_run_font_and_size(p, cfg)

        if changed:
            fixed_count += 1
            loc = structure.get(idx)
            msg = f"修复标题{level}: P{idx} [{loc.short()}] {p.text.strip()[:30]}..."
            report_lines.append(msg)
            logger.info(msg)

    # 2) 正文修复（与 text_checker 对齐：对齐/行距/（可选）字号/字体）
    sections = utils.get_sections(doc)
    body_normal = utils.get_body_normal_paragraphs(
        sections,
        exclusion=utils.get_table_caption_paragraphs(doc)
        + utils.get_figure_caption_paragraphs(doc)
        + utils.get_code_caption_paragraphs(doc),
    )

    tcfg = format_config.text_config
    if tcfg:
        for p in body_normal:
            if _skip_special(p.text):
                continue

            idx = utils.get_paragraph_index(p, document=doc)
            if idx >= 0 and _is_toc_idx(idx):
                continue

            changed = False
            if tcfg.get('alignment') is not None:
                changed |= _set_alignment(p, _alignment_from_cfg(tcfg.get('alignment')))
            if tcfg.get('line_spacing') is not None:
                changed |= _set_line_spacing_times(p, float(tcfg['line_spacing']))

            # 新增：缩进修复
            changed |= _set_indentation(p, tcfg)

            # 正文也需要修复字体/字号（之前被注释导致 text_checker 报错但不修复）
            changed |= _apply_run_font_and_size(p, tcfg)

            if changed:
                fixed_count += 1
                if idx >= 0:
                    loc = structure.get(idx)
                    msg = f"修复正文: P{idx} [{loc.short()}] {p.text.strip()[:30]}..."
                else:
                    msg = f"修复正文: {p.text.strip()[:30]}..."
                report_lines.append(msg)
                logger.info(msg)

    # 3) 图题修复（与 figure_checker 思路一致：修复 caption 段落）
    fcfg = format_config.figure_config
    if fcfg:
        figure_caps = utils.get_figure_caption_paragraphs(doc)
        for p in figure_caps:
            idx = utils.get_paragraph_index(p, document=doc)
            if idx >= 0 and _is_toc_idx(idx):
                continue
            changed = False
            if fcfg.get('alignment') is not None:
                changed |= _set_alignment(p, _alignment_from_cfg(fcfg.get('alignment')))
            if fcfg.get('line_spacing') is not None:
                changed |= _set_line_spacing_times(p, float(fcfg['line_spacing']))
            changed |= _set_indentation(p, fcfg)
            changed |= _apply_run_font_and_size(p, fcfg)
            if changed:
                fixed_count += 1
                if idx >= 0:
                    loc = structure.get(idx)
                    msg = f"修复图题: P{idx} [{loc.short()}] {p.text.strip()[:30]}..."
                else:
                    msg = f"修复图题: {p.text.strip()[:30]}..."
                report_lines.append(msg)
                logger.info(msg)

    # 4) 表题修复
    tbcfg = format_config.table_config
    if tbcfg:
        table_caps = utils.get_table_caption_paragraphs(doc)
        for p in table_caps:
            idx = utils.get_paragraph_index(p, document=doc)
            if idx >= 0 and _is_toc_idx(idx):
                continue
            changed = False
            if tbcfg.get('alignment') is not None:
                changed |= _set_alignment(p, _alignment_from_cfg(tbcfg.get('alignment')))
            if tbcfg.get('line_spacing') is not None:
                changed |= _set_line_spacing_times(p, float(tbcfg['line_spacing']))
            changed |= _set_indentation(p, tbcfg)
            changed |= _apply_run_font_and_size(p, tbcfg)
            if changed:
                fixed_count += 1
                if idx >= 0:
                    loc = structure.get(idx)
                    msg = f"修复表题: P{idx} [{loc.short()}] {p.text.strip()[:30]}..."
                else:
                    msg = f"修复表题: {p.text.strip()[:30]}..."
                report_lines.append(msg)
                logger.info(msg)

    # 5) 参考文献修复（对齐/行距/字体字号）
    rcfg = format_config.reference_config
    if rcfg:
        ref_paras = sections.get('参考文献', [])
        for p in ref_paras[1:]:  # 通常第一个段落是 "参考文献" 标题，跳过
            if len(p.text.strip()) < 5:  # 过短的参考文献条目不修复（可能是误识别的 TOC 条目）
                continue
            idx = utils.get_paragraph_index(p, document=doc)
            if idx >= 0 and _is_toc_idx(idx):
                continue
            changed = False
            if rcfg.get('alignment') is not None:
                changed |= _set_alignment(p, _alignment_from_cfg(rcfg.get('alignment')))
            if rcfg.get('line_spacing') is not None:
                changed |= _set_line_spacing_times(p, float(rcfg['line_spacing']))

            # 参考文献：强制缩进为 0
            changed |= _set_indentation(p, rcfg)

            changed |= _apply_run_font_and_size(p, rcfg)
            if changed:
                fixed_count += 1
                if idx >= 0:
                    loc = structure.get(idx)
                    msg = f"修复参考文献: P{idx} [{loc.short()}] {p.text.strip()[:30]}..."
                else:
                    msg = f"修复参考文献: {p.text.strip()[:30]}..."
                report_lines.append(msg)
                logger.info(msg)

    if fixed_count <= 0:
        return None

    base = os.path.basename(docx_path)
    out_path = os.path.join(fixed_dir, base)
    doc.save(out_path)
    return FixResult(fixed_path=out_path, fixed_count=fixed_count, report_lines=report_lines)
