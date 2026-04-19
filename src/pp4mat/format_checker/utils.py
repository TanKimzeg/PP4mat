from deprecated import deprecated
from pp4mat.logger import setup_logger
from docx.text.paragraph import Paragraph
from docx.text.run import Run
from docx.document import Document as DocumentObject
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from typing import Any, Literal
import re

from pp4mat.config_converter.config_handle import FormatConfig

# 工具模块在 import 时不应创建文件日志（避免被其它模块导入时反复创建/抢占）。
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

def _alignment_from_w_val(val: str | None) -> WD_PARAGRAPH_ALIGNMENT | None:
    """将 Word XML 中 w:jc/@w:val 映射为 python-docx 的 WD_PARAGRAPH_ALIGNMENT。

    兼容：left/center/right/both/justify/distribute 以及常见变体。
    """
    if not val:
        return None
    v = str(val).strip().lower()
    mapping = {
        "left": WD_PARAGRAPH_ALIGNMENT.LEFT,
        "start": WD_PARAGRAPH_ALIGNMENT.LEFT,
        "center": WD_PARAGRAPH_ALIGNMENT.CENTER,
        "right": WD_PARAGRAPH_ALIGNMENT.RIGHT,
        "end": WD_PARAGRAPH_ALIGNMENT.RIGHT,
        "both": WD_PARAGRAPH_ALIGNMENT.JUSTIFY,
        "justify": WD_PARAGRAPH_ALIGNMENT.JUSTIFY,
        "distribute": WD_PARAGRAPH_ALIGNMENT.DISTRIBUTE,
    }
    return mapping.get(v)


def _get_alignment_from_paragraph_xml(p: Paragraph) -> WD_PARAGRAPH_ALIGNMENT | None:
    """从段落 XML 的 w:pPr/w:jc 直接提取对齐。

    说明：不少文档的对齐只写在 XML 里，python-docx 的 p.alignment 可能为 None。
    """
    try:
        from docx.oxml.ns import qn

        pPr = p._element.find(qn("w:pPr"))
        if pPr is None:
            return None
        jc = pPr.find(qn("w:jc"))
        if jc is None:
            return None
        return _alignment_from_w_val(jc.get(qn("w:val")))
    except Exception:
        return None


def _get_alignment_from_style_xml(style) -> WD_PARAGRAPH_ALIGNMENT | None:
    """沿样式继承链，从 style.element 的 w:pPr/w:jc 提取对齐。"""
    try:
        from docx.oxml.ns import qn

        visited = set()
        cur = style
        while cur is not None and id(cur) not in visited:
            visited.add(id(cur))
            try:
                el = getattr(cur, "element", None)
                if el is not None:
                    pPr = el.find(qn("w:pPr"))
                    if pPr is not None:
                        jc = pPr.find(qn("w:jc"))
                        if jc is not None:
                            al = _alignment_from_w_val(jc.get(qn("w:val")))
                            if al is not None:
                                return al
            except Exception:
                pass
            cur = getattr(cur, "base_style", None)
    except Exception:
        return None

    return None

def _get_doc_default_alignment(document: DocumentObject) -> WD_PARAGRAPH_ALIGNMENT | None:
    """从文档级默认/基础样式提取默认段落对齐方式。

    说明：很多 docx 并不会在 docDefaults/pPrDefault 里写 w:jc，
    而是把默认段落设置放在 Normal（或其本地化名称）样式里。

    返回：
    - 找到则返回 WD_PARAGRAPH_ALIGNMENT
    - 否则返回 None
    """
    try:
        from docx.oxml.ns import qn

        # 1) docDefaults/pPrDefault/jc
        try:
            styles_elem = document.styles.element
            docDefaults = styles_elem.find(qn("w:docDefaults"))
            if docDefaults is not None:
                pPrDefault = docDefaults.find(qn("w:pPrDefault"))
                if pPrDefault is not None:
                    pPr = pPrDefault.find(qn("w:pPr"))
                    if pPr is not None:
                        jc = pPr.find(qn("w:jc"))
                        if jc is not None:
                            al = _alignment_from_w_val(jc.get(qn("w:val")))
                            if al is not None:
                                return al
        except Exception:
            pass

        # 2) 回退：Normal/正文 等基础样式（沿继承链）
        # 注意：不同模板/语言下样式名可能不同，做多名尝试。
        style_candidates = [
            "Normal",
            "正文",
            "Body Text",
            "BodyText",
            "Normal (Web)",
        ]
        for name in style_candidates:
            try:
                st = document.styles[name]
            except Exception:
                st = None
            if st is None:
                continue
            al = _get_style_alignment(st)
            if al is not None:
                return al

    except Exception:
        return None

    return None

