import logging
import orjson
from typing import Any, Dict

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data: Dict[str, Any] = {
            "level": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
        }
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return orjson.dumps(data).decode()

def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())
    for h in list(root.handlers):
        root.removeHandler(h)
    h = logging.StreamHandler()
    h.setFormatter(JsonFormatter())
    root.addHandler(h)
