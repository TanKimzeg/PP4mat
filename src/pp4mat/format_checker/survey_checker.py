from docx.document import Document as DocumentObject

from pp4mat.logger import setup_logger
from pp4mat.format_checker.protocols import FormatChecker, FormatErrors

logger = setup_logger(__package__)

class SurveyChecker(FormatChecker):
    def __init__(self, doc: DocumentObject, errors: FormatErrors) -> None:
        self.errors = errors
        self.doc = doc

    def check_format(self) -> None:
        self.survey_checker(self.doc, self.errors)
        return None

    @staticmethod
    def survey_checker(document: DocumentObject, errors: dict[str, list[str]]) -> None:
        keywords = [
            "综述",
            "国内外",
            "现状"
        ]
        logger.info("检查文献综述部分...")
        found = False
        for p in document.paragraphs:
            if any(keyword in p.text for keyword in keywords):
                logger.info(f"找到文献综述相关内容：{p.text.strip()}")
                found = True
                return

        if not found:
            logger.error("文献综述部分缺失或不完整，请检查！")
            errors["文献综述检测"].append("文献综述部分缺失或不完整")
