import json
import logging
import time
from pythonjsonlogger import jsonlogger
from typing import Optional


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record.setdefault("timestamp", time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
        log_record.setdefault("level", record.levelname)
        # Service name may be injected via logger extra
        log_record.setdefault("service", getattr(record, 'service', 'clientes'))
        # Correlation id (cid) thread-local via logging extra
        cid = getattr(record, 'cid', None)
        if cid:
            log_record["cid"] = cid


def configure_logging(service_name: str = "clientes") -> logging.Logger:
    logger = logging.getLogger(service_name)
    handler = logging.StreamHandler()
    formatter = CustomJsonFormatter("%(timestamp)s %(level)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger

