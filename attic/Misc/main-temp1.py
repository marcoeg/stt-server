from ray import serve
from fastapi import FastAPI
from starlette.requests import Request
from transformers import pipeline
from ray.serve.handle import DeploymentHandle
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WhisperService")
app = FastAPI()

@serve.deployment
class WhisperTranscriber:
    def __init__(self):
        self.transcriber = pipeline(
            "automatic-speech-recognition",
            model="openai/whisper-base",
            device="cuda"
        )

    async def __call__(self, audio_data: bytes) -> dict:
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            tmp_file.write(audio_data)
            tmp_file_path = tmp_file.name
        
        try:
            result = self.transcriber(tmp_file_path)
            return {"success": True, "text": result["text"]}
        finally:
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

@serve.deployment
@serve.ingress(app)
class WhisperAPI:
    def __init__(self, transcriber: DeploymentHandle):
        self.transcriber = transcriber

    @app.post("/transcribe")  
    async def transcribe(self, request: Request) -> dict:  
        form = await request.form()
        audio_file = form["audio_file"]
        audio_data = await audio_file.read()
        
        result = await self.transcriber.remote(audio_data)
        return result

    @app.get("/health")
    async def health(self):
        return {"status": "healthy"}

app = WhisperAPI.bind(WhisperTranscriber.bind())