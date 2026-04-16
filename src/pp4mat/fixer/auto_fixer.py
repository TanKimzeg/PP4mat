from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Iterable

from docx import Document
from docx.document import Document as DocumentObject
from docx.text.paragraph import Paragraph
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
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


def _set_alignment(paragraph: Paragraph, cfg: dict[str, Any]) -> bool:
    alignment: WD_PARAGRAPH_ALIGNMENT | None = cfg.get("alignment")
    if alignment and paragraph.alignment != alignment:
        paragraph.alignment = alignment
        return True
    return False


def _set_line_spacing_times(paragraph, cfg: dict[str, Any]) -> bool:
    times = cfg.get("line_spacing")
    pf = paragraph.paragraph_format
    old = pf.line_spacing
    if times and old != times:
        pf.line_spacing = times
        return True
    return False


def _apply_run_font_and_size(p, cfg: dict[str, Any]) -> bool:
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


def _set_indentation(paragraph, cfg: dict[str, Any]) -> bool:
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


def _apply_paragraph_by_cfg(p: Paragraph, cfg: dict) -> bool:
    """对单个段落应用 cfg（alignment/line_spacing/indent/font&size），返回是否修改。"""

    changed = False

    changed |= _set_alignment(p, cfg)

    changed |= _set_line_spacing_times(p, cfg)

    changed |= _set_indentation(p, cfg)
    changed |= _apply_run_font_and_size(p, cfg)

    return changed


def _fix_paragraphs(
    doc: DocumentObject,
    structure: DocumentStructure,
    paragraphs: Iterable[Paragraph],
    cfg: dict,
    *,
    label: str,
    report_lines: list[str],
    fixed_count: int,
    skip_fn,
    is_toc_idx_fn,
) -> int:
    """批量修复段落，返回累计 fixed_count（只在发生修改时 +1）。"""

    for p in paragraphs:
        if skip_fn(p.text):
            continue

        idx = utils.get_paragraph_index(p, document=doc)
        if idx >= 0 and is_toc_idx_fn(idx):
            continue

        if not (p.text or "").strip():
            continue

        if _apply_paragraph_by_cfg(p, cfg):
            fixed_count += 1
            if idx >= 0:
                loc = structure.get(idx)
                msg = f"{label}: P{idx} [{loc.short()}] {p.text.strip()[:30]}..."
            else:
                msg = f"{label}: {p.text.strip()[:30]}..."
            report_lines.append(msg)
            logger.info(msg)

    return fixed_count


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
            for s in ["独创性声明", "摘要", "Abstract", "关键词", "Keywords"]
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
        if utils.norm_text(p.text).startswith("参考文献："):
            cfg["alignment"] = WD_PARAGRAPH_ALIGNMENT.LEFT  # 参考文献标题左对齐
        elif utils.norm_text(p.text).startswith("附录："):
            cfg["alignment"] = WD_PARAGRAPH_ALIGNMENT.LEFT  # 附录标题左对齐

        changed = False
        changed |= _set_alignment(p, cfg)
        changed |= _set_line_spacing_times(p, cfg)
        changed |= _apply_run_font_and_size(p, cfg)

        if changed:
            fixed_count += 1
            loc = structure.get(idx)
            msg = f"修复标题{level}: P{idx} [{loc.short()}] {p.text.strip()[:30]}..."
            report_lines.append(msg)
            logger.info(msg)

    # 2) 正文/致谢/图题/表题/参考文献：使用统一批处理
    sections = utils.get_sections(doc)
    body_normal = utils.get_body_normal_paragraphs(
        sections,
        exclusion=utils.get_table_caption_paragraphs(doc)
        + utils.get_figure_caption_paragraphs(doc)
        + utils.get_code_caption_paragraphs(doc),
    )

    tcfg = format_config.text_config
    if tcfg:
        fixed_count = _fix_paragraphs(
            doc,
            structure,
            body_normal,
            tcfg,
            label="修复正文",
            report_lines=report_lines,
            fixed_count=fixed_count,
            skip_fn=_skip_special,
            is_toc_idx_fn=_is_toc_idx,
        )

    acfg = format_config.acknowledgement_config
    if acfg:
        ack_paras = sections.get("致谢", [])
        fixed_count = _fix_paragraphs(
            doc,
            structure,
            ack_paras[1:],  # 跳过“致谢”标题
            acfg,
            label="修复致谢",
            report_lines=report_lines,
            fixed_count=fixed_count,
            skip_fn=_skip_special,
            is_toc_idx_fn=_is_toc_idx,
        )

    fcfg = format_config.figure_config
    if fcfg:
        fixed_count = _fix_paragraphs(
            doc,
            structure,
            utils.get_figure_caption_paragraphs(doc),
            fcfg,
            label="修复图题",
            report_lines=report_lines,
            fixed_count=fixed_count,
            skip_fn=_skip_special,
            is_toc_idx_fn=_is_toc_idx,
        )

    tbcfg = format_config.table_config
    if tbcfg:
        fixed_count = _fix_paragraphs(
            doc,
            structure,
            utils.get_table_caption_paragraphs(doc),
            tbcfg,
            label="修复表题",
            report_lines=report_lines,
            fixed_count=fixed_count,
            skip_fn=_skip_special,
            is_toc_idx_fn=_is_toc_idx,
        )

    rcfg = format_config.reference_config
    if rcfg:
        ref_paras = sections.get('参考文献', [])
        fixed_count = _fix_paragraphs(
            doc,
            structure,
            ref_paras[1:],  # 通常第一个段落是标题
            rcfg,
            label="修复参考文献",
            report_lines=report_lines,
            fixed_count=fixed_count,
            skip_fn=_skip_special,
            is_toc_idx_fn=_is_toc_idx,
        )

    if fixed_count <= 0:
        return None

    base = os.path.basename(docx_path)
    out_path = os.path.join(fixed_dir, base)
    doc.save(out_path)
    return FixResult(fixed_path=out_path, fixed_count=fixed_count, report_lines=report_lines)
