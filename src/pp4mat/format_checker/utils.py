from deprecated import deprecated
from pp4mat.logger import setup_logger
from docx.text.paragraph import Paragraph
from docx.text.run import Run
from docx.document import Document as DocumentObject
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
import re

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

def get_effective_alignment(p: Paragraph) -> WD_PARAGRAPH_ALIGNMENT | None:
    if p.alignment is not None:
        return p.alignment
    if p.paragraph_format.alignment is not None:
        return p.paragraph_format.alignment
    if p.style and p.style.paragraph_format.alignment is not None:
        return p.style.paragraph_format.alignment
    return None

def get_effective_font_pt_size(p: Paragraph) -> float | None:
    for run in p.runs:
        if len(run.text.strip()) < 5: continue # 跳过空白或过短的run，避免误判
        s = run.font.size.pt if run.font.size else None
        if s is not None:
            return s
        s = run.style.font.size.pt if run.style and run.style.font.size else None
        if s is not None:
            return s
    if p.style and p.style.font.size:
        return p.style.font.size.pt
    return None

def get_effective_font_name(p: Paragraph) -> str | None:
    for run in p.runs:
        if len(run.text.strip()) < 5: continue # 跳过空白或过短的run，避免误判
        font_name = run.font.name if run.font.name else None
        if font_name is not None:
            return font_name
        font_name = run.style.font.name if run.style and run.style.font.name else None
        if font_name is not None:
            return font_name
    if p.style and p.style.font.name:
        return p.style.font.name
    return None
    
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

    def _norm(s: str) -> str:
        return re.sub(r"\s+", "", (s or "").strip())

    def _style_name(par: Paragraph) -> str:
        style = getattr(par, "style", None)
        return (getattr(style, "name", "") or "").strip()

    def _is_toc_paragraph(par: Paragraph) -> bool:
        name = _style_name(par)
        up = name.upper()
        # 英文/中文常见 TOC 样式
        return up.startswith("TOC") or name.startswith("目录")

    def _is_heading1_style(par: Paragraph) -> bool:
        name = _style_name(par).lower()
        # 常见：Heading 1 / 标题 1 / 一级标题
        return ("heading 1" in name) or ("标题 1" in name) or ("一级标题" in name)

    def _has_numbering(par: Paragraph) -> bool:
        """检测段落是否带自动编号（w:numPr）。

        目录条目也可能带编号，但通常其样式会是 TOC，此处会被 _is_toc_paragraph 过滤。
        """
        try:
            el = getattr(par, "_p", None)
            if el is None:
                return False
            # 仅检测是否存在 numPr（不解析具体级别）
            return bool(el.xpath('.//w:pPr/w:numPr'))
        except Exception:
            return False
    undergraduate_location:dict[str, list[Paragraph]] = defaultdict(list)
    undergraduate_sections = [
        "毕业论文（设计）",
        "摘 要：", 
        "关键词：", 
        "Abstract:", 
        "Keywords:", 
        "目 录", 
        # "文献综述",
        "参考文献", 
        "附  录"
    ]
    paragraphs = doc.paragraphs
    for p in paragraphs:
        if '\u3000' in p.text:
            p.text = p.text.replace('\u3000', ' ')

    # 基于标题切片（适用于手写目录/固定模板）
    p_idx = 0
    for i, section in enumerate(undergraduate_sections):
        begin, end = False, False
        while p_idx < len(paragraphs) and not end:
            for j in range(i + 1, len(undergraduate_sections)):
                if (paragraphs[p_idx].text.strip().startswith(undergraduate_sections[j]) if i + 1 < len(undergraduate_sections) else "") and not (
                    _style_name(paragraphs[p_idx]).upper().startswith("TOC")):
                    end = True
                    break
            if end:
                break
            if paragraphs[p_idx].text.strip().startswith(section):
                begin = True
            if begin:
                undergraduate_location[section.strip('：').strip(':')].append(paragraphs[p_idx])
            p_idx += 1
        if begin is False or end is False:
            p_idx = 0

    # --- 更健壮的“目录/正文”分割 ---
    # 对自动目录场景：目录条目通常是 TOC 样式或字段结果，应跳过这些段落来寻找正文起点。
    # 文本匹配一级章节：1. / 1.引言 / 1 引言（允许空格）
    h1_text = re.compile(r"^\s*\d+\s*(?:[\.．]|\s)\s*\S")

    body_start_idx: int | None = None
    for i, par in enumerate(paragraphs):
        t = par.text.strip()
        if not t and not _is_heading1_style(par):
            continue
        # 自动目录条目跳过
        if _is_toc_paragraph(par):
            continue

        if h1_text.match(t) or _is_heading1_style(par) or (_has_numbering(par) and _is_heading1_style(par)):
            body_start_idx = i
            break

    if body_start_idx is not None:
        # 目录只保留正文开始点之前的段落（避免目录切片把正文也吃进去）
        if "目 录" in undergraduate_location and undergraduate_location["目 录"]:
            toc_list = undergraduate_location["目 录"]
            # 建立 paragraph 对象 -> index 的映射，避免反复 paragraphs.index() 造成 O(n^2)
            idx_map = {id(par): idx for idx, par in enumerate(paragraphs)}
            undergraduate_location["目 录"] = [par for par in toc_list if idx_map.get(id(par), -1) < body_start_idx]

        # 正文：从 body_start_idx 到参考文献/附录之前（若能定位到）
        end_idx = len(paragraphs)
        for i in range(body_start_idx, len(paragraphs)):
            t = paragraphs[i].text.strip()
            if _is_toc_paragraph(paragraphs[i]):
                continue
            if _norm(t).startswith(_norm("参考文献")) or _norm(t).startswith(_norm("附录")) or _norm(t).startswith(_norm("附  录")):
                end_idx = i
                break

        undergraduate_location["正文"] = [par for par in paragraphs[body_start_idx:end_idx] if not _is_toc_paragraph(par)]

    return undergraduate_location

