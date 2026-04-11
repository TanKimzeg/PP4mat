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


def fix_document(config: Config, fixed_dir: str = "./fixed_docs") -> FixResult | None:
    """根据当前 rules.yaml 对可修复项进行自动修复。"""

    docx_path = config.docx
    format_config: FormatConfig = config.format_config

    os.makedirs(fixed_dir, exist_ok=True)

    doc: DocumentObject = Document(docx_path)
    structure = DocumentStructure(doc)

    fixed_count = 0

    # 1) 标题修复（Heading1-3）
    for idx, p in enumerate(doc.paragraphs):
        level = utils.match_heading_level(p)
        if level is None: continue
        cfg = utils.config_for_level(format_config, level)
        if not cfg: continue

        if any(p.text.strip().replace(" ", "").replace("\u3000", "").startswith(s) for s in ["参考文献", "致谢", "附录", "独创性声明", "摘要", "Abstract", "关键词", "Keywords"]): 
            continue # 避免误修复这些章节标题（可能被错误识别为 Heading1-3）
        changed = False
        if cfg.get('alignment') is not None:
            changed |= _set_alignment(p, _alignment_from_cfg(cfg.get('alignment')))
        if cfg.get('line_spacing') is not None:
            changed |= _set_line_spacing_times(p, float(cfg['line_spacing']))

        changed |= _apply_run_font_and_size(p, cfg)

        if changed:
            fixed_count += 1
            loc = structure.get(idx)
            logger.info(f"修复标题{level}: P{idx} [{loc.short()}] {p.text.strip()[:30]}...")

    # 2) 正文修复（仅对 utils.get_body_normal_paragraphs 筛出的段落）
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
            if any(p.text.strip().replace(" ", "").replace("\u3000", "").startswith(s) for s in ["参考文献", "致谢", "附录", "独创性声明", "摘要", "Abstract", "关键词", "Keywords"]): 
                continue # 避免误修复这些章节标题（可能被错误识别为 Heading1-3）
            try:
                idx = doc.paragraphs.index(p)
            except ValueError:
                idx = -1
            changed = False

            if tcfg.get('alignment') is not None:
                changed |= _set_alignment(p, _alignment_from_cfg(tcfg.get('alignment')))
            if tcfg.get('line_spacing') is not None:
                changed |= _set_line_spacing_times(p, float(tcfg['line_spacing']))

            # changed |= _apply_run_font_and_size(p, tcfg)

            if changed:
                fixed_count += 1
                if idx >= 0:
                    loc = structure.get(idx)
                    logger.info(f"修复正文: P{idx} [{loc.short()}] {p.text.strip()[:30]}...")

    # 3) 图题修复
    fcfg = format_config.figure_config
    if fcfg:
        figure_caps = utils.get_figure_caption_paragraphs(doc)
        for p in figure_caps:
            try:
                idx = doc.paragraphs.index(p)
            except ValueError:
                idx = -1
            changed = False
            if fcfg.get('alignment') is not None:
                changed |= _set_alignment(p, _alignment_from_cfg(fcfg.get('alignment')))
            if fcfg.get('line_spacing') is not None:
                changed |= _set_line_spacing_times(p, float(fcfg['line_spacing']))
            changed |= _apply_run_font_and_size(p, fcfg)
            if changed:
                fixed_count += 1
                if idx >= 0:
                    loc = structure.get(idx)
                    logger.info(f"修复图题: P{idx} [{loc.short()}] {p.text.strip()[:30]}...")

    # 4) 表题修复
    tbcfg = format_config.table_config
    if tbcfg:
        table_caps = utils.get_table_caption_paragraphs(doc)
        for p in table_caps:
            try:
                idx = doc.paragraphs.index(p)
            except ValueError:
                idx = -1
            changed = False
            if tbcfg.get('alignment') is not None:
                changed |= _set_alignment(p, _alignment_from_cfg(tbcfg.get('alignment')))
            if tbcfg.get('line_spacing') is not None:
                changed |= _set_line_spacing_times(p, float(tbcfg['line_spacing']))
            changed |= _apply_run_font_and_size(p, tbcfg)
            if changed:
                fixed_count += 1
                if idx >= 0:
                    loc = structure.get(idx)
                    logger.info(f"修复表题: P{idx} [{loc.short()}] {p.text.strip()[:30]}...")

    # 5) 参考文献修复（仅 reference 分段）
    rcfg = format_config.reference_config
    if rcfg:
        ref_paras = sections.get('参考文献', [])
        for p in ref_paras:
            try:
                idx = doc.paragraphs.index(p)
            except ValueError:
                idx = -1
            changed = False
            if rcfg.get('alignment') is not None:
                changed |= _set_alignment(p, _alignment_from_cfg(rcfg.get('alignment')))
            if rcfg.get('line_spacing') is not None:
                changed |= _set_line_spacing_times(p, float(rcfg['line_spacing']))
            changed |= _apply_run_font_and_size(p, rcfg)
            if changed:
                fixed_count += 1
                if idx >= 0:
                    loc = structure.get(idx)
                    logger.info(f"修复参考文献: P{idx} [{loc.short()}] {p.text.strip()[:30]}...")

    if fixed_count <= 0:
        return None

    base = os.path.basename(docx_path)
    out_path = os.path.join(fixed_dir, base)
    doc.save(out_path)
    return FixResult(fixed_path=out_path, fixed_count=fixed_count)
