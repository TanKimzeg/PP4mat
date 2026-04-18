from typing import Any
from docx.text.paragraph import Paragraph

from pp4mat.logger import setup_logger
from pp4mat.config_converter import FormatConfig
from pp4mat.format_checker.protocols import FormatChecker, FormatErrors

logger = setup_logger(__package__)

class CitationChecker(FormatChecker):
    def __init__(self, sections: dict[str, list[Paragraph]], config: FormatConfig, errors: FormatErrors) -> None:
        self.errors = errors
        self.config = config
        self.sections = sections

    def check_format(self) -> None:
        self.citation_count_checker(self.sections, self.config, self.errors)
        return None
    
    @staticmethod
    def citation_count_checker(sections: dict[str, list[Paragraph]], 
                            format_config: FormatConfig, errors: dict[str, list[str]]) -> None:
        logger.info("检查脚注数量")
        config = format_config.citation_min_count
        if config is None:
            logger.warning("脚注数量配置未提供，跳过检查。")
            return
        cnt = 0
        import re
        citation_pattern = r'\[[1-9]\d*\]'
        for s,pl in sections.items():
            if s != "参考文献":
                for p in pl:
                    sub_string = re.findall(citation_pattern, p.text)
                    cnt += len(sub_string)
                    if len(sub_string) > 0:
                        logger.debug(f"段落：{p.text.strip()[:5]}...{'...'.join(sub_string)}... 包含 {len(sub_string)} 个引用")
        if cnt < config:
            logger.error(f"脚注数量少于{config}条，当前数量为{cnt}条，请检查！")
            errors["脚注检测"].append(f"脚注数量少于{config}条，当前数量为{cnt}条")

