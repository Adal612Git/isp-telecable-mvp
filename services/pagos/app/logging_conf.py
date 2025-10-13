import time
from pythonjsonlogger import jsonlogger
import logging


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record.setdefault("timestamp", time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
        log_record.setdefault("level", record.levelname)
        log_record.setdefault("service", getattr(record, 'service', 'pagos'))
        cid = getattr(record, 'cid', None)
        if cid:
            log_record["cid"] = cid


def configure_logging(service_name: str = "pagos") -> logging.Logger:
    logger = logging.getLogger(service_name)
    handler = logging.StreamHandler()
    handler.setFormatter(CustomJsonFormatter("%(timestamp)s %(level)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger

