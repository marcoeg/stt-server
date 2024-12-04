import modal
from pathlib import Path
import fastapi
from fastapi import FastAPI, UploadFile, Form, File
from typing import Optional, Dict

# Define the Modal app
app = modal.App("whisper-transcription")

# Create a Modal image with all required dependencies
image = (
    modal.Image.debian_slim()
    .apt_install([
        "ffmpeg",
        "libsndfile1",
        "libsndfile1-dev",
    ])
    .pip_install([
        "torch~=2.2.0", 
        "torchaudio", 
        "openai-whisper==20231117",
        "soundfile",
        "numpy",
        "fastapi",
        "python-multipart"
    ])
)

@app.cls(
    image=image,
    gpu="H100",
    container_idle_timeout=300
)
class WhisperModel:
    def __init__(self):
        self.models: Dict[str, any] = {}
        self.valid_models = ["tiny", "base", "small", "medium", "large"]

    @modal.enter()
    def initialize(self):
        import torch
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")

    def get_model(self, model_size: str):
        if model_size not in self.valid_models:
            raise ValueError(f"Invalid model size. Choose from: {', '.join(self.valid_models)}")
        
        if model_size not in self.models:
            import whisper
            print(f"Loading {model_size} model...")
            self.models[model_size] = whisper.load_model(model_size).to(self.device)
            print(f"Model {model_size} loaded successfully")
        
        return self.models[model_size]

    @modal.method()
    def transcribe(self, audio_data, model_size: str = "base", language: Optional[str] = None):
        model = self.get_model(model_size)
        
        options = {}
        if language:
            options["language"] = language
            
        result = model.transcribe(audio_data, **options)
        return result["text"]

@app.function(
    image=image,
    gpu="a10g",
    container_idle_timeout=300
)
@modal.web_endpoint(method="POST")
async def transcribe(
    audio_file: UploadFile = File(...),
    model_size: str = Form("base"),
    language: Optional[str] = Form(None)
):
    """
    Web endpoint for audio transcription.
    """
    try:
        content = await audio_file.read()
        
        # Process audio data
        import numpy as np
        import soundfile as sf
        import io
        
        with io.BytesIO(content) as audio_bytes:
            audio_data, sample_rate = sf.read(audio_bytes)
            
            # Convert to mono if stereo
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)
            
            # Convert to float32
            audio_data = audio_data.astype(np.float32)
        
        # Initialize model class
        model = WhisperModel()
        
        # Call the transcription function
        text = model.transcribe.remote(
            audio_data=audio_data,
            model_size=model_size,
            language=language
        )
        
        return fastapi.responses.JSONResponse(content={"text": text})
    except ValueError as e:
        return fastapi.responses.JSONResponse(
            content={"error": str(e)},
            status_code=400
        )
    except Exception as e:
        return fastapi.responses.JSONResponse(
            content={"error": str(e)},
            status_code=500
        )