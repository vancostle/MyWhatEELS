import os, logging

class Logger:
    _loggers = {}

    @classmethod
    def get_logger(
        cls,
        log_file: str = "default_log_file.log",
        logger_name: str = None,
        console: bool = False
    ):
        """
        Get the logger instance for the module.
        If console=True, also log to the console (StreamHandler). Otherwise, only log to file.
        """
        if logger_name is None:
            logger_name = __name__
        logger_key = f"{logger_name}:{log_file}:{console}"
        if logger_key in cls._loggers:
            return cls._loggers[logger_key]

        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)

        # Ensure logs directory exists
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        log_path = os.path.join(logs_dir, log_file)

        formatter = logging.Formatter(
            "%(asctime)s : %(name)s : %(levelname)s : %(funcName)s : %(message)s"
        )

        # Avoid adding handlers multiple times
        if not any(isinstance(h, logging.FileHandler) and getattr(h, 'baseFilename', None) == os.path.abspath(log_path) for h in logger.handlers):
            file_handler = logging.FileHandler(log_path)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        if console:
            if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
                stream_handler = logging.StreamHandler()
                stream_handler.setFormatter(formatter)
                logger.addHandler(stream_handler)

        logger.propagate = False  # Prevent logs from propagating to the root logger
        # Ensure logger is not already in the loggers dictionary
        cls._loggers[logger_key] = logger
        return logger
