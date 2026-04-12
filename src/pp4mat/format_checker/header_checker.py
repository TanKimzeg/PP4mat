from __future__ import annotations

from docx.document import Document as DocumentObject

from pp4mat.format_checker.utils import match_heading_level, config_for_level
from pp4mat.config_converter.config_handle import FormatConfig
from pp4mat.format_checker import utils
from pp4mat.logger import setup_logger
from pp4mat.skillhub.location import DocumentStructure

logger = setup_logger(__package__)


def header_checker(document: DocumentObject, format_config: FormatConfig, errors: dict[str, list[str]]) -> None:
    logger.info("检查小节标题格式(header_checker)...")

    structure = DocumentStructure(document)

    for i, p in enumerate(document.paragraphs):
        # 跳过目录区域（目录内的 toc 段落/条目不应作为正文标题检测）
        try:
            loc = structure.get(i)
            if (loc.short() or "").strip() == "目录":
                continue
        except Exception:
            pass

        if any(p.text.strip().replace(" ", "").replace("\u3000", "").startswith(s) for s in ["参考文献", "致谢", "附录", "独创性声明", "摘要", "Abstract", "关键词", "Keywords"]):
            continue  # 避免误修复这些章节标题（可能被错误识别为 Heading1-3）

        level = match_heading_level(p)
        if level is None:
            continue

        cfg = config_for_level(format_config, level)
        if not cfg:
            # 未配置则跳过
            continue

        loc = structure.get(i)
        loc_str = f"P{i} [{loc.short()}]"
        preview = (p.text or "").strip()[:30]

        # 对齐
        expected_align = cfg.get("alignment")
        actual_align = utils.get_effective_alignment(p, document=document)
        if expected_align is not None and actual_align != expected_align:
            errors["标题检测"].append(
                f"{loc_str} 标题{level}对齐错误：应为{expected_align}，实际为{actual_align}，内容:'{preview}...'"
            )

        # 行距（倍数）
        expected_ls = cfg.get("line_spacing")
        if expected_ls is not None:
            if not utils.check_line_spacing(p, expected=float(expected_ls), allow_inherited_true=True):
                errors["标题检测"].append(
                    f"{loc_str} 标题{level}行距可能不正确：期望{expected_ls}倍，内容:'{preview}...'"
                )

        # 字体（中文/西文）
        expected_cn = cfg.get("font_chinese") or cfg.get("font_name")
        expected_en = cfg.get("font_western")
        expected_size = cfg.get("font_size")

        actual_cn, actual_en = utils.get_effective_fonts(p)
        actual_size = utils.get_effective_font_pt_size(p)

        if expected_cn and actual_cn and actual_cn != expected_cn:
            errors["标题检测"].append(
                f"{loc_str} 标题{level}中文字体错误：应为{expected_cn}，实际为{actual_cn}，内容:'{preview}...'"
            )
        if expected_en and actual_en and actual_en != expected_en:
            errors["标题检测"].append(
                f"{loc_str} 标题{level}西文字体错误：应为{expected_en}，实际为{actual_en}，内容:'{preview}...'"
            )
        if expected_size and actual_size and float(actual_size) != float(expected_size):
            errors["标题检测"].append(
                f"{loc_str} 标题{level}字号错误：应为{expected_size}pt，实际为{actual_size}pt，内容:'{preview}...'"
            )
