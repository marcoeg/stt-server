"""
Logging configuration and management for Whisper Serve.

This module handles:
- Logger initialization and configuration
- Log file rotation and management
- Log formatting
- Centralized logging setup for all modules

Provides a consistent logging interface across the application, supporting both
file and console logging with appropriate formatting and log level management.

Author: Marco Graziano (marco@graziano.com)
Copyright (c) 2024 Graziano Labs Corp. All rights reserved.
"""

import logging
from logging.handlers import RotatingFileHandler
import sys
import os

log_level = os.getenv('LOG_LEVEL', 'INFO')
log_format = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_file = "/home/ubuntu/logs/whisper_service.log" #"/shared/logs/whisper_service.log"
    

def setup_logger(name: str = "whisper_service") -> logging.Logger:
    """Configure and return a logger instance"""
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Create formatters and handlers
    formatter = logging.Formatter(log_format)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

# Global logger instance
logger = setup_logger()