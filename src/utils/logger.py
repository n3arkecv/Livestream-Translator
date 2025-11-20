import logging
import colorama
from colorama import Fore, Style

colorama.init()

class SystemLogger:
    def __init__(self, name="System"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def info(self, message: str, **kwargs):
        self.logger.info(f"{Fore.BLUE}{message}{Style.RESET_ALL} {kwargs if kwargs else ''}")

    def warning(self, message: str, **kwargs):
        self.logger.warning(f"{Fore.YELLOW}{message}{Style.RESET_ALL} {kwargs if kwargs else ''}")

    def error(self, message: str, exc: Exception = None, **kwargs):
        self.logger.error(f"{Fore.RED}{message}{Style.RESET_ALL} {kwargs if kwargs else ''}", exc_info=exc)

