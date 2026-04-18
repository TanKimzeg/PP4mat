from docx.document import Document as DocumentObject
from pp4mat.config_converter import FormatConfig
from pp4mat.format_checker.protocols import FormatChecker, FormatErrors
from pp4mat.logger import setup_logger
from pp4mat.format_checker import utils

logger = setup_logger(__package__)

class WordsChecker(FormatChecker):
    def __init__(self, doc: DocumentObject, config: FormatConfig, errors: FormatErrors) -> None:
        self.config = config
        self.doc = doc
        self.errors = errors


    def check_format(self) -> None:
        self.check_enough_words(self.doc, self.config, self.errors)
        return None

    @staticmethod
    def check_enough_words(document: DocumentObject, format_config: FormatConfig, errors: dict[str, list[str]]) -> None:
        logger.info("检查文档字数...")
        config = format_config.words_min_count
        if config is None:
            logger.warning("字数配置未提供，跳过检查。")
            return
        word_count = utils.total_words(document)
        if word_count < config:
            logger.error(f"文档字数少于{config}字，当前字数为{word_count}字，请检查！")
            errors["字数检测"].append(f"文档字数少于{config}字，当前字数为{word_count}字")
        else:
            logger.info(f"文档字数满足要求，当前字数为{word_count}字。")
