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
from .config import config

def setup_logger(name: str = "whisper_service") -> logging.Logger:
    """Configure and return a logger instance"""
    logger = logging.getLogger(name)
    logger.setLevel(config["logging"]["level"])

    # Create formatters and handlers
    formatter = logging.Formatter(config["logging"]["format"])
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        config["logging"]["file"],
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

# Global logger instance
logger = setup_logger()