import logging
import sys
import colorama

# Initialize colorama for Windows compatibility
colorama.init(autoreset=True)

def setup_logger(name=__package__, level=logging.INFO):
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
        formatter = ColorFormatter(
            '[%(asctime)s-%(levelname)s] %(name)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        
        # 可选：创建文件处理器
        # file_handler = logging.FileHandler('package_logs.log')
        # file_handler.setFormatter(formatter)
        
        # 添加处理器
        logger.addHandler(console_handler)
        # logger.addHandler(file_handler)
    
    return logger