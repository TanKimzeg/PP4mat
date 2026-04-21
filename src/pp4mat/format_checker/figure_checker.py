from typing import Any
from functools import singledispatch
from docx.document import Document as DocumentObject

from pp4mat.logger import setup_logger
from pp4mat.format_checker.utils import (
    get_effective_alignment,
    get_effective_fonts,
    get_effective_font_pt_size,
    Formatter,
)
from pp4mat.config_converter import FormatConfig
from pp4mat.format_checker.protocols import FormatChecker, FormatErrors

logger = setup_logger(__package__, console=True, file=False)


@singledispatch  # TODO: unable to find the expected picture by Shape.Type
def figure_check(doc: Any, format_config: FormatConfig, errors: FormatErrors) -> None:
    """默认实现：基于 Word COM(win32) 检查图片与图题。"""
    logger.info("检查图片格式...")
    config = format_config.figure_config
    if config is None:
        logger.warning("图片格式配置未提供，跳过检查。")
        return

    picture_cnt = 0
    for shape in doc.Shapes:
        if shape.Type == 17:  # msoPicture
            picture_cnt += 1
            if shape.Anchor.Paragraphs.Count > 0:
                anchor_p = shape.Anchor.Paragraphs(1)
                next_p = anchor_p.Next()
                while next_p is not None and next_p.Range.Text.strip() == "":
                    next_p = next_p.Next()
                if next_p is None:
                    logger.error(f"图片{picture_cnt}未找到对应的标题段落，请检查文档格式。")
                    errors["图片检测"].append(f"图片{picture_cnt}未找到对应的标题段落")
                    continue
                if not any([next_p.Range.Text.strip().startswith(f"图{picture_cnt} "),
                             next_p.Range.Text.strip().startswith(f"图 {picture_cnt} ")]):
                    logger.error(
                        f"图片{picture_cnt}的标题格式错误，应该以\"图{picture_cnt} \"开头，但实际为：{next_p.Range.Text.strip()}。请注意空格、编号。"
                    )
                    errors["图片检测"].append(
                        f"图片{picture_cnt}的标题格式错误，应该以\"图{picture_cnt} \"开头，但实际为：{next_p.Range.Text.strip()}。请注意空格、编号。"
                    )
                else:
                    logger.info(f"图片{picture_cnt}的标题格式正确：{next_p.Range.Text.strip()}")
            else:
                logger.error(f"图片{picture_cnt}未找到对应的标题段落，请检查文档格式。")
                errors["图片检测"].append(f"图片{picture_cnt}未找到对应的标题段落")


@figure_check.register
def _(document: DocumentObject, format_config: FormatConfig, errors: FormatErrors) -> None:
    """python-docx 实现：通过 runs 的 drawing 元素识别图片，并检查下一段是否为图题。"""
    config = format_config.figure_config

    def is_img(run: Any) -> bool:
        drawing_elements = run._element.xpath('.//w:drawing')
        for drawing in drawing_elements:
            if drawing.xpath('.//a:graphic'):
                return True
        return False

    paragraphs = document.paragraphs
    picture_cnt = 0
    for i, p in enumerate(paragraphs):
        if p.runs and any(is_img(run) for run in p.runs):
            if i + 1 < len(paragraphs):
                next_p = paragraphs[i + 1]
                if next_p.text.strip().startswith("图"):
                    picture_cnt += 1
                    if not any([next_p.text.strip().startswith(f"图{picture_cnt} "),
                                 next_p.text.strip().startswith(f"图 {picture_cnt} ")]):
                        logger.error(
                            f"图片{picture_cnt}的标题格式错误，应该以\"图{picture_cnt} \"开头，但实际为：\"{next_p.text.strip()}\"。请注意空格、编号。"
                        )
                        errors["图片检测"].append(
                            f"图片{picture_cnt}的标题格式错误，应该以\"图{picture_cnt} \"开头，但实际为：\"{next_p.text.strip()}\"。请注意空格、编号。"
                        )

                    if config is None:
                        continue

                    expected_alignment = config.get("alignment")
                    actual_alignment = get_effective_alignment(next_p, document=document)
                    if expected_alignment and actual_alignment != expected_alignment:
                        msg = (
                            f"图片{picture_cnt}的标题对齐方式错误，应该为{Formatter.fmt_align(expected_alignment)}，"
                            f"但实际为{Formatter.fmt_align(actual_alignment)}"
                        )
                        logger.error(msg)
                        errors["图片检测"].append(msg)

                    expected_font_size = config.get("font_size")
                    expected_cn = config.get("font_chinese") or config.get("font_name")
                    expected_en = config.get("font_western")

                    actual_font_size = get_effective_font_pt_size(next_p)
                    actual_cn, actual_en = get_effective_fonts(next_p)

                    if expected_font_size and actual_font_size and actual_font_size != expected_font_size:
                        msg = (
                            f"图片{picture_cnt}的标题字体大小错误，应该为{Formatter.fmt_font_pt_size(expected_font_size)}，"
                            f"但实际为{Formatter.fmt_font_pt_size(actual_font_size)}"
                        )
                        logger.error(msg)
                        errors["图片检测"].append(msg)

                    if expected_cn and actual_cn and actual_cn != expected_cn:
                        msg = f"图片{picture_cnt}的标题中文字体错误，应该为{expected_cn}，但实际为{actual_cn}"
                        logger.error(msg)
                        errors["图片检测"].append(msg)
                    if expected_en and actual_en and actual_en != expected_en:
                        msg = f"图片{picture_cnt}的标题西文字体错误，应该为{expected_en}，但实际为{actual_en}"
                        logger.error(msg)
                        errors["图片检测"].append(msg)
                else:
                    logger.warning(f"该对象不以\"图\"开头，可能不是图片：{next_p.text.strip()}")


class FigureChecker(FormatChecker):
    def __init__(self, doc: Any, config: FormatConfig, errors: FormatErrors) -> None:
        self.config = config
        self.doc = doc
        self.errors = errors

    def check_format(self) -> None:
        figure_check(self.doc, self.config, self.errors)
        return None

