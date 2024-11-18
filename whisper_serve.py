import ray
from ray import serve
from ray.serve.handle import DeploymentHandle
import whisper
import torch
import numpy as np
from dataclasses import dataclass
from typing import Dict, Any, Optional
import time
import os
import warnings
from fastapi import FastAPI, File, UploadFile, HTTPException
import io
import signal

# Suppress warnings
warnings.filterwarnings("ignore")
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
torch.set_warn_always(False)

# Configure model directory
MODEL_DIR = os.path.join(os.getcwd(), "models")
os.makedirs(MODEL_DIR, exist_ok=True)

# Global flag for graceful shutdown
running = True

def signal_handler(signum, frame):
    global running
    print("\nReceived shutdown signal. Cleaning up...")
    running = False

@dataclass
class TranscriptionResult:
    """Data class for transcription results"""
    success: bool
    text: str
    latency: float
    word_count: int
    gpu_memory: float
    error: Optional[str] = None

def load_audio(file_content: bytes) -> np.ndarray:
    """Load audio using whisper's built-in function"""
    try:
        # Save bytes to a temporary file
        temp_file = "temp_audio.wav"
        with open(temp_file, "wb") as f:
            f.write(file_content)
        
        # Load audio using whisper's function
        try:
            audio = whisper.load_audio(temp_file)
            return audio
        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)
                
    except Exception as e:
        raise ValueError(f"Error processing audio: {str(e)}")

@ray.remote
class ModelLoader:
    """Centralized model loading to avoid multiple downloads"""
    def __init__(self):
        self.loaded_models = {}

    def load_model(self, model_size: str) -> str:
        if model_size not in self.loaded_models:
            print(f"Loading Whisper {model_size} model centrally...")
            # Override torch.load to use weights_only=True
            original_torch_load = torch.load
            torch.load = lambda f, **kwargs: original_torch_load(f, weights_only=True, **kwargs)
            
            try:
                model = whisper.load_model(
                    model_size,
                    download_root=MODEL_DIR
                )
                self.loaded_models[model_size] = MODEL_DIR
                print(f"Model {model_size} loaded and cached successfully!")
            finally:
                torch.load = original_torch_load
                
        return self.loaded_models[model_size]

@serve.deployment(
    num_replicas=4,
    ray_actor_options={
        "num_cpus": 0.5,
        "num_gpus": 0.1 if torch.cuda.is_available() else 0
    }
)
class WhisperTranscriber:
    def __init__(self, model_size: str = "base", model_loader=None):
        self.model_size = model_size
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.model_loader = model_loader
        self._load_model()

    def _load_model(self):
        if self.model is None:
            try:
                original_torch_load = torch.load
                torch.load = lambda f, **kwargs: original_torch_load(f, weights_only=True, **kwargs)
                
                try:
                    self.model = whisper.load_model(
                        self.model_size,
                        device=self.device,
                        download_root=MODEL_DIR
                    )
                    if self.device == "cuda":
                        self.model = self.model.cuda()
                finally:
                    torch.load = original_torch_load
                    
            except Exception as e:
                print(f"Error loading model: {str(e)}")
                raise RuntimeError(f"Failed to load Whisper model: {str(e)}")

    async def __call__(self, audio_data: bytes) -> Dict[str, Any]:
        start_time = time.time()
        
        try:
            # Load and process audio
            audio = load_audio(audio_data)
            
            if len(audio) == 0:
                raise ValueError("Audio file is empty or corrupted")

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
            print(f"Transcription error: {str(e)}")  # Add logging
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

app = FastAPI()

@serve.deployment
@serve.ingress(app)
class WhisperAPI:
    def __init__(self, transcriber: DeploymentHandle):
        self.transcriber = transcriber

    @app.post("/transcribe")
    async def transcribe(self, audio_file: UploadFile = File(...)):
        if not audio_file.filename.endswith(('.wav', '.mp3', '.m4a', '.ogg')):
            raise HTTPException(
                status_code=400,
                detail="Unsupported audio format. Please upload .wav, .mp3, .m4a, or .ogg files."
            )
        
        try:
            audio_data = await audio_file.read()
            result = await self.transcriber.remote(audio_data)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

def create_deployment(model_size: str = "base"):
    """Create and deploy the Whisper service"""
    if ray.is_initialized():
        ray.shutdown()
        
    ray.init(num_cpus=4)
    
    # Start Ray Serve
    serve.start(
        http_options={"host": "0.0.0.0", "port": 8000},
        dedicated_cpu=True,
    )

    # Create model loader and preload the model
    model_loader = ModelLoader.remote()
    ray.get(model_loader.load_model.remote(model_size))
    
    # Deploy the transcriber
    transcriber = WhisperTranscriber.bind(model_size=model_size, model_loader=model_loader)
    
    # Deploy the API
    api = WhisperAPI.bind(transcriber)

    # Deploy both with route prefix
    serve.run(
        api,
        route_prefix="/",
        name="whisper_service"
    )

    print("\nService is ready! Listening at http://localhost:8000")
    print("Press Ctrl+C to shutdown")

def main():
    import argparse
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    parser = argparse.ArgumentParser(description="Deploy Whisper service with Ray Serve")
    parser.add_argument("--model", default="base",
                      choices=["tiny", "base", "small", "medium", "large"])
    args = parser.parse_args()
    
    try:
        create_deployment(model_size=args.model)
        
        # Keep the main process running
        while running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    finally:
        print("Cleaning up Ray resources...")
        ray.shutdown()
        print("Shutdown complete")

if __name__ == "__main__":
    main()