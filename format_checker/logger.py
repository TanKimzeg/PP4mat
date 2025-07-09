import logging
import sys
import colorama
import datetime
import os

# Initialize colorama for Windows compatibility
colorama.init(autoreset=True)

def setup_logger(name=__package__, level=logging.INFO) -> logging.Logger:
    """创建并配置日志记录器"""
    class ColorFormatter(logging.Formatter):
        """自定义日志格式化器，添加颜色到日志级别"""
        LEVEL_COLORS = {
            "DEBUG": colorama.Fore.BLUE,  # 蓝色
            "INFO": colorama.Fore.GREEN,  # 绿色
            "WARNING": colorama.Fore.YELLOW,  # 黄色
            "ERROR": colorama.Fore.RED,  # 红色
            "CRITICAL": colorama.Fore.MAGENTA,  # 紫色
        }

        def format(self, record):
            levelname = record.levelname
            if levelname in self.LEVEL_COLORS:
                record.levelname = f"{self.LEVEL_COLORS[levelname]}{levelname}{colorama.Style.RESET_ALL}"
            return super().format(record)
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 禁用传播
    logger.propagate = False

    # 避免重复添加处理器（防止多次调用时重复日志）
    if not logger.handlers:
        # 创建格式化器
        consoler_formatter = ColorFormatter(
            '[%(asctime)s-%(levelname)s] %(name)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        file_formatter = logging.Formatter(
            '[%(asctime)s-%(levelname)s] %(name)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        
        if logger.level != logging.DEBUG:
            if not os.path.exists('./error_logs'):
                os.makedirs('./error_logs')
            file_handler = logging.FileHandler(f'./error_logs/{datetime.datetime.now().strftime("%H%M%S")}.log', encoding='utf-8')
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(logging.ERROR)
            logger.addHandler(file_handler)
        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(consoler_formatter)
        logger.addHandler(console_handler)
        # 疑似logger的Bug,这两行Handler的顺序不能交换,否则日志文件会输出控制台的颜色代码
    
    return logger