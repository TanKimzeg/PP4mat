import os
from collections import defaultdict
from docx import Document
from docx.document import Document as DocumentObject
from docx.text.paragraph import Paragraph
import win32com.client

from pp4mat.format_checker.protocols import FormatErrors, FormatChecker
from pp4mat.config_converter import Config, FormatConfig
from pp4mat.logger import setup_logger
from pp4mat.format_checker import utils
from pp4mat.format_checker.cover_info_checker import CoverInfoChecker
from pp4mat.format_checker.section_checker import SectionChecker
from pp4mat.format_checker.toc_checker import TOCChecker
from pp4mat.format_checker.survey_checker import SurveyChecker
from pp4mat.format_checker.header_checker import HeaderChecker
from pp4mat.format_checker.figure_checker import FigureChecker
from pp4mat.format_checker.text_checker import TextChecker
from pp4mat.format_checker.table_checker import TableChecker
from pp4mat.format_checker.reference_checker import ReferenceChecker
from pp4mat.format_checker.ack_checker import AcknowledgementChecker
from pp4mat.format_checker.citation_checker import CitationChecker
from pp4mat.format_checker.words_checker import WordsChecker

logger = setup_logger(__package__)

def title_checker(document: DocumentObject, format_config: FormatConfig) -> None:
    logger.info("检查标题格式...")
    config = format_config.title_config
    if config is None:
        logger.warning("标题格式配置未提供，跳过检查。")
        return 
    raise NotImplementedError("标题格式检查功能尚未实现")

def formula_checker(document: DocumentObject, format_config: FormatConfig) -> None:
    logger.info("检查公式格式...")
    config = format_config.formula_config
    if config is None:
        logger.warning(f"公式格式配置未提供，跳过检查。")
        return
    raise NotImplementedError("公式格式检查功能尚未实现")

def page_checker(document: DocumentObject, format_config: FormatConfig) -> None:
    global errors
    logger.info("检查页面格式...")
    # Placeholder for page checking logic
    config = format_config.page_config
    if config is None:
        logger.warning(f"页面格式配置未提供，跳过检查。")
        return
    raise NotImplementedError("页面格式检查功能尚未实现")

def abstract_checker(abstact: list[Paragraph], format_config: FormatConfig) -> None:
    global errors
    logger.info("检查摘要格式...")
    config = format_config.abstract_config
    if config is None:
        logger.warning(f"摘要格式配置未提供，跳过检查。")
        return
    raise NotImplementedError("摘要格式检查功能尚未实现")

def check_format(config: Config) -> tuple[dict,dict]:
    errors: FormatErrors = defaultdict(list)
    docx_path = config.docx
    format_config: FormatConfig = config.format_config
    setup_logger(__package__,level=config.debug, log_dir=config.log_dir)

    document = Document(docx_path)
    utils.attach_paragraph_indices(document)
    sections = utils.get_sections(document)

    word = win32com.client.Dispatch("Word.Application")
    win32doc = word.Documents.Open(os.path.abspath(docx_path))

    try:
        cover_info = utils.cover_info_from_textbox(win32doc)
        cover_info_checker = CoverInfoChecker(cover_info, errors)
        toc_checker = TOCChecker(sections, win32doc, format_config, errors)
        section_checker = SectionChecker(sections, errors)
        header_checker = HeaderChecker(document, format_config, errors)
        text_checker = TextChecker(
            utils.get_body_normal_paragraphs(
                sections,
                exclusion=utils.get_table_caption_paragraphs(document)
                + utils.get_figure_caption_paragraphs(document)
                + utils.get_code_caption_paragraphs(document)
            ), document, format_config, errors
        )
        survey_checker = SurveyChecker(document, errors)
        table_checker = TableChecker(document, format_config, errors)
        figure_checker = FigureChecker(document, format_config, errors)
        acknowledgement_checker = AcknowledgementChecker(sections["致谢"], document, format_config, errors)
        reference_checker = ReferenceChecker(sections["参考文献"], document, format_config, errors)
        citation_count_checker = CitationChecker(sections, format_config, errors)
        words_checker = WordsChecker(document, format_config, errors)

        checkers: list[FormatChecker] = [
            cover_info_checker,
            toc_checker,
            section_checker,
            header_checker,
            text_checker,
            survey_checker,
            table_checker,
            figure_checker,
            acknowledgement_checker,
            reference_checker,
            citation_count_checker,
            words_checker
        ]
        for checker in checkers:
            checker.check_format()

        return errors, cover_info
    finally:
        try:
            win32doc.Close()
        finally:
            word.Quit()
