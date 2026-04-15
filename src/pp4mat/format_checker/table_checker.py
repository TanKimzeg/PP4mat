from pp4mat.logger import setup_logger
from pp4mat.format_checker.utils import (
    get_effective_alignment,
    get_effective_fonts,
    get_effective_font_pt_size,
    Formatter
)
from pp4mat.config_converter.config_handle import FormatConfig
from docx.document import Document as DocumentObject


logger = setup_logger(__package__)

def table_checker(document: DocumentObject, 
                  format_config: FormatConfig, errors: dict[str, list[str]]) -> None:
    logger.info("检查表格格式...")
    config = format_config.table_config
    tables = document.tables
    paragraphs = document.paragraphs
    
    for i, table in enumerate(tables):
        table_index = None
        for j, p in enumerate(paragraphs):
            if p._element.getnext() == table._element:
                table_index = j
                break

        if table_index is not None and table_index > 0:
            header_p = paragraphs[table_index]
            if not header_p.text.strip().startswith(f"表{i+1} "):
                logger.error(f"表格{i+1}的标题格式错误，应该以\"表{i+1} \"开头，但实际为：\"{header_p.text.strip()}\"")
                errors["表格检测"].append(f"表格{i+1}的标题格式错误，应该以\"表{i+1} \"开头，但实际为：\"{header_p.text.strip()}\"")
            if config is not None:
                expected_alignment = config["alignment"]
                actual_alignment = get_effective_alignment(header_p, document=document)
                if expected_alignment and actual_alignment != expected_alignment:
                    msg = f"表格{i+1}的标题对齐方式错误，应该为{Formatter.fmt_align(expected_alignment)}，但实际为{Formatter.fmt_align(actual_alignment)}"
                    logger.error(msg)
                    errors["表格检测"].append(msg)

                expected_font_size = config.get("font_size")
                expected_cn = config.get("font_chinese") or config.get("font_name")
                expected_en = config.get("font_western")

                actual_font_size = get_effective_font_pt_size(header_p)
                actual_cn, actual_en = get_effective_fonts(header_p)

                if expected_font_size and actual_font_size and actual_font_size != expected_font_size:
                    msg = f"表格{i+1}的标题字体大小错误，应该为{Formatter.fmt_font_pt_size(expected_font_size)}，但实际为{Formatter.fmt_font_pt_size(actual_font_size)}"
                    logger.error(msg)
                    errors["表格检测"].append(msg)

                if expected_cn and actual_cn and actual_cn != expected_cn:
                    msg = f"表格{i+1}的标题中文字体错误，应该为{expected_cn}，但实际为{actual_cn}"
                    logger.error(msg)
                    errors["表格检测"].append(msg)
                if expected_en and actual_en and actual_en != expected_en:
                    msg = f"表格{i+1}的标题西文字体错误，应该为{expected_en}，但实际为{actual_en}"
                    logger.error(msg)
                    errors["表格检测"].append(msg)
            else:
                logger.info(f"表格{i+1}的标题格式正确：{header_p.text.strip()}")
        else:
            logger.error(f"表格{i+1}未找到对应的标题段落，请检查文档格式。")
            errors["表格检测"].append(f"表格{i+1}未找到对应的标题段落")
