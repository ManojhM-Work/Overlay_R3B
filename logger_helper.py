import logging
import os

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Log")
LOG_FILE_PATH = os.path.join(LOG_DIR, "amq_stub.log")

def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    
    logger = logging.getLogger("AMQ_STUB")
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers if setup multiple times
    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
        
        # File handler
        file_handler = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        
        # Stream console handler
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(logging.INFO)
        logger.addHandler(stream_handler)
        
    return logger

logger = setup_logging()
