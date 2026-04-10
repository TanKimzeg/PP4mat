from typing import Any
from functools import singledispatch
import os
from docx import Document
from pp4mat.logger import setup_logger
from pp4mat.format_checker import utils
from collections import defaultdict
from pp4mat.config_converter.config_handle import Config, FormatConfig
from docx.document import Document as DocumentObject
from docx.text.paragraph import Paragraph
import win32com.client

logger = setup_logger(__package__)

def title_checker(document: DocumentObject, format_config: FormatConfig) -> None:
    logger.info("检查标题格式...")
    config = format_config.title_config
    if config is None:
        logger.warning("标题格式配置未提供，跳过检查。")
        return 
    raise NotImplementedError("标题格式检查功能尚未实现")

def heading_checker(document: DocumentObject, format_config: FormatConfig) -> None:
    logger.info("检查小节标题格式...")
    raise NotImplementedError

def text_checker(text: list[Paragraph], format_config: FormatConfig, errors: dict[str, list[str]] | None = None) -> None:
    logger.info("检查正文格式...")
    config = format_config.text_config
    if config is None:
        logger.warning(f"正文格式配置未提供，跳过检查。")
        return

    # 当前仅实现：正文（非标题）行距 1.5 倍检查
    for i, p in enumerate(text):
        if not utils.check_line_spacing(p, expected=config["line_spacing"], allow_inherited_true=True):
            msg = f"正文第{i+1}段行距可能不正确：\"{p.text.strip()[:30]}……\""
            logger.error(msg)
            if errors is not None:
                errors["正文检测"].append(msg)


def formula_checker(document: DocumentObject, format_config: FormatConfig) -> None:
    logger.info("检查公式格式...")
    config = format_config.formula_config
    if config is None:
        logger.warning(f"公式格式配置未提供，跳过检查。")
        return
    raise NotImplementedError("公式格式检查功能尚未实现")

@singledispatch # TODO: unable to find the expected picture by Shape.Type
def figure_checker(win32doc: Any, format_config: FormatConfig, errors: dict[str, list[str]]) -> None:
    logger.info("检查图片格式...")
    config = format_config.figure_config
    if config is None:
        logger.warning(f"图片格式配置未提供，跳过检查。")
        return
    picture_cnt = 0
    for shape in win32doc.Shapes:
        # if shape.Type == win32com.client.constants.msoPicture:
        if shape.Type == 17:  # msoPicture
            picture_cnt += 1
            if shape.Anchor.Paragraphs.Count > 0:
                anchor_p = shape.Anchor.Paragraphs(1)
                next_p = anchor_p.Next()
                while next_p.Range.Text.strip() == "":
                    next_p = next_p.Next()
                if next_p is None:
                    logger.error(f"图片{picture_cnt}未找到对应的标题段落，请检查文档格式。")
                    errors["图片检测"].append(f"图片{picture_cnt}未找到对应的标题段落")
                    continue
                if not next_p.Range.Text.strip().startswith(f"图{picture_cnt} "):
                    logger.error(f"图片{picture_cnt}的标题格式错误，应该以\"图{picture_cnt} \"开头，但实际为：{next_p.Range.Text.strip()}。请注意空格、编号。")
                    errors["图片检测"].append(f"图片{picture_cnt}的标题格式错误，应该以\"图{picture_cnt} \"开头，但实际为：{next_p.Range.Text.strip()}。请注意空格、编号。")
                else:
                    logger.info(f"图片{picture_cnt}的标题格式正确：{next_p.Range.Text.strip()}")
            else:
                logger.error(f"图片{picture_cnt}未找到对应的标题段落，请检查文档格式。")
                errors["图片检测"].append(f"图片{picture_cnt}未找到对应的标题段落")

