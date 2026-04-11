"""轻量规则引擎（为格式检测/修复提供统一规则定义）。

目标：把 paper-check 项目中“规则化检测 + 精确定位”的思想融合进来，
但保持 Paper4mat 当前的结构。

规则形态：
- check(paragraph, ctx) -> list[Issue]
- fix(paragraph, ctx) -> bool (可选)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal

from docx.document import Document as DocumentObject
from docx.text.paragraph import Paragraph

from pp4mat.skillhub.location import DocumentStructure, ParaLocation


Severity = Literal["error", "warning"]


@dataclass
class Issue:
    category: str
    message: str
    severity: Severity = "error"
    location: str | None = None
    preview: str | None = None
    fixable: bool = False
    rule_id: str | None = None


@dataclass
class CheckContext:
    doc: DocumentObject
    structure: DocumentStructure
    config: Any

    def loc_of(self, idx: int) -> ParaLocation:
        return self.structure.get(idx)


RuleCheck = Callable[[Paragraph, int, CheckContext], list[Issue]]
RuleFix = Callable[[Paragraph, int, CheckContext], bool]


@dataclass
class ParagraphRule:
    rule_id: str
    category: str
    applies_to_regions: set[str] | None
    check: RuleCheck
    fix: RuleFix | None = None

    def applies(self, region: str) -> bool:
        if self.applies_to_regions is None:
            return True
        return region in self.applies_to_regions
