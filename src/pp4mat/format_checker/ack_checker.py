from __future__ import annotations
from typing import Any

from docx.document import Document as DocumentObject
from docx.text.paragraph import Paragraph

from pp4mat.config_converter import FormatConfig
from pp4mat.format_checker.protocols import FormatChecker, FormatErrors
from pp4mat.format_checker.utils import (
    get_effective_alignment,
    get_effective_fonts,
    get_effective_font_pt_size,
    get_paragraph_index,
    get_effective_line_spacing,
    Formatter
)
from pp4mat.logger import setup_logger

logger = setup_logger(__package__)

class AcknowledgementChecker(FormatChecker):
    def __init__(self, paragraphs: list[Paragraph], doc: DocumentObject, config: FormatConfig, errors: FormatErrors) -> None:
        self.paragraphs = paragraphs
        self.doc = doc
        self.config = config
        self.errors = errors
    
    def check_format(self) -> None:
        self.acknowledgement_checker(self.paragraphs, self.doc, self.config, self.errors)
        return None

    @staticmethod
    def acknowledgement_checker(paras: list[Paragraph], document: DocumentObject, format_config: FormatConfig, errors: FormatErrors) -> None:
        """致谢检查：字体/字号/对齐/行距（按 rules.yaml 的 acknowledgement 配置）。

        依赖 utils.get_sections() 提供 sections['致谢']。
        默认跳过第一个 "致谢" 标题段落。
        """

        cfg = format_config.acknowledgement_config
        if not cfg:
            return

        # 通常第一个是“致谢”标题
        body = paras[1:] if len(paras) >= 2 else []

        expected_cn = cfg.get("font_chinese")
        expected_en = cfg.get("font_western")
        expected_size = cfg.get("font_size")
        expected_alignment = cfg.get("alignment")
        expected_line_spacing = cfg.get("line_spacing")

        bucket = errors.setdefault("致谢检测", [])

        for p in body:
            if len(p.text.strip()) < 1: continue # 跳过空行

            idx = get_paragraph_index(p, document)
            loc_prefix = f"P{idx} " if idx >= 0 else ""

            # 对齐
            if expected_alignment is not None:
                got_align = get_effective_alignment(p, document)
                if got_align != expected_alignment:
                    bucket.append(f"{loc_prefix}致谢对齐错误：期望 {Formatter.fmt_align(expected_alignment)}，实际 {Formatter.fmt_align(got_align)}")

            # 行距
            if expected_line_spacing is not None:
                got_ls = get_effective_line_spacing(p)
                if got_ls is None or abs(float(got_ls) - float(expected_line_spacing)) > 0.05:
                    bucket.append(f"{loc_prefix}致谢行距错误：期望 {expected_line_spacing}，实际 {got_ls}")

            # 字体（中西）
            got_cn, got_en = get_effective_fonts(p)
            if expected_cn and got_cn and got_cn != expected_cn:
                bucket.append(f"{loc_prefix}致谢中文字体错误：期望 {expected_cn}，实际 {got_cn}")
            elif expected_cn and not got_cn:
                bucket.append(f"{loc_prefix}致谢中文字体缺失：期望 {expected_cn}")

            if expected_en and got_en and got_en != expected_en:
                bucket.append(f"{loc_prefix}致谢西文字体错误：期望 {expected_en}，实际 {got_en}")
            elif expected_en and not got_en:
                bucket.append(f"{loc_prefix}致谢西文字体缺失：期望 {expected_en}")

            # 字号
            if expected_size is not None:
                size = get_effective_font_pt_size(p)
                if size and abs(float(size) - float(expected_size)) > 0.01:
                    bucket.append(f"{loc_prefix}致谢字号错误：期望 {Formatter.fmt_font_pt_size(expected_size)}，实际 {Formatter.fmt_font_pt_size(size)}")
