import logging
import sys
import structlog
from asgi_correlation_id import correlation_id

def configure_logging(log_level: str = "INFO", json_format: bool = True):
    """
    Configures structlog and standard logging.
    """
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    # Add correlation ID to logs
    def add_correlation(logger, method_name, event_dict):
        request_id = correlation_id.get()
        if request_id:
            event_dict["request_id"] = request_id
        return event_dict

    shared_processors.append(add_correlation)

    if json_format:
        processors = shared_processors + [
            structlog.processors.JSONRenderer()
        ]
    else:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer()
        ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging to use structlog
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer() if json_format else structlog.dev.ConsoleRenderer(),
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level.upper())

    # Silence noisy loggers
    logging.getLogger("uvicorn.access").handlers = []  # We'll rely on our own middleware or uvicorn's JSON logs if needed
    logging.getLogger("uvicorn.access").propagate = False
