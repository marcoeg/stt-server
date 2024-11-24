"""
Core model management and transcription logic for Whisper Serve.

This module implements:
- ModelLoader: Ray actor for centralized model loading and caching
- WhisperTranscriber: Main transcription deployment handling inference
- TranscriptionResult: Data class for standardized result formatting

The module serves as the computational core of the application, managing model lifecycle
and performing the actual transcription tasks in a distributed manner via Ray.

Author: Marco Graziano (marco@graziano.com)
Copyright (c) 2024 Graziano Labs Corp. All rights reserved.
"""

import ray
from ray import serve
import whisper
import torch
from dataclasses import dataclass
from typing import Dict, Any, Optional
import time
from logger import logger
from utils import load_audio

@dataclass
class TranscriptionResult:
    """Data class for transcription results"""
    success: bool
    text: str
    latency: float
    word_count: int
    gpu_memory: float
    error: Optional[str] = None

@ray.remote
class ModelLoader:
    """Centralized model loading to avoid multiple downloads"""
    def __init__(self):
        self.loaded_models = {}

    # model_size is the name of the whisper model which is also its size (base, large, turbo, ..)
    def load_model(self, model_size: str) -> str:
        if model_size not in self.loaded_models:
            logger.info(f"Loading Whisper {model_size} model centrally...")
            # Override torch.load to use weights_only=True
            original_torch_load = torch.load
            torch.load = lambda f, **kwargs: original_torch_load(f, weights_only=True, **kwargs)
            
            try:
                model = whisper.load_model(
                    model_size,
                    download_root="/shared/models" #config.model_path
                )
                self.loaded_models[model_size] = "/shared/models" #config.model_path
                logger.info(f"Model {model_size} loaded and cached successfully!")
            finally:
                torch.load = original_torch_load
                
        return self.loaded_models[model_size]
    
@serve.deployment
class WhisperTranscriber:
    def __init__(self, model_size: str = "base", model_loader = None):
        logger.info(f"Starting WhisperTranscriber initialization: model_size={model_size}, model_loader present={model_loader is not None}")
        self.model_size = model_size
        self.model_loader = model_loader
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")
        self.model = None
        logger.info("About to load model...")
        self._load_model()
        logger.info("WhisperTranscriber initialization completed")

    def _load_model(self):
        if self.model is None:
            try:
                if self.model_loader:
                    logger.info("Using model_loader for cached path")
                    model_path = ray.get(self.model_loader.load_model.remote(self.model_size))
                    logger.info(f"Got cached model path: {model_path}")
                
                logger.info("Setting up torch load override")
                original_torch_load = torch.load
                torch.load = lambda f, **kwargs: original_torch_load(f, weights_only=True, **kwargs)

                try:
                    logger.info(f"Loading Whisper model {self.model_size}")
                    self.model = whisper.load_model(
                        self.model_size,
                        device=self.device,
                        download_root="/shared/models"
                    )
                    if self.device == "cuda":
                        self.model = self.model.cuda()
                    logger.info("Model loaded successfully")
                finally:
                    torch.load = original_torch_load
                    
            except Exception as e:
                logger.error(f"Error loading model: {str(e)}", exc_info=True)
                raise RuntimeError(f"Failed to load Whisper model: {str(e)}")

    async def __call__(self, audio_data: bytes) -> Dict[str, Any]:
        start_time = time.time()
        
        try:
            # Load and process audio
            audio = load_audio(audio_data)
            
            # Get initial GPU memory state
            start_mem = torch.cuda.memory_allocated() / (1024**3) if torch.cuda.is_available() else 0
            
            # Transcribe
            result = self.model.transcribe(audio)
            
            # Calculate memory usage
            end_mem = torch.cuda.memory_allocated() / (1024**3) if torch.cuda.is_available() else 0
            memory_used = end_mem - start_mem
            
            transcription_result = TranscriptionResult(
                success=True,
                text=result["text"],
                latency=time.time() - start_time,
                word_count=len(result["text"].split()),
                gpu_memory=memory_used
            )
            
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            transcription_result = TranscriptionResult(
                success=False,
                text="",
                latency=time.time() - start_time,
                word_count=0,
                gpu_memory=0,
                error=str(e)
            )
        finally:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        return transcription_result.__dict__