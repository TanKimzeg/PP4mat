from docx.text.paragraph import Paragraph

from pp4mat.logger import setup_logger
from pp4mat.format_checker.protocols import FormatChecker, FormatErrors

logger = setup_logger(__package__)

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
        for section in undergraduate_sections:
            if section not in sections or len(sections[section]) == 0:
                logger.error(f"\"{section}\"缺失或位置不正确")
                errors["章节检测"].append(f"\"{section}\"缺失或位置不正确!请使用模板,注意空格、冒号")
            else:
                logger.info(f"\"{section}\"部分存在 {len(sections[section])} 个段落")
