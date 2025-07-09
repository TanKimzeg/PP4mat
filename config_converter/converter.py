from .config_handle import Config
from .align_converter import align_convert

def convert_config(config: Config) -> None:
    """
    Converts the configuration values to the appropriate types for use in python-docx.
    
    :param config: The Config object containing the configuration values.
    """
    align_convert(config)