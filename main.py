"""
Main entry point for the Whisper Serve application.

This module orchestrates the initialization and deployment of the Ray Serve application.
It handles:
- Command line argument parsing
- Service initialization and deployment
- Signal handling for graceful shutdown
- Main service loop management

The module serves as the primary executable for starting the Whisper transcription service.

Author: Marco Graziano (marco@graziano.com)
Copyright (c) 2024 Graziano Labs Corp. All rights reserved.
"""

import ray
from ray import serve
import signal
import time
import argparse
from whisper_serve.config import config
from whisper_serve.models import ModelLoader, WhisperTranscriber
from whisper_serve.api import WhisperAPI
from whisper_serve.logger import logger

# Global flag for graceful shutdown
running = True

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global running
    logger.info("Received shutdown signal. Cleaning up...")
    running = False

def create_deployment():
    """Create and deploy the Whisper service"""
    if ray.is_initialized():
        ray.shutdown()
        
    # Initialize Ray
    ray.init(num_cpus=config["server"]["num_cpus"])
    
    # Start Ray Serve
    serve.start(
        http_options={
            "host": config["server"]["host"],
            "port": config["server"]["port"]
        },
        dedicated_cpu=config["server"]["dedicated_cpu"],
    )

    # Create model loader and preload the model
    model_loader = ModelLoader.remote()
    ray.get(model_loader.load_model.remote(config["model"]["size"]))
    
    # Deploy the transcriber
    transcriber = WhisperTranscriber.bind(
        model_size=config["model"]["size"],
        model_loader=model_loader
    )
    
    # Deploy the API
    api = WhisperAPI.bind(transcriber)

    # Deploy both with route prefix
    serve.run(
        api,
        route_prefix="/",
        name="whisper_service"
    )

    logger.info(f"\nService is ready! Listening at http://{config['server']['host']}:{config['server']['port']}")
    logger.info("Press Ctrl+C to shutdown")

def main():
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        create_deployment()
        
        # Keep the main process running
        while running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        raise
    finally:
        logger.info("Cleaning up Ray resources...")
        ray.shutdown()
        logger.info("Shutdown complete")

if __name__ == "__main__":
    main()