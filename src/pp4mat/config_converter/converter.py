from pp4mat.config_converter.config_handle import FormatConfig
from pp4mat.config_converter.align_converter import align_convert

def convert_config(config: FormatConfig) -> None:
    """
    Converts the configuration values to the appropriate types for use in python-docx.
    
    :param config: The Config object containing the configuration values.
    """
    align_convert(config)