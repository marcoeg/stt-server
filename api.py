"""
HTTP API interface for the Whisper Serve application.

This module provides:
- FastAPI application definition
- REST endpoint implementations
- Request validation and error handling
- Health check endpoints
- Integration with Ray Serve for deployment

Serves as the interface layer between HTTP clients and the transcription service,
handling all aspects of the REST API including request parsing and response formatting.

Author: Marco Graziano (marco@graziano.com)
Copyright (c) 2024 Graziano Labs Corp. All rights reserved.
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from ray import serve
from ray.serve.handle import DeploymentHandle
from logger import logger

app = FastAPI()

@serve.deployment
@serve.ingress(app)
class WhisperAPI:
    def __init__(self, transcriber: DeploymentHandle):
        self.transcriber = transcriber

    @app.post("/transcribe")
    async def transcribe(self, audio_file: UploadFile = File(...)):
        # Validate file format
        if not any(audio_file.filename.endswith(fmt) 
                  for fmt in ["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"]):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported audio format. Supported formats: mp3, mp4, mpeg, mpga, m4a, wav, webm") #{config.supported_formats}"
            
        try:
            logger.info(f"Processing file: {audio_file.filename}")
            audio_data = await audio_file.read()
            result = await self.transcriber.remote(audio_data)
            return result
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error processing request: {str(e)}"
            )
            
    @app.get("/health")
    async def health_check(self):  
        """Health check endpoint"""
        return {"status": "healthy"}