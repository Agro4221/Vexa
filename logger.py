from __future__ import annotations
import logging
from logging.handlers import RotatingFileHandler
import config

_logger=logging.getLogger("vexa")

def _configure():
    if _logger.handlers:
        return
    _logger.setLevel(logging.INFO)
    fmt=logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s",datefmt="%Y-%m-%d %H:%M:%S")
    console=logging.StreamHandler(); console.setFormatter(fmt)
    file_handler=RotatingFileHandler(config.LOG_DIR/"vexa.log",maxBytes=5*1024*1024,backupCount=5,encoding="utf-8"); file_handler.setFormatter(fmt)
    _logger.addHandler(console); _logger.addHandler(file_handler); _logger.propagate=False

_configure()

def log_event(category:str,message:str,level:int=logging.INFO)->None:
    _logger.log(level,"[%s] %s",category.upper(),message)

def clear_old_data(max_age_hours:float=24.0)->None:
    import time
    now=time.time(); removed=0
    for path in config.VISION_DIR.glob("*"):
        try:
            if path.is_file() and now-path.stat().st_mtime>max_age_hours*3600:
                path.unlink(); removed+=1
        except OSError as exc:
            log_event("SYSTEM",f"Не удалось удалить {path}: {exc}",logging.WARNING)
    log_event("SYSTEM",f"Очистка старых данных зрения: удалено {removed} файлов.")
