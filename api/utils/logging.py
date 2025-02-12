import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

def setup_logging(
    log_level: int = logging.INFO,
    log_file_prefix: str = "application",
    log_dir: str = "logs",
    max_file_size: int = 5 * 1024 * 1024,  # 5 MB
) -> logging.Logger:
    """
    Sets up and returns a centralized logger for the application.

    Args:
        log_level (int): Logging level (e.g., logging.DEBUG, logging.INFO).
        log_file_prefix (str): Prefix for the log file name.
        log_dir (str): Directory where the log file will be stored.
        max_file_size (int): Maximum size of the log file before rotation.

    Returns:
        logging.Logger: Configured logger instance.
    """
    # Create log directory if it doesn't exist
    log_dir_path = Path(log_dir)
    log_dir_path.mkdir(parents=True, exist_ok=True)

    # Configure the root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Check if the logger already has handlers
    if not logger.handlers:
        # Formatter for log messages
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Rotating file handler
        today_date = datetime.now().strftime("%Y-%m-%d")
        log_file_name = f"{log_file_prefix}_{today_date}.log"
        log_file_path = log_dir_path / log_file_name
        file_handler = RotatingFileHandler(log_file_path, maxBytes=max_file_size)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Avoid duplicate logs
    logger.propagate = False

    return logger