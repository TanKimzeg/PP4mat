from deprecated import deprecated
from pp4mat.logger import setup_logger
from docx.text.paragraph import Paragraph
from docx.document import Document as DocumentObject

logger = setup_logger(__package__)

def get_indentation(p: Paragraph) -> float:
    left_indent = p.paragraph_format.left_indent
    if left_indent is None:
        # 从style中获取默认缩进
        if p.style:
            left_indent = p.style.paragraph_format.left_indent
            if left_indent is None:
                # 如果style中也没有定义缩进，则返回0
                return 0.0
    # return left_indent.pt if hasattr(left_indent, 'pt') else left_indent / 20.0
    return left_indent if left_indent is not None else 0.0

def get_bold(p: Paragraph) -> bool:
    raise NotImplementedError

def correct_size(ps: list[Paragraph], size: int) -> bool:
    # convert = {"小六": 13  ,   "六号": 15  , "小五":  18  ,  "五号": 21  ,
    #             "小四": 24  ,   "四号": 28  , "小三" :30 ,   "三号":32  ,
    #             "小二": 36 , "二号":44 ,"小一": 48 , "一号": 52}
    # expected_size = convert[size]
    expected_size = float(size)
    # Check the font size of the first run in the paragraph
    for p in ps:
        for run in p.runs:
            if len(run.text.strip()) == 0: continue
            s = run.font.size.pt if run.font.size else None
            if s is None:
                s = run.style.font.size
                if s is None:
                    if p.style: s = p.style.font.size
            assert s is not None, "Font size should not be None"
            if float(s) != expected_size:
                return False
    return True

def total_words(doc: DocumentObject) -> int:
    return sum(len(p.text.strip()) for p in doc.paragraphs)

def get_sections(doc: DocumentObject) -> dict[str, list[Paragraph]]:
    from collections import defaultdict
    undergraduate_location:dict[str, list[Paragraph]] = defaultdict(list)
    undergraduate_sections = [
        "毕业论文（设计）",
        "摘 要：", 
        "关键词：", 
        "Abstract:", 
        "Keywords:", 
        "目 录", 
        # "文献综述",
        "参考文献：", 
        "附  录："
    ]
    paragraphs = doc.paragraphs
    for p in paragraphs:
        if '\u3000' in p.text:
            p.text = p.text.replace('\u3000', ' ')
    p = 0
    for i,section in enumerate(undergraduate_sections):
        begin, end = False, False
        while p < len(paragraphs) and not end:
            for j in range(i+1, len(undergraduate_sections)):
                if paragraphs[p].text.strip().startswith(undergraduate_sections[j]) if i+1 < len(undergraduate_sections) else "":
                    end = True
                    break
            if end: break
            if section in paragraphs[p].text.strip()[:10]:
                begin = True
            if begin:
                undergraduate_location[section.strip('：').strip(':')].append(paragraphs[p])
            p += 1
        if begin == False or end == False:
            p = 0

    #  分割 目录 和 正文
    if "目 录" in undergraduate_location:
        toc = undergraduate_location["目 录"]
        text_start = False
        for idx, p in enumerate(toc):
            if p.text.strip().startswith("1.引 言"):
                if not text_start:
                    text_start = True
                    continue
                else:
                    undergraduate_location["正文"] = toc[idx:]
                    undergraduate_location["目 录"] = toc[:idx]
                    break
    return undergraduate_location

@deprecated(version='0.1.0', reason="Use cover_info_from_textbox instead")
def cover_info(cover_section: list[Paragraph]) :
    infomation = [
        "题目：",
        "姓名：",
        "学号：",
        "学院：",
        "年级：",
        "专业：",
        "区队：",
        "指导教师：",
    ]
    extract_info = dict()
    for p in cover_section:
        for keyword in infomation:
            if keyword in p.text:
                val = p.text.split(keyword)[-1].strip()
                extract_info[keyword] = val
                logger.info(f"提取到信息：{keyword} {val}")
    return extract_info

def cover_info_from_textbox(win32doc) -> dict[str, str]:
    """
    
    提取封面信息，包括题目、姓名、学号等。

    :return: dict[str, str] 

    封面信息字典，键为信息类型(题目/姓名/学号等)，值为对应内容。
    """
    infomation = [
        "题目：",
        "学号：",
        "姓名：",
        "学院：",
        "年级：",
        "专业：",
        "区队：",
        "指导教师：",
    ]
    info = dict()
    textbox_content = extract_textbox_content(win32doc)
    for i in range(min(len(textbox_content), len(infomation))):
        content = textbox_content[i]
        info[infomation[i][:-1]] = content.strip()
        logger.debug(f"提取到信息：{infomation[i]} {content.strip()}")
    return info

def extract_textbox_content(doc) -> list[str]:
    import re
    """
    提取 Word 文档中的文本框内容。

    Args:
        doc_path (str): Word 文档路径。

    Returns:
        list[str]: 文档中所有文本框的内容。
    """
    def clean_text(text: str) -> str:
        return re.sub(r"[\x00-\x1F\x7F-\x9F]", "", text).strip()
    # word = win32com.client.Dispatch("Word.Application")
    # doc = word.Documents.Open(doc_path)
    textbox_contents = []

    # 遍历所有形状对象
    for shape in doc.Shapes:
        if shape.TextFrame.HasText:
            if shape.TextFrame.TextRange.Text.strip() != "":
                raw_text = shape.TextFrame.TextRange.Text.strip()
                cleaned_text = clean_text(raw_text)
                if cleaned_text:
                    anchor_pos = shape.Anchor.Start
                    textbox_contents.append((anchor_pos, cleaned_text))
    textbox_contents.sort(key=lambda x: x[0])  # 按锚点位置排序
    textbox_contents = [content for _, content in textbox_contents]  # 提取内容
    return textbox_contents

def count_citations(locations: dict[str, list[Paragraph]]) -> int:
    cnt = 0
    import re
    citation_pattern = r'\[[1-9]\d*\]'
    for s,pl in locations.items():
        if s != "参考文献":
            for p in pl:
                sub_string = re.findall(citation_pattern, p.text)
                cnt += len(sub_string)
                if len(sub_string) > 0:
                    logger.debug(f"段落：{p.text.strip()[:5]}...{'...'.join(sub_string)}... 包含 {len(sub_string)} 个引用")
    return cnt
