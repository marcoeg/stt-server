"""
Utility functions for the Whisper Serve application.

This module provides common utilities including:
- Audio file processing and validation
- Temporary file management
- Format conversion utilities
- Generic helper functions

Contains shared functionality used across different modules of the application,
particularly focusing on audio processing and file handling operations.

Author: Marco Graziano (marco@graziano.com)
Copyright (c) 2024 Graziano Labs Corp. All rights reserved.
"""

import os
import tempfile
from typing import Optional
import numpy as np
import whisper
from .logger import logger

def load_audio(file_content: bytes) -> Optional[np.ndarray]:
    """Load audio using whisper's built-in function"""
    temp_file = None
    try:
        # Create a temporary file with the correct extension
        temp_fd, temp_file = tempfile.mkstemp(suffix='.wav')
        os.close(temp_fd)  # Close file descriptor
        
        # Write content to temporary file
        with open(temp_file, "wb") as f:
            f.write(file_content)
        
        # Load audio using whisper's function
        logger.debug(f"Loading audio from temporary file: {temp_file}")
        audio = whisper.load_audio(temp_file)
        
        if len(audio) == 0:
            raise ValueError("Audio file is empty")
            
        return audio
        
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        raise ValueError(f"Error processing audio: {str(e)}")
        
    finally:
        # Clean up temp file
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception as e:
                logger.warning(f"Failed to remove temporary file {temp_file}: {str(e)}")