@deprecated(version='0.1.0', reason="Use cover_info_from_textbox instead")
def cover_info(cover_section: list[Paragraph]) -> dict[str, str]:
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
                val = p.text.split(keyword)[-1].strip().replace('_', '')
                extract_info[keyword[:-1]] = val
                logger.warning(f"提取到封面信息：{keyword} {val},没有使用文本框!")
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

def get_effective_line_spacing(p: Paragraph) -> float | None:
    """返回“多倍行距”的倍数（如 1.0/1.5/2.0），无法判定则返回 None。

    说明：python-docx 中 line_spacing 可能来自段落直设、样式、或样式继承。
    仅在可解释为“倍数行距”时返回 float。
    """
    # 1) 直设
    if p.paragraph_format and p.paragraph_format.line_spacing is not None:
        ls = p.paragraph_format.line_spacing
        if isinstance(ls, (int, float)):
            return float(ls)

    # 2) 样式链
    style = getattr(p, "style", None)
    visited = set()
    while style is not None and id(style) not in visited:
        visited.add(id(style))
        try:
            pf = style.paragraph_format
            if pf and pf.line_spacing is not None:
                ls = pf.line_spacing
                if isinstance(ls, (int, float)):
                    return float(ls)
        except Exception:
            pass
        style = getattr(style, "base_style", None)

    return None

def check_line_spacing(p: Paragraph, expected: float, tol: float = 0.05, allow_inherited_true: bool = True) -> bool:
    """检查段落行距是否符合预期。

    - expected: 期望的倍数行距（如 1.0/1.5/2.0）
    - tol: 容差范围，默认 0.05（即允许误差 ±0.05）
    - allow_inherited_true: 当无法判定行距时（None），是否按“可能继承为 expected”放行
    """
    ls = get_effective_line_spacing(p)
    if ls is None:
        return True if allow_inherited_true else False
    return abs(ls - expected) <= tol

def get_table_caption_paragraphs(document: DocumentObject) -> list[Paragraph]:
    """从文档中提取所有表格标题段落。

    表格标题段落的规则：
    - 段落文本以“表”开头
    """
    captions = []
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
            if header_p.text.strip().startswith(f"表"):
                captions.append(header_p)
    return captions

def get_figure_caption_paragraphs(document: DocumentObject) -> list[Paragraph]:
    captions = []
    def is_img(run: Run) -> bool:
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
                    if next_p.text.strip().startswith(f"图"):
                        captions.append(next_p)
    return captions


def get_body_normal_paragraphs(sections: dict[str, list[Paragraph]], exclusion: list[Paragraph] | None = None) -> list[Paragraph]:
    """从 sections['正文'] 中提取可用于正文格式检查的段落。


    注意：exclusion 里的 Paragraph 对象可能来自“另一份 Document 解析”或重新构造，
    这时用 id()/对象相等都不可靠，因此这里用 文本 做稳定匹配。
    """
    body = sections.get("正文") or []
    exclusion_texts = {p.text.strip() for p in (exclusion or [])}

    def _style_name(par: Paragraph) -> str:
        style = getattr(par, "style", None)
        return (getattr(style, "name", "") or "").strip()

    def _is_heading(par: Paragraph) -> bool:
        name = _style_name(par)
        low = name.lower()
        if "heading" in low:
            return True
        if "标题" in name:
            return True
        if "一级标题" in name or "二级标题" in name or "三级标题" in name:
            return True
        return False

    def _is_toc(par: Paragraph) -> bool:
        name = _style_name(par)
        up = name.upper()
        if up.startswith("TOC"):
            return True
        if name.startswith("目录"):
            return True
        return False

    out: list[Paragraph] = []
    for p in body:
        if not (p.text or "").strip():
            continue
        if _is_toc(p):
            continue
        if _is_heading(p):
            continue
        if p.text.strip() in exclusion_texts:
            continue
        out.append(p)

    return out