@figure_checker.register(DocumentObject)
def _(document: DocumentObject, format_config: FormatConfig, errors: dict[str, list[str]]) -> None:
    config = format_config.figure_config

    def is_img(run: Any) -> bool:
        drawing_elements = run._element.xpath('.//w:drawing')
        for drawing in drawing_elements:
            if drawing.xpath('.//a:graphic'):
                return True
        return False

    paragraphs = document.paragraphs
    picture_cnt = 0
    for i, p in enumerate(paragraphs):
        if p.runs and any(is_img(run) for run in p.runs):
            if i + 1 < len(paragraphs):
                next_p = paragraphs[i + 1]
                if next_p.text.strip().startswith(f"图"):
                    picture_cnt += 1
                    if not next_p.text.strip().startswith(f"图{picture_cnt} "):
                        logger.error(f"图片{picture_cnt}的标题格式错误，应该以\"图{picture_cnt} \"开头，但实际为：\"{next_p.text.strip()}\"。请注意空格、编号。")
                        errors["图片检测"].append(f"图片{picture_cnt}的标题格式错误，应该以\"图{picture_cnt} \"开头，但实际为：\"{next_p.text.strip()}\"。请注意空格、编号。")
                    if config is not None:
                        expected_alignment = config["alignment"]
                        actual_alignment = utils.get_effective_alignment(next_p)
                        if expected_alignment and actual_alignment != expected_alignment:
                            logger.error(f"图片{picture_cnt}的标题对齐方式错误，应该为{expected_alignment}，但实际为{actual_alignment}")
                            errors["图片检测"].append(f"图片{picture_cnt}的标题对齐方式错误，应该为{expected_alignment}，但实际为{actual_alignment}")
                        expected_font_size = config["font_size"]
                        expected_font_name = config["font_name"]
                        actual_font_size = utils.get_effective_font_pt_size(next_p)
                        actual_font_name = utils.get_effective_font_name(next_p)
                        if expected_font_size and actual_font_size and actual_font_size != expected_font_size:
                            logger.error(f"图片{picture_cnt}的标题字体大小错误，应该为{expected_font_size}pt，但实际为{actual_font_size}pt")
                            errors["图片检测"].append(f"图片{picture_cnt}的标题字体大小错误，应该为{expected_font_size}pt，但实际为{actual_font_size}pt")
                        if expected_font_name and actual_font_name and actual_font_name != expected_font_name:
                            logger.error(f"图片{picture_cnt}的标题字体错误，应该为{expected_font_name}，但实际为{actual_font_name}")
                            errors["图片检测"].append(f"图片{picture_cnt}的标题字体错误，应该为{expected_font_name}，但实际为{actual_font_name}")
                else:
                    logger.warning(f"该对象不以\"图\"开头，可能不是图片：{next_p.text.strip()}")


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
                actual_alignment = utils.get_effective_alignment(header_p)
                if expected_alignment and actual_alignment != expected_alignment:
                    logger.error(f"表格{i+1}的标题对齐方式错误，应该为{expected_alignment}，但实际为{actual_alignment}")
                    errors["表格检测"].append(f"表格{i+1}的标题对齐方式错误，应该为{expected_alignment}，但实际为{actual_alignment}")
                expected_font_size = config["font_size"]
                expected_font_name = config["font_name"]
                actual_font_size = utils.get_effective_font_pt_size(header_p)
                actual_font_name = utils.get_effective_font_name(header_p)
                if expected_font_size and actual_font_size and actual_font_size != expected_font_size:
                    logger.error(f"表格{i+1}的标题字体大小错误，应该为{expected_font_size}pt，但实际为{actual_font_size}pt")
                    errors["表格检测"].append(f"表格{i+1}的标题字体大小错误，应该为{expected_font_size}pt，但实际为{actual_font_size}pt")
                if expected_font_name and actual_font_name and actual_font_name != expected_font_name:
                    logger.error(f"表格{i+1}的标题字体错误，应该为{expected_font_name}，但实际为{actual_font_name}")
                    errors["表格检测"].append(f"表格{i+1}的标题字体错误，应该为{expected_font_name}，但实际为{actual_font_name}")
            else:
                logger.info(f"表格{i+1}的标题格式正确：{header_p.text.strip()}")
        else:
            logger.error(f"表格{i+1}未找到对应的标题段落，请检查文档格式。")
            errors["表格检测"].append(f"表格{i+1}未找到对应的标题段落")
    

