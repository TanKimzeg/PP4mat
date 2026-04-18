import datetime
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

import colorama

# Initialize colorama for Windows compatibility
colorama.init(autoreset=True)


def setup_logger(
    name: str | None = None,
    level: int = logging.INFO,
    log_dir: Path | None = None,
    log_file: str | None = None,
    console: bool = True,
    file: bool | None = None,
    propagate: bool = False,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> logging.Logger:
    """创建并配置日志记录器（极简版）。

    约定：
    - 只在第一次调用时挂载 handler（避免重复输出）
    - 后续调用仅更新 logger 的 level/propagate
    - console/file handler 分离：控制台有颜色，文件无颜色
    - file=None：仅对入口 logger（pp4mat/__main__）默认启用文件日志
    """

    class ColorFormatter(logging.Formatter):
        LEVEL_COLORS = {
            "DEBUG": colorama.Fore.BLUE,
            "INFO": colorama.Fore.GREEN,
            "WARNING": colorama.Fore.YELLOW,
            "ERROR": colorama.Fore.RED,
            "CRITICAL": colorama.Fore.MAGENTA,
        }

        def format(self, record: logging.LogRecord) -> str:
            original_levelname = record.levelname
            try:
                color = self.LEVEL_COLORS.get(original_levelname)
                if color:
                    record.levelname = f"{color}{original_levelname}{colorama.Style.RESET_ALL}"
                return super().format(record)
            finally:
                record.levelname = original_levelname

    resolved_name = name or (__package__ if __package__ else "pp4mat")
    logger = logging.getLogger(resolved_name)

    # 每次调用都允许更新基础属性
    logger.setLevel(level)
    logger.propagate = propagate

    # 已初始化则直接返回（极简：不再响应 console/file 的开关变化）
    if getattr(logger, "_pp4mat_configured", False):
        return logger

    fmt = "[%(asctime)s-%(levelname)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    # file=None 的默认策略
    if file is None:
        file = resolved_name in {"pp4mat", "__main__"}

    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(ColorFormatter(fmt, datefmt=datefmt))
        logger.addHandler(console_handler)

    if file:
        _log_dir = log_dir or Path.cwd() / "logs"
        _log_dir.mkdir(parents=True, exist_ok=True)

        _log_file = log_file or f"{datetime.date.today().strftime('%Y%m%d')}.log"
        log_path = _log_dir / _log_file

        file_handler = RotatingFileHandler(
            filename=log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        # 文件建议更全，控制台由 level 控制噪声
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
        logger.addHandler(file_handler)

    logger._pp4mat_configured = True  # type: ignore[attr-defined]
    return logger
