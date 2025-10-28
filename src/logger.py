"""
Logging configuration

Sets up structured logging with appropriate formatting and levels.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import coloredlogs


def setup_logger(level: str = 'info', log_file: Optional[str] = None) -> logging.Logger:
    """Setup structured logging with colors and file output"""
    
    # Get logger
    logger = logging.getLogger('storjcloud-client')
    
    # Set level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler with colors
    console_format = '%(asctime)s %(name)s[%(process)d] %(levelname)s %(message)s'
    coloredlogs.install(
        level=numeric_level,
        logger=logger,
        fmt=console_format,
        datefmt='%Y-%m-%d %H:%M:%S',
        field_styles={
            'asctime': {'color': 'blue'},
            'name': {'color': 'cyan'},
            'levelname': {'color': 'white', 'bold': True},
            'process': {'color': 'magenta'}
        },
        level_styles={
            'debug': {'color': 'white'},
            'info': {'color': 'green'},
            'warning': {'color': 'yellow'},
            'error': {'color': 'red'},
            'critical': {'color': 'red', 'bold': True}
        }
    )
    
    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        
        file_format = logging.Formatter(
            '%(asctime)s [%(process)d] %(name)s %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """Get a logger instance"""
    if name:
        return logging.getLogger(f'storjcloud-client.{name}')
    else:
        return logging.getLogger('storjcloud-client')