def reference_checker(reference: list[Paragraph], 
                      format_config: FormatConfig, errors: dict[str, list[str]]) -> None:
    import re
    logger.info("检查参考文献格式...")
    config = format_config.reference_config
    if config is None:
        logger.warning("参考文献格式配置未提供，跳过检查。")
        return
    # Placeholder for reference checking logic
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
    if config["font_size"] or config["font_name"]:
        for i, p in enumerate(reference):
            if i < 1: continue # 跳过第一条，避免误判
            expected_font_size = config["font_size"]
            expected_font_name = config["font_name"]
            actual_font_size = utils.get_effective_font_pt_size(p)
            actual_font_name = utils.get_effective_font_name(p)
            if expected_font_size and actual_font_size and actual_font_size != expected_font_size:
                logger.error(f"参考文献第{i+1}条的字体大小错误，应该为{expected_font_size}pt，但实际为{actual_font_size}pt")
                errors["参考文献检测"].append(f"参考文献第{i+1}条的字体大小错误，应该为{expected_font_size}pt，但实际为{actual_font_size}pt")
            if expected_font_name and actual_font_name and actual_font_name != expected_font_name:
                logger.error(f"参考文献第{i+1}条的字体错误，应该为{expected_font_name}，但实际为{actual_font_name}")
                errors["参考文献检测"].append(f"参考文献第{i+1}条的字体错误，应该为{expected_font_name}，但实际为{actual_font_name}")
            
    else:
        logger.info(f"参考文献数量满足要求，当前数量为{cnt}条。")
    
    # 检查英文参考文献数量
    if en_cnt < config["en_min_count"]:
        logger.error(f"英文参考文献数量少于{config['en_min_count']}条，当前数量为{en_cnt}条，请检查！")
        errors["参考文献检测"].append(f"英文参考文献数量少于{config['en_min_count']}条，当前数量为{en_cnt}条")
    else:
        logger.info(f"英文参考文献数量满足要求，当前数量为{en_cnt}条。")
    
def citation_count_checker(location: dict[str, list[Paragraph]], 
                           format_config: FormatConfig, errors: dict[str, list[str]]) -> None:
    logger.info("检查脚注数量")
    config = format_config.citation_min_count
    if config is None:
        logger.warning("脚注数量配置未提供，跳过检查。")
        return
    citation_count = utils.count_citations(location)
    if citation_count < config:
        logger.error(f"脚注数量少于{config}条，当前数量为{citation_count}条，请检查！")
        errors["脚注检测"].append(f"脚注数量少于{config}条，当前数量为{citation_count}条")

def section_checker(section_location: dict, errors: dict[str, list[str]]) -> None:
    undergraduate_sections = [
        "毕业论文（设计）",
        "摘 要", 
        "关键词", 
        "Abstract", 
        "Keywords", 
        "目 录", 
        # "文献综述",
        "参考文献", 
        "附  录"
    ]
    for section in undergraduate_sections:
        if section not in section_location or len(section_location[section]) == 0:
            logger.error(f"\"{section}\"缺失或位置不正确")
            errors["章节检测"].append(f"\"{section}\"缺失或位置不正确!请使用模板,注意空格、冒号")
        else:
            logger.info(f"\"{section}\"部分存在 {len(section_location[section])} 个段落")

def survey_checker(document: DocumentObject, format_config: FormatConfig, errors: dict[str, list[str]]) -> None:
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

