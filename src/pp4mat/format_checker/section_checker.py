from docx.text.paragraph import Paragraph

from pp4mat.logger import setup_logger
from pp4mat.format_checker.protocols import FormatChecker, FormatErrors

logger = setup_logger(__package__, console=True, file=False)

class SectionChecker(FormatChecker):
    def __init__(self, sections: dict[str, list[Paragraph]], errors: FormatErrors) -> None:
        self.sections = sections
        self.errors = errors

    def check_format(self) -> None:
        self.section_checker(self.sections, self.errors)
        return None

    @staticmethod
    def section_checker(sections: dict[str, list[Paragraph]], errors: dict[str, list[str]]) -> None:
        undergraduate_sections = [
            "毕业论文（设计）",
            "摘要", 
            "关键词", 
            "Abstract", 
            "Keywords", 
            "目录", 
            "致谢",
            "参考文献", 
            "附录"
        ]
        backet = errors.setdefault("章节检测", [])
        for section in undergraduate_sections:
            if section not in sections or len(sections[section]) == 0:
                logger.error(f"\"{section}\"缺失或位置不正确")
                if section in ["目录", "致谢"]:  # 目录和致谢可以视为可选项，缺失时仅警告
                    backet.append(f"\"{section}\"部分缺失或位置不正确！请查看模板格式，注意冒号。")
                else:
                    backet.append(f"\"{section}\"缺失或位置不正确！请查看模板格式。")
            else:
                logger.info(f"\"{section}\"部分存在 {len(sections[section])} 个段落")
