from __future__ import annotations

from typing import Any, TYPE_CHECKING

from docx.enum.text import WD_ALIGN_PARAGRAPH

if TYPE_CHECKING:
    from pp4mat.config_converter.config_handle import FormatConfig

"""pp4mat.config_converter.align_converter

将 YAML 配置中的对齐字符串值转换为 python-docx 使用的 ``WD_ALIGN_PARAGRAPH``。

约定：
- 仅处理 ``FormatConfig`` 中以 ``_config`` 结尾且值为 ``dict`` 的字段。
- 若 dict 中包含 ``alignment`` 键，则尝试转换。
- 不可识别/空值时使用 ``default``（默认 JUSTIFY），或在显式传入 default=None 时返回 None。
"""


_ALIGNMENT_MAP: dict[str, WD_ALIGN_PARAGRAPH] = {
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
    "distribute": WD_ALIGN_PARAGRAPH.DISTRIBUTE,
}

_REVERSE_ALIGNMENT_MAP: dict[WD_ALIGN_PARAGRAPH, str] = {v: k for k, v in _ALIGNMENT_MAP.items()}


def to_enum(alignment: Any, *, default: WD_ALIGN_PARAGRAPH | None = WD_ALIGN_PARAGRAPH.JUSTIFY) -> WD_ALIGN_PARAGRAPH | None:
    """把配置里的 alignment 值转换为 ``WD_ALIGN_PARAGRAPH``。

    支持：
    - 字符串：'left'/'center'/'right'/'justify'/'distribute'（大小写不敏感，允许前后空格）
    - 已经是 WD_ALIGN_PARAGRAPH：原样返回
    - None：返回 default

    说明：历史上你这里对未知值默认返回 JUSTIFY。为了兼容，保持该行为。
    """
    if alignment is None:
        return default

    if isinstance(alignment, WD_ALIGN_PARAGRAPH):
        return alignment

    if isinstance(alignment, str):
        key = alignment.strip().lower()
        return _ALIGNMENT_MAP.get(key, default)

    # 其他类型不处理，回退默认值
    return default


def to_string(alignment: WD_ALIGN_PARAGRAPH | None) -> str:
    """把 ``WD_ALIGN_PARAGRAPH`` 转回字符串（用于调试/导出）。"""
    if alignment is None:
        return "none"
    return _REVERSE_ALIGNMENT_MAP.get(alignment, "none")


def align_convert(config: "FormatConfig") -> "FormatConfig":
    """就地转换 config 中所有 ``*_config`` 字段里的 alignment。"""
    for attr_name, attr_value in vars(config).items():
        if not attr_name.endswith("_config"):
            continue
        if not isinstance(attr_value, dict):
            continue

        if "alignment" in attr_value:
            attr_value["alignment"] = to_enum(attr_value.get("alignment"))

    return config