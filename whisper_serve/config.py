"""
Configuration management module for Whisper Serve.

This module provides centralized configuration handling through:
- Loading and parsing of JSON configuration files
- Environment variable overrides
- Configuration validation and processing
- Default value management

The Config class serves as a single source of truth for application settings,
providing validated configuration values to other modules in the package.

Author: Marco Graziano (marco@graziano.com)
Copyright (c) 2024 Graziano Labs Corp. All rights reserved.
"""

import os
import json
from typing import Dict, Any
import torch

class Config:
    """Configuration manager for the Whisper service"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self._validate_and_process_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
        with open(self.config_path, 'r') as f:
            config = json.load(f)
            
        # Override with environment variables if present
        if os.getenv("WHISPER_MODEL_SIZE"):
            config["model"]["size"] = os.getenv("WHISPER_MODEL_SIZE")
        if os.getenv("WHISPER_PORT"):
            config["server"]["port"] = int(os.getenv("WHISPER_PORT"))
            
        return config
        
    def _validate_and_process_config(self):
        """Validate and process configuration values"""
        # Ensure model directory exists
        model_dir = self.config["model"]["model_dir"]
        os.makedirs(model_dir, exist_ok=True)
        
        # Set absolute path for model directory
        self.config["model"]["model_dir"] = os.path.abspath(model_dir)
        
        # Auto-detect device if set to auto
        if self.config["model"]["device"] == "auto":
            self.config["model"]["device"] = "cuda" if torch.cuda.is_available() else "cpu"
            
        # Validate model size
        valid_sizes = ["tiny", "base", "small", "medium", "large"]
        if self.config["model"]["size"] not in valid_sizes:
            raise ValueError(f"Invalid model size. Must be one of: {valid_sizes}")
            
        # Adjust GPU allocation if GPU not available
        if not torch.cuda.is_available():
            self.config["deployment"]["gpu_per_replica"] = 0
            
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
        
    def __getitem__(self, key: str) -> Any:
        """Get configuration section"""
        return self.config[key]
        
    @property
    def model_path(self) -> str:
        """Get the full path to the model directory"""
        return self.config["model"]["model_dir"]
        
    @property
    def supported_formats(self) -> list:
        """Get list of supported audio formats"""
        return self.config["model"]["supported_formats"]

# Global configuration instance
config = Config()