def toc_checker(toc: list[Paragraph], format_config: FormatConfig, errors: dict[str, list[str]]) -> None:
    logger.info("检查目录格式...")
    if not toc:
        logger.warning("目录部分为空，跳过检查。")
        return
    import re
    h1_pattern = re.compile(r"^\d+\.")
    h2_pattern = re.compile(r"^\d+\.\d+")
    h3_pattern = re.compile(r"^\d+\.\d+\.\d+")
    chapter_count = 0
    for p in toc:
        if re.match(h1_pattern, p.text.strip()):
            if not re.match(h2_pattern, p.text.strip()):
                chapter_count += 1
            if re.match(h3_pattern, p.text.strip()):
                logger.error(f"目录项格式错误：{p.text.strip()}，不应包含三级标题")
                errors["目录检测"].append(f"目录项格式错误：{p.text.strip()}，不应包含三级标题")
    if format_config.chapter_min_count and chapter_count < format_config.chapter_min_count:
        logger.error(f"目录章节数量少于{format_config.chapter_min_count}章，当前数量为{chapter_count}章，请检查！")
        errors["目录检测"].append(f"目录章节数量少于{format_config.chapter_min_count}章，当前数量为{chapter_count}章")


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

def check_cover_info(info: dict[str, str], errors: dict[str, list[str]]) -> None:
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


def check_format(config: Config) -> tuple[dict,dict]:
    errors:dict[str,list[str]] = defaultdict(list)
    docx_path = config.docx
    format_config: FormatConfig = config.format_config
    setup_logger(__package__,level=config.debug, log_dir=config.log_dir)
    
    document = Document(docx_path)
    sections = utils.get_sections(document)
    # pywin32支持更复杂的Word文档操作,本项目中,论文的封面信息存储在文本框中,
    # 因此需要使用pywin32来提取文本框内容;检测图片和图题的关联也需要pywin32来实现.
    word = win32com.client.Dispatch("Word.Application")
    win32doc = word.Documents.Open(os.path.abspath(docx_path))

    # 封面信息（文本框）
    cover_info = utils.cover_info_from_textbox(win32doc)

    # 目录兜底：部分 docx 的自动目录可能不在 python-docx 的 paragraphs 视图里。
    # 用 COM 直接读取 TablesOfContents 的 Range.Text。
    toc_paragraphs: list[Paragraph] = sections.get("目 录") or []
    try:
        if not toc_paragraphs and win32doc.TablesOfContents.Count >= 1:
            toc_text = win32doc.TablesOfContents(1).Range.Text or ""
            toc_lines = [ln.strip() for ln in str(toc_text).splitlines() if ln.strip()]

            class _FakeParagraph:
                def __init__(self, text: str):
                    self.text = text

            # 仅 toc_checker 用到 p.text，所以用轻量对象即可
            toc_paragraphs = [
                _FakeParagraph(t)  # type: ignore[arg-type]
                for t in toc_lines
            ]
            logger.info(f"已使用 Word COM 提取目录，共 {len(toc_paragraphs)} 行")
    except Exception as e:
        logger.warning(f"Word COM 提取目录失败，仍使用 python-docx 目录段落：{e}")
    finally:
        sections["目 录"] = toc_paragraphs

    win32doc.Close()
    word.Quit()
    # cover_info.update(utils.cover_info(sections["毕业论文（设计）"]))
    check_cover_info(cover_info, errors)
    section_checker(sections, errors)
    toc_checker(sections["目 录"], format_config, errors)

    # 正文进一步筛选（排除 TOC/标题等）后再做正文格式检查
    body_normal = utils.get_body_normal_paragraphs(
        sections,
        exclusion=utils.get_table_caption_paragraphs(document)
        + utils.get_figure_caption_paragraphs(document)
        + utils.get_code_caption_paragraphs(document),
    )
    text_checker(body_normal, format_config, errors)

    survey_checker(document, format_config, errors)
    table_checker(document, format_config, errors)
    figure_checker(document, format_config, errors)
    reference_checker(sections["参考文献"], format_config, errors)

    citation_count_checker(sections, format_config, errors)
    check_enough_words(document, format_config, errors)

    return errors, cover_info
