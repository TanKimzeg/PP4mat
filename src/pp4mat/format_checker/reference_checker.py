from pp4mat.logger import setup_logger
from pp4mat.format_checker import utils
from pp4mat.config_converter.config_handle import FormatConfig
from docx.text.paragraph import Paragraph

logger = setup_logger(__package__)

def reference_checker(reference: list[Paragraph], 
                      format_config: FormatConfig, errors: dict[str, list[str]]) -> None:
    import re
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

    if config.get("font_size") or config.get("font_name") or config.get("font_chinese") or config.get("font_western"):
        for i, p in enumerate(reference):
            if i < 1:
                continue  # 跳过第一条，避免误判

            expected_font_size = config.get("font_size")
            expected_cn = config.get("font_chinese") or config.get("font_name")
            expected_en = config.get("font_western")

            actual_font_size = utils.get_effective_font_pt_size(p)
            actual_cn, actual_en = utils.get_effective_fonts(p)

            if expected_font_size and actual_font_size and actual_font_size != expected_font_size:
                logger.error(f"参考文献第{i+1}条的字体大小错误，应该为{expected_font_size}pt，但实际为{actual_font_size}pt")
                errors["参考文献检测"].append(f"参考文献第{i+1}条的字体大小错误，应该为{expected_font_size}pt，但实际为{actual_font_size}pt")

            if expected_cn and actual_cn and actual_cn != expected_cn:
                logger.error(f"参考文献第{i+1}条的中文字体错误，应该为{expected_cn}，但实际为{actual_cn}")
                errors["参考文献检测"].append(f"参考文献第{i+1}条的中文字体错误，应该为{expected_cn}，但实际为{actual_cn}")
            if expected_en and actual_en and actual_en != expected_en:
                logger.error(f"参考文献第{i+1}条的西文字体错误，应该为{expected_en}，但实际为{actual_en}")
                errors["参考文献检测"].append(f"参考文献第{i+1}条的西文字体错误，应该为{expected_en}，但实际为{actual_en}")

    else:
        logger.info(f"参考文献数量满足要求，当前数量为{cnt}条。")

    # 检查英文参考文献数量
    if en_cnt < config["en_min_count"]:
        logger.error(f"英文参考文献数量少于{config['en_min_count']}条，当前数量为{en_cnt}条，请检查！")
        errors["参考文献检测"].append(f"英文参考文献数量少于{config['en_min_count']}条，当前数量为{en_cnt}条")
    else:
        logger.info(f"英文参考文献数量满足要求，当前数量为{en_cnt}条。")
