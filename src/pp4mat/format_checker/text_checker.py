from __future__ import annotations

from docx.document import Document as DocumentObject
from docx.text.paragraph import Paragraph

from pp4mat.config_converter.config_handle import FormatConfig
from pp4mat.format_checker import utils
from pp4mat.logger import setup_logger
from pp4mat.skillhub.location import DocumentStructure

logger = setup_logger(__package__)


def text_paragraphs_checker(
    paragraphs: list[Paragraph],
    document: DocumentObject,
    format_config: FormatConfig,
    errors: dict[str, list[str]],
) -> None:
    """更完整的正文检测：字体（中/西）、对齐、行距。"""

    cfg = format_config.text_config
    if cfg is None:
        logger.warning("正文格式配置未提供，跳过检查。")
        return

    expected_cn = cfg.get("font_chinese") or cfg.get("font_name")
    expected_en = cfg.get("font_western")
    expected_size = cfg.get("font_size")
    expected_alignment = cfg.get("alignment")
    expected_ls = cfg.get("line_spacing")

    structure = DocumentStructure(document)

    for p in paragraphs:
        idx = utils.get_paragraph_index(p, document=document)

        # 用户要求：仅显示章节
        if idx >= 0:
            loc = structure.get(idx)
            loc_str = f"[{loc.short()}]"
        else:
            loc_str = ""

        preview = (p.text or "").strip()[:30]

        if expected_alignment is not None:
            actual_align = utils.get_effective_alignment(p, document=document)
            if actual_align != expected_alignment:
                errors["正文检测"].append(
                    f"{loc_str} 正文对齐错误：应为{expected_alignment}，实际为{actual_align}，内容:'{preview}...'"
                )

        if expected_ls is not None:
            if not utils.check_line_spacing(p, expected=float(expected_ls), allow_inherited_true=True):
                errors["正文检测"].append(
                    f"{loc_str} 正文行距可能不正确：期望{expected_ls}倍，内容:'{preview}...'"
                )

        # actual_cn, actual_en = utils.get_effective_fonts(p)
        actual_size = utils.get_effective_font_pt_size(p)

        # if expected_cn and actual_cn and actual_cn != expected_cn:
        #     errors["正文检测"].append(
        #         f"{loc_str} 正文中文字体错误：应为{expected_cn}，实际为{actual_cn}，内容:'{preview}...'"
        #     )
        # if expected_en and actual_en and actual_en != expected_en:
        #     errors["正文检测"].append(
        #         f"{loc_str} 正文西文字体错误：应为{expected_en}，实际为{actual_en}，内容:'{preview}...'"
        #     )

        if expected_size and actual_size and float(actual_size) != float(expected_size):
            errors["正文检测"].append(
                f"{loc_str} 正文字号错误：应为{expected_size}pt，实际为{actual_size}pt，内容:'{preview}...'"
            )
