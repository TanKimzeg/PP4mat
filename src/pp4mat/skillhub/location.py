"""位置/定位工具。

本模块参考 paper-check 项目里的 DocumentStructure 思路，
在不引入其整套脚本的前提下，提供：
- 段落所属区域/章节定位
- 生成用于报告的简短定位字符串

定位结果用于 checker 输出更可读的错误信息与自动修复日志。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from docx.document import Document as DocumentObject
from docx.text.paragraph import Paragraph


Region = Literal[
    "封面",
    "原创性声明",
    "授权声明",
    "中文摘要",
    "英文摘要",
    "目录",
    "正文",
    "参考文献",
    "致谢",
    "附录",
    "未知",
]


@dataclass(frozen=True)
class ParaLocation:
    index: int
    region: Region
    chapter: str | None = None
    section: str | None = None
    subsection: str | None = None

    def short(self) -> str:
        if self.region != "正文" and self.region != "未知":
            return self.region
        if self.section:
            return self.section
        if self.chapter:
            return self.chapter
        return self.region

    def full(self) -> str:
        parts: list[str] = []
        if self.region and self.region != "正文":
            parts.append(f"【{self.region}】")
        if self.chapter:
            parts.append(f"章: {self.chapter}")
        if self.section:
            parts.append(f"节: {self.section}")
        if self.subsection:
            parts.append(f"小节: {self.subsection}")
        return " > ".join(parts) if parts else self.region


class DocumentStructure:
    """为 doc.paragraphs 中每个段落提供稳定的区域/章节归属。"""

    SPECIAL_SECTIONS: dict[Region, list[str]] = {
        "封面": ["本科", "毕业论文", "毕业设计", "学位论文"],
        "原创性声明": ["原创性声明", "独创性声明", "学术诚信"],
        "授权声明": ["授权声明", "使用授权", "授权书"],
        "中文摘要": ["摘要", "摘 要", "摘  要", "摘　要"],
        "英文摘要": ["abstract"],
        "目录": ["目录", "目 录", "目  录", "目　录"],
        "参考文献": ["参考文献", "参 考 文 献", "参  考  文  献"],
        "致谢": ["致谢", "致  谢", "致　谢", "致 谢"],
        "附录": ["附录", "附  录"],
    }

    def __init__(self, doc: DocumentObject):
        self.doc = doc
        self.paragraphs = doc.paragraphs
        self._loc: dict[int, ParaLocation] = {}
        self._build()

    @staticmethod
    def _clean(s: str) -> str:
        return (s or "").strip().lower().replace(" ", "").replace("\u3000", "")

    def _is_special_section(self, text: str, found_body: bool, after_references: bool) -> Region | None:
        text_clean = self._clean(text)
        text_len = len((text or "").strip())

        for region, keywords in self.SPECIAL_SECTIONS.items():
            for kw in keywords:
                if self._clean(kw) in text_clean:
                    if region == "封面":
                        if found_body or after_references:
                            continue
                        if text_len > 100:
                            continue
                    if region in {"中文摘要", "英文摘要", "目录", "参考文献", "致谢", "附录"}:
                        if text_len > 50:
                            continue
                    if region in {"原创性声明", "授权声明"}:
                        if text_len > 80:
                            continue
                    return region
        return None

    def _build(self) -> None:
        current_region: Region = "未知"
        found_body = False
        after_references = False

        current_chapter: str | None = None
        current_section: str | None = None
        current_subsection: str | None = None

        for i, p in enumerate(self.paragraphs):
            text = (p.text or "").strip()
            style_name = (getattr(getattr(p, "style", None), "name", "") or "").strip()

            if text:
                special = self._is_special_section(text, found_body, after_references)
                if special is not None:
                    current_region = special
                    current_chapter = None
                    current_section = None
                    current_subsection = None
                    if special == "参考文献":
                        after_references = True
                    self._loc[i] = ParaLocation(i, current_region)
                    continue

            # 标题样式：尽量兼容中英文样式名
            low = style_name.lower()
            is_h1 = ("heading 1" in low) or ("标题 1" in style_name) or ("一级标题" in style_name)
            is_h2 = ("heading 2" in low) or ("标题 2" in style_name) or ("二级标题" in style_name)
            is_h3 = ("heading 3" in low) or ("标题 3" in style_name) or ("三级标题" in style_name)

            if is_h1:
                found_body = True
                current_region = "正文"
                current_chapter = text or current_chapter
                current_section = None
                current_subsection = None
            elif is_h2:
                current_region = "正文" if found_body else current_region
                current_section = text or current_section
                current_subsection = None
            elif is_h3:
                current_region = "正文" if found_body else current_region
                current_subsection = text or current_subsection

            if current_region == "未知" and found_body:
                current_region = "正文"

            self._loc[i] = ParaLocation(
                index=i,
                region=current_region,
                chapter=current_chapter,
                section=current_section,
                subsection=current_subsection,
            )

    def get(self, para_index: int) -> ParaLocation:
        return self._loc.get(para_index, ParaLocation(para_index, "未知"))

    def locate_paragraph(self, p: Paragraph) -> ParaLocation:
        """通过对象 id() 快速定位；失败则降级为未知。"""
        try:
            idx = self.paragraphs.index(p)
            return self.get(idx)
        except Exception:
            return ParaLocation(-1, "未知")
