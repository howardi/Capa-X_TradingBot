import logging
import json
import sys
from datetime import datetime
import traceback

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        
        if record.exc_info:
            log_obj["exception"] = traceback.format_exception(*record.exc_info)
            
        if hasattr(record, "extra_data"):
            log_obj.update(record.extra_data)
            
        return json.dumps(log_obj)

def setup_logger(name="CapaRoxBot", level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        
    return logger

logger = setup_logger()
