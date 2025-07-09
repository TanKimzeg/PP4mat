from config_converter.config_handle import Config
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.document import Document as DocumentObject

"""
Converts alignment values from a configuration file to the corresponding
`WD_ALIGN_PARAGRAPH` values used in python-docx.
"""

@staticmethod
def to_enum(alignment: str) -> WD_ALIGN_PARAGRAPH | None:
    """
    Converts a string alignment value to a WD_ALIGN_PARAGRAPH value.
    
    :param alignment: The alignment as a string (e.g., 'left', 'center', 'right', 'justify').
    :return: Corresponding WD_ALIGN_PARAGRAPH value.
    """
    alignments = {
        'left': WD_ALIGN_PARAGRAPH.LEFT,
        'center': WD_ALIGN_PARAGRAPH.CENTER,
        'right': WD_ALIGN_PARAGRAPH.RIGHT,
        # 'justify': WD_ALIGN_PARAGRAPH.JUSTIFY
        'justify': None
        # 这里有一个奇怪的问题,word里面选择"两端对齐"时检测出来是None
    }
    
    return alignments.get(alignment.lower(), WD_ALIGN_PARAGRAPH.JUSTIFY)

@staticmethod
def to_string(alignment: WD_ALIGN_PARAGRAPH) -> str:
    """
    Converts a WD_ALIGN_PARAGRAPH value to a string representation.
    
    :param alignment: The alignment as a WD_ALIGN_PARAGRAPH value.
    :return: Corresponding string representation.
    """
    if alignment is None:
        return 'none'
    
    alignments = {
        WD_ALIGN_PARAGRAPH.LEFT: 'left',
        WD_ALIGN_PARAGRAPH.CENTER: 'center',
        WD_ALIGN_PARAGRAPH.RIGHT: 'right',
        WD_ALIGN_PARAGRAPH.JUSTIFY: 'justify'
    }
    
    return alignments.get(alignment, 'none')

def align_convert(config: Config) -> None:
    # Convert alignment values
    if config.title_config and 'alignment' in config.title_config:
        config.title_config['alignment'] = to_enum(config.title_config['alignment'])
    
    if config.text_config and 'alignment' in config.text_config:
        config.text_config['alignment'] = to_enum(config.text_config['alignment'])
    
    if config.formula_config and 'alignment' in config.formula_config:
        config.formula_config['alignment'] = to_enum(config.formula_config['alignment'])
    
    if config.figure_config and 'alignment' in config.figure_config:
        config.figure_config['alignment'] = to_enum(config.figure_config['alignment'])
    
    if config.table_config and 'alignment' in config.table_config:
        config.table_config['alignment'] = to_enum(config.table_config['alignment'])
    
    if config.reference_config and 'alignment' in config.reference_config:
        config.reference_config['alignment'] = to_enum(config.reference_config['alignment'])
    
    if config.page_config and 'alignment' in config.page_config:
        config.page_config['alignment'] = to_enum(config.page_config['alignment'])
    
    if config.abstract_config and 'alignment' in config.abstract_config:
        config.abstract_config['alignment'] = to_enum(config.abstract_config['alignment'])
    
    if config.heading1_config and 'alignment' in config.heading1_config:
        config.heading1_config['alignment'] = to_enum(config.heading1_config['alignment'])
    if config.heading2_config and 'alignment' in config.heading2_config:
        config.heading2_config['alignment'] = to_enum(config.heading2_config['alignment'])
    if config.heading3_config and 'alignment' in config.heading3_config:
        config.heading3_config['alignment'] = to_enum(config.heading3_config['alignment'])
    if config.heading4_config and 'alignment' in config.heading4_config:
        config.heading4_config['alignment'] = to_enum(config.heading4_config['alignment'])
    if config.heading5_config and 'alignment' in config.heading5_config:
        config.heading5_config['alignment'] = to_enum(config.heading5_config['alignment'])
    if config.heading6_config and 'alignment' in config.heading6_config:
        config.heading6_config['alignment'] = to_enum(config.heading6_config['alignment'])

