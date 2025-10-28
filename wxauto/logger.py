from wxauto.param import WxParam

import logging
import colorama
from pathlib import Path
from datetime import datetime
import sys
import io


# # 初始化 colorama
colorama.init()

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')

LOG_COLORS = {
    'DEBUG': colorama.Fore.CYAN,
    'INFO': colorama.Fore.GREEN,
    'WARNING': colorama.Fore.YELLOW,
    'ERROR': colorama.Fore.RED,
    'CRITICAL': colorama.Fore.MAGENTA
}

class ColoredFormatter(logging.Formatter):
    def format(self, record):
        levelname = record.levelname
        message = super().format(record)
        return f"{LOG_COLORS[levelname]}{message}{colorama.Style.RESET_ALL}"

class WxautoLogger:
    name: str = 'wxauto'

    def __init__(self):
        self.logger = self.setup_logger()
        self.file_handler = None  # 先不创建文件处理器
        self.set_debug(False)

    def setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        # 配置根记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

        # 添加asyncio日志过滤
        logging.getLogger('asyncio').setLevel(logging.WARNING)

        # 设置第三方库的日志级别
        logging.getLogger('comtypes').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)

        # 清除现有处理器
        root_logger.handlers.clear()

        # 格式
        fmt = '%(asctime)s [%(name)s] [%(levelname)s] [%(filename)s:%(lineno)d]  %(message)s'
        
        # 控制台处理器（带颜色）
        self.console_handler = logging.StreamHandler()
        console_formatter = ColoredFormatter(
            fmt=fmt,
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        self.console_handler.setFormatter(console_formatter)
        self.console_handler.setLevel(logging.DEBUG)

        root_logger.addHandler(self.console_handler)

        return logging.getLogger(self.name)

    def setup_file_logger(self):
        """根据WxParam.ENABLE_FILE_LOGGER决定是否创建文件日志处理器"""
        if not WxParam.ENABLE_FILE_LOGGER or self.file_handler is not None:
            return

        # 文件处理器（无颜色）
        log_dir = Path("wxauto_logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        # 使用当前时间创建日志文件
        current_time = datetime.now().strftime("%Y%m%d")
        log_file = log_dir / f"app_{current_time}.log"

        self.file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_formatter = logging.Formatter(
            '%(asctime)s [%(name)s] [%(levelname)s] [%(filename)s:%(lineno)d]  %(message)s',
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        self.file_handler.setFormatter(file_formatter)
        self.file_handler.setLevel(logging.DEBUG)

        # 将文件处理器添加到日志记录器
        logging.getLogger().addHandler(self.file_handler)

    def set_debug(self, debug=False):
        """动态设置日志级别"""
        if debug:
            self.console_handler.setLevel(logging.DEBUG)
        else:
            self.console_handler.setLevel(logging.INFO)

    def _ensure_file_logger(self):
        """确保文件日志处理器被初始化"""
        if WxParam.ENABLE_FILE_LOGGER and self.file_handler is None:
            self.setup_file_logger()

    def debug(self, msg: str, stacklevel=2, *args, **kwargs):
        self._ensure_file_logger()  # 确保文件日志初始化
        self.logger.debug(msg, *args, stacklevel=stacklevel, **kwargs)

    def info(self, msg: str, stacklevel=2, *args, **kwargs):
        self._ensure_file_logger()  # 确保文件日志初始化
        self.logger.info(msg, *args, stacklevel=stacklevel, **kwargs)

    def warning(self, msg: str, stacklevel=2, *args, **kwargs):
        self._ensure_file_logger()  # 确保文件日志初始化
        self.logger.warning(msg, *args, stacklevel=stacklevel, **kwargs)

    def error(self, msg: str, stacklevel=2, *args, **kwargs):
        self._ensure_file_logger()  # 确保文件日志初始化
        self.logger.error(msg, *args, stacklevel=stacklevel, **kwargs)

    def critical(self, msg: str, stacklevel=2, *args, **kwargs):
        self._ensure_file_logger()  # 确保文件日志初始化
        self.logger.critical(msg, *args, stacklevel=stacklevel, **kwargs)

# wxlog实例化的地方不再创建文件日志
wxlog = WxautoLogger()
