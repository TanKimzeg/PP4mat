from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError
import sys
from .logger import setup_logger

logger = setup_logger(__package__)

class Config:
    def __init__(self,config_path:str) -> None:
        self.yaml = YAML()
        self.config_path = config_path
        self.reload()
        logger.info(f"从 {self.config_path} 加载配置文件")

    def _load_config(self) -> dict:
        """ 定义如何加载配置文件"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as file:
                config = self.yaml.load(file)
            return config
        except FileNotFoundError:
            logger.critical(f"配置文件 '{self.config_path}' 未找到.")
            sys.exit(f"Error: Configuration file '{self.config_path}' not found.")
        except YAMLError as e:
            logger.critical(f"解析配置文件 '{self.config_path}' 时出错: {e}")
            sys.exit(f"Error: Failed to parse configuration file '{self.config_path}': {e}")

    def reload(self) -> None:
        """ 将配置文件里面的参数,赋予单独的变量,方便后面程序调用. """
        configs = self._load_config()

        self.title_config:dict | None = configs.get('title', None)
        self.text_config:dict | None = configs.get('text', None)
        self.formula_config:dict | None = configs.get('formula', None)
        self.figure_config:dict | None = configs.get('figure', None)
        self.table_config:dict | None = configs.get('table', None)
        self.reference_config:dict | None = configs.get('reference', None)
        self.page_config:dict | None = configs.get('page', None)
        self.abstract_config:dict | None = configs.get('abstract', None)
        self.heading1_config:dict | None = configs.get('heading1', None)
        self.heading2_config:dict | None = configs.get('heading2', None)
        self.heading3_config:dict | None = configs.get('heading3', None)
        self.heading4_config:dict | None = configs.get('heading4', None)
        self.heading5_config:dict | None = configs.get('heading5', None)
        self.heading6_config:dict | None = configs.get('heading6', None)
        self.words_min_count:int | None = configs.get('words_min_count', None)
        self.citation_min_count:int | None = configs.get('citation_min_count', None)
        self.chapter_min_count: int | None = configs.get('chapter_min_count', None)