def _get_style_alignment(style) -> WD_PARAGRAPH_ALIGNMENT | None:
    """沿样式继承链查找 paragraph_format.alignment。"""
    visited = set()
    cur = style
    while cur is not None and id(cur) not in visited:
        visited.add(id(cur))
        try:
            pf = getattr(cur, "paragraph_format", None)
            if pf is not None and pf.alignment is not None:
                return pf.alignment
        except Exception:
            pass
        cur = getattr(cur, "base_style", None)
    return None

def get_effective_alignment(p: Paragraph, document: DocumentObject | None = None) -> WD_PARAGRAPH_ALIGNMENT | None:
    """获取段落最终对齐方式（更贴近 Word 渲染）。

    python-docx 的 p.alignment / paragraph_format.alignment 有时为 None，
    但实际对齐可能写在段落/样式 XML 的 w:pPr/w:jc 中。

    优先级（从高到低）：
    1) 段落 XML 直设：w:pPr/w:jc
    2) 段落直设：p.alignment
    3) 段落格式：p.paragraph_format.alignment
    4) 样式 XML（沿继承链）：style.element/w:pPr/w:jc
    5) 样式对象（沿继承链）：style.paragraph_format.alignment
    6) 文档默认：docDefaults/pPrDefault/jc + Normal/正文等候选样式兜底
    """
    # 1) 段落 XML 直设
    al = _get_alignment_from_paragraph_xml(p)
    if al is not None:
        return al

    # 2) 段落对象直设
    if p.alignment is not None:
        return p.alignment

    # 3) 段落格式
    try:
        if p.paragraph_format.alignment is not None:
            return p.paragraph_format.alignment
    except Exception:
        pass

    # 4) 样式 XML（继承链）
    if p.style is not None:
        al = _get_alignment_from_style_xml(p.style)
        if al is not None:
            return al

    # 5) 样式对象（继承链）
    if p.style is not None:
        al = _get_style_alignment(p.style)
        if al is not None:
            return al

    # 6) 文档默认
    if document is not None:
        return _get_doc_default_alignment(document)

    return None

def get_effective_font_pt_size(p: Paragraph) -> float | None:
    for run in p.runs:
        if len(run.text.strip()) < 2: continue # 跳过空白或过短的run，避免误判
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


def get_effective_fonts(p: Paragraph) -> tuple[str | None, str | None]:
    """返回(中文字体eastAsia, 西文字体ascii/hAnsi/name)。

    优先从 run 的 XML rFonts 提取（最可靠），其次回退到 python-docx 的 run.font.name/style.font.name。
    """
    from docx.oxml.ns import qn

    def _from_run(run: Run) -> tuple[str | None, str | None]:
        east: str | None = None
        west: str | None = None
        try:
            rPr = run._element.find(qn('w:rPr'))
            if rPr is not None:
                rFonts = rPr.find(qn('w:rFonts'))
                if rFonts is not None:
                    east = rFonts.get(qn('w:eastAsia'))
                    west = rFonts.get(qn('w:ascii')) or rFonts.get(qn('w:hAnsi'))
        except Exception:
            pass

        # 回退：python-docx 的 font.name 通常更偏“西文”
        if west is None:
            try:
                west = run.font.name or None
            except Exception:
                west = None

        return east, west

    for run in p.runs:
        if len((run.text or '').strip()) < 1:
            continue
        east, west = _from_run(run)
        if east or west:
            return east, west

    # 再回退：段落样式字体
    east = None
    west = None
    try:
        if p.style and p.style.element is not None:
            rPr = p.style.element.find(qn('w:rPr'))
            if rPr is not None:
                rFonts = rPr.find(qn('w:rFonts'))
                if rFonts is not None:
                    east = rFonts.get(qn('w:eastAsia'))
                    west = rFonts.get(qn('w:ascii')) or rFonts.get(qn('w:hAnsi'))
    except Exception:
        pass

    if west is None and p.style and p.style.font.name:
        west = p.style.font.name

    return east, west


def get_effective_font_east_asia(p: Paragraph) -> str | None:
    return get_effective_fonts(p)[0]


def get_effective_font_western(p: Paragraph) -> str | None:
    return get_effective_fonts(p)[1]

def get_bold(p: Paragraph) -> bool:
    raise NotImplementedError

def total_words(doc: DocumentObject) -> int:
    return sum(len(p.text.strip()) for p in doc.paragraphs)

def get_sections(doc: DocumentObject) -> dict[str, list[Paragraph]]:
    from collections import defaultdict

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
        "摘要：", 
        "关键词：", 
        "Abstract:", 
        "Keywords:", 
        "目录", 
        "致谢",
        "参考文献：", 
        "附录："
    ]
    paragraphs = doc.paragraphs

    # 基于标题切片（适用于手写目录/固定模板）
    p_idx = 0
    for i, section in enumerate(undergraduate_sections):
        begin, end = False, False
        while p_idx < len(paragraphs) and not end:
            for j in range(i + 1, len(undergraduate_sections)):
                if (norm_text(paragraphs[p_idx].text).startswith(undergraduate_sections[j]) if i + 1 < len(undergraduate_sections) else "") and not (
                    undergraduate_sections[j] != "目录" and _is_toc_paragraph(paragraphs[p_idx])):
                    end = True
                    break
            if end:
                break
            if norm_text(paragraphs[p_idx].text).startswith(section) and not (
                section != "目录" and _is_toc_paragraph(paragraphs[p_idx])):
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
        if "目录" in undergraduate_location and undergraduate_location["目录"]:
            toc_list = undergraduate_location["目录"]
            # 建立 paragraph 对象 -> index 的映射，避免反复 paragraphs.index() 造成 O(n^2)
            idx_map = {id(par): idx for idx, par in enumerate(paragraphs)}
            undergraduate_location["目录"] = [par for par in toc_list if idx_map.get(id(par), -1) < body_start_idx]

        # 正文：从 body_start_idx 到参考文献/附录之前（若能定位到）
        end_idx = len(paragraphs)
        for i in range(body_start_idx, len(paragraphs)):
            t = paragraphs[i].text.strip()
            if _is_toc_paragraph(paragraphs[i]):
                continue
            if any([norm_text(t).startswith(norm_text(s)) for s in ["致谢", "参考文献", "附录"]]):
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

def get_code_caption_paragraphs(document: DocumentObject) -> list[Paragraph]:
    captions = []
    def is_numbered(p: Paragraph) -> bool:
        return bool(p._p.xpath('.//w:pPr/w:numPr'))
    paragraphs = document.paragraphs
    pattern = re.compile(r"^\s*\d+\s*[\.．]\s+")
    for i, p in enumerate(paragraphs):
        if is_numbered(p) or pattern.match(p.text.strip()):
            captions.append(p)
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
        # 复用主标题识别逻辑（样式 + 文本编号形态）
        return match_heading_level(par) is not None

    def _is_toc(par: Paragraph) -> bool:
        name = _style_name(par)
        up = name.upper()
        if up.startswith("TOC"):
            return True
        if name.startswith("目录"):
            return True
        return False

    def is_special(p: Paragraph) -> bool:
        return any(
            (p.text or "").strip().replace(" ", "").replace("\u3000", "").startswith(s)
            for s in ["参考文献", "致谢", "附录", "独创性声明", "摘要", "Abstract", "关键词", "Keywords"]
        )
    
    out: list[Paragraph] = []
    for p in body:
        if not (p.text or "").strip():
            continue
        if is_special(p):
            continue
        if _is_toc(p):
            continue
        if _is_heading(p):
            continue
        if p.text.strip() in exclusion_texts:
            continue
        out.append(p)

    return out

def match_heading_level(p: Paragraph) -> Literal[1, 2, 3] | None:
    """基于样式名 + 文本编号形态推断标题级别。"""
    if len(p.text.strip()) < 2:  # 避免过短文本误判为标题
        return None
    style_level: Literal[1, 2, 3] | None = None
    name = (getattr(getattr(p, "style", None), "name", "") or "").strip()
    low = name.lower()

    if ("heading 1" in low) or ("标题 1" in name) or ("一级标题" in name):
        style_level = 1
    elif ("heading 2" in low) or ("标题 2" in name) or ("二级标题" in name):
        style_level = 2
    elif ("heading 3" in low) or ("标题 3" in name) or ("三级标题" in name):
        style_level = 3

    # normal 样式不应被误判为标题，直接返回 None
    if "normal" in low:
        return None

    # 文本兜底：1 / 1. / 1.1 / 1.1.1
    # 注意：必须从“更具体的层级”开始匹配，否则 '2.1xxx' 会被一级标题正则误判为 1 级。
    re_level: Literal[1, 2, 3] | None = None
    t = (p.text or "").strip()

    # 3级：1.1.1 xxx / 1.1.1xxx
    if re.match(r"^\d+\s*[\.．]\s*\d+\s*[\.．]\s*\d+\s*(?:[\.．]|\s)?\s*\S", t):
        re_level = 3
    # 2级：1.1 xxx / 1.1xxx
    elif re.match(r"^\d+\s*[\.．]\s*\d+\s*(?:[\.．]|\s)?\s*\S", t):
        re_level = 2
    # 1级：1 xxx / 1. xxx
    elif re.match(r"^\d+\s*(?:[\.．]|\s)\s*\S", t):
        re_level = 1

    # 如果样式和文本级别不一致，并且文本能判定出层级，则优先以文本为准（避免样式误用导致的误判）
    if re_level and re_level != style_level:
        return re_level

    return style_level if style_level else None


def config_for_level(format_config: FormatConfig, level: int) -> dict[str, Any] | None:
    if level == 1:
        return format_config.heading1_config
    if level == 2:
        return format_config.heading2_config
    if level == 3:
        return format_config.heading3_config
    if level == 4:
        return format_config.heading4_config
    if level == 5:
        return format_config.heading5_config
    if level == 6:
        return format_config.heading6_config
    return None

def attach_paragraph_indices(document: DocumentObject) -> None:
    """给 document.paragraphs 里的段落对象绑定一个稳定索引。

    目的：避免后续对子集段落调用 document.paragraphs.index(p) 失败（对象非同一实例/被重建）。

    说明：python-docx 的 Paragraph 是普通 Python 对象，允许动态挂载属性。
    """
    for i, p in enumerate(document.paragraphs):
        try:
            setattr(p, "__pp4mat_index", i)
        except Exception:
            # 极端情况下（对象限制/代理）忽略
            pass


def get_paragraph_index(p: Paragraph, document: DocumentObject | None = None) -> int:
    """获取段落在文档中的索引（优先用 attach_paragraph_indices 写入的属性）。"""
    try:
        idx = getattr(p, "__pp4mat_index")
        if isinstance(idx, int):
            return idx
    except Exception:
        pass

    if document is not None:
        # 兜底：尝试用 index()
        try:
            return document.paragraphs.index(p)
        except Exception:
            return -1

    return -1


def norm_text(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").replace("\u3000", " ").strip())

class Formatter:
    @staticmethod
    def fmt_align(alignment: WD_PARAGRAPH_ALIGNMENT | None) -> str:
        match alignment:
            case WD_PARAGRAPH_ALIGNMENT.LEFT:
                return "左对齐"
            case WD_PARAGRAPH_ALIGNMENT.CENTER:
                return "居中"
            case WD_PARAGRAPH_ALIGNMENT.RIGHT:
                return "右对齐"
            case WD_PARAGRAPH_ALIGNMENT.JUSTIFY:
                return "两端对齐"
            case WD_PARAGRAPH_ALIGNMENT.DISTRIBUTE:
                return "分散对齐"
            case WD_PARAGRAPH_ALIGNMENT.JUSTIFY_HI:
                return "两端对齐（高）" 
            case WD_PARAGRAPH_ALIGNMENT.JUSTIFY_LOW:
                return "两端对齐（低）"
            case WD_PARAGRAPH_ALIGNMENT.JUSTIFY_MED:
                return "两端对齐（中）"
            case WD_PARAGRAPH_ALIGNMENT.THAI_JUSTIFY:
                return "两端对齐（泰文）"
            case None:
                return "未设置（继承）"
            
    @staticmethod
    def fmt_font_pt_size(size: float) -> str:
        # 常见字号映射（仅供参考，实际可能因模板而异）
        size_map = {
            5: "八号",
            5.5: "七号",
            6.5: "小六",
            7.5: "六号",
            9: "小五",
            10.5: "五号",
            12: "小四",
            14: "四号",
            15: "小三",
            16: "三号",
            18: "小二",
            22: "二号",
            24: "小一",
            26: "一号",
            36: "小初",
            42: "初号",
        }
        return size_map.get(size, f"{size} pt")

