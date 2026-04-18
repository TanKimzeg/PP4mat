from typing import Any

from pp4mat.logger import setup_logger
from pp4mat.format_checker.protocols import FormatChecker, FormatErrors

logger = setup_logger(__package__)

class CoverInfoChecker(FormatChecker):
    def __init__(self, cover_info: dict[str, str], errors: FormatErrors) -> None:
        self.errors = errors
        self.cover_info = cover_info

    def check_format(self) -> None:
        # 封面信息（文本框）
        self.check_cover_info(self.cover_info, self.errors)
        return None



    @staticmethod
    def check_cover_info(info: dict[str, str], errors: FormatErrors) -> None:
        infomation = [
            "题目",
            "学号",
            "姓名",
            "学院",
            "年级",
            "专业",
            "区队",
            "指导教师",
        ]
        for info_key in infomation:
            if info_key not in info:
                logger.error(f"封面信息缺失：{info_key}，请检查！")
                errors["封面信息检测"].append(f"封面信息缺失：{info_key}")

