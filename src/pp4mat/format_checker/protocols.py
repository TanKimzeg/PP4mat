from __future__ import annotations

from typing import Protocol, TypeAlias

FormatErrors: TypeAlias = dict[str, list[str]]


class FormatChecker(Protocol):
    def check_format(self) -> None:
        """检查论文格式，把错误写入构造时传入的 errors 容器。"""
        ...
