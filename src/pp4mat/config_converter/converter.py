from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

from pp4mat.config_converter.align_converter import align_convert

if TYPE_CHECKING:
    from pp4mat.config_converter.config_handle import FormatConfig

"""pp4mat.config_converter.converter

配置转换入口：把 YAML 读入的原始值转换为程序内部使用的类型（例如 python-docx 的枚举）。

约定：converter 的签名为 ``(FormatConfig) -> FormatConfig``，允许就地修改并返回同一个对象，
便于做成 pipeline。
"""

Converter = Callable[["FormatConfig"], "FormatConfig"]


def default_converters() -> list[Converter]:
    """内置的默认转换器列表（按顺序执行）。"""
    return [
        align_convert,
    ]


def apply_converters(config: "FormatConfig", converters: Iterable[Converter]) -> "FormatConfig":
    """按顺序应用一组 converters。"""
    for conv in converters:
        config = conv(config)
    return config


def convert_config(config: "FormatConfig", converters: Iterable[Converter] | None = None) -> "FormatConfig":
    """对外入口（向后兼容）。

    - 旧用法：``convert_config(cfg)``
    - 新用法：``convert_config(cfg, [align_convert, ...])``
    """
    return apply_converters(config, converters or default_converters())