import re
from pp4mat.logger import setup_logger
from pp4mat.format_checker.utils import (
    get_effective_alignment,
    get_effective_fonts,
    get_effective_font_pt_size,
    Formatter
)
from pp4mat.config_converter import FormatConfig
from pp4mat.format_checker.protocols import FormatChecker, FormatErrors
from docx.text.paragraph import Paragraph
from docx.document import Document as DocumentObject

logger = setup_logger(__package__)

class ReferenceChecker(FormatChecker):
    def __init__(self, paragraphs: list[Paragraph], doc: DocumentObject, config: FormatConfig, errors: FormatErrors) -> None:
        self.paragraphs = paragraphs
        self.doc = doc
        self.config = config
        self.errors = errors

    def check_format(self) -> None:
        self.reference_checker(self.paragraphs, self.doc, self.config, self.errors)
        return None

    @staticmethod
    def reference_checker(
            reference: list[Paragraph], 
            document: DocumentObject,
            format_config: FormatConfig, 
            errors: dict[str, list[str]]
        ) -> None:
        logger.info("检查参考文献格式...")
        config = format_config.reference_config
        if config is None:
            logger.warning("参考文献格式配置未提供，跳过检查。")
            return

        pattern = re.compile(r'^\[[1-9]\d*\]')
        cnt = 0
        en_cnt = 0
        for p in reference:
            if re.match(pattern, p.text.strip()):
                cnt += 1
                if all(char.isascii() for char in p.text):
                    en_cnt += 1

        if cnt < config["min_count"]:
            logger.error(f"参考文献数量少于{config['min_count']}条，当前数量为{cnt}条，请检查！")
            errors["参考文献检测"].append(f"参考文献数量少于{config['min_count']}条，当前数量为{cnt}条")

        else:
            logger.info(f"参考文献数量满足要求，当前数量为{cnt}条。")
        

        expected_font_size = config.get("font_size")
        expected_cn = config.get("font_chinese")
        expected_en = config.get("font_western")
        expected_alignment = config.get("alignment")
        bucket = errors.setdefault("参考文献检测", [])
        for i, p in enumerate(reference):
            if i < 1:
                continue  # 跳过第一条，避免误判
            if len(p.text.strip()) < 1: continue # 跳过无效参考文献

            actual_font_size = get_effective_font_pt_size(p)
            actual_cn, actual_en = get_effective_fonts(p)
            actual_alignment = get_effective_alignment(p, document)

            if expected_font_size and actual_font_size and actual_font_size != expected_font_size:
                msg = f"参考文献第{i+1}条的字体大小错误，应该为{Formatter.fmt_font_pt_size(expected_font_size)}，但实际为{Formatter.fmt_font_pt_size(actual_font_size)}"
                logger.error(msg)
                bucket.append(msg)

            if expected_cn and actual_cn and actual_cn != expected_cn:
                msg = f"参考文献第{i+1}条的中文字体错误，应该为{expected_cn}，但实际为{actual_cn}"
                logger.error(msg)
                bucket.append(msg)

            if expected_en and actual_en and actual_en != expected_en:
                msg = f"参考文献第{i+1}条的西文字体错误，应该为{expected_en}，但实际为{actual_en}"
                logger.error(msg)
                bucket.append(msg)

            if expected_alignment and actual_alignment != expected_alignment:
                msg = f"参考文献第{i+1}条的对齐方式错误，应该为{Formatter.fmt_align(expected_alignment)}，但实际为{Formatter.fmt_align(actual_alignment)}"
                logger.error(msg)
                bucket.append(msg)


        # 检查英文参考文献数量
        if en_cnt < config["en_min_count"]:
            msg = f"英文参考文献数量少于{config['en_min_count']}条，当前数量为{en_cnt}条，请检查！"
            logger.error(msg)
            bucket.append(msg)
        else:
            logger.info(f"英文参考文献数量满足要求，当前数量为{en_cnt}条。")
