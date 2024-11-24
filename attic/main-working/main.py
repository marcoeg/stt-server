from starlette.requests import Request
from ray import serve
from transformers import pipeline
import tempfile
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WhisperService")


@serve.deployment
class WhisperTranscriber:
    def __init__(self):
        self.transcriber = pipeline(
            "automatic-speech-recognition",
            model="openai/whisper-base",
            device="cuda"
        )

    async def __call__(self, http_request: Request) -> dict:
        form = await http_request.form()
        audio_file = form["audio_file"]
        audio_data = await audio_file.read()

        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            tmp_file.write(audio_data)
            tmp_file_path = tmp_file.name

        try:
            result = self.transcriber(tmp_file_path)
            return {"success": True, "text": result["text"]}
        finally:
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)


# Bind WhisperTranscriber as the main app
app = WhisperTranscriber.bind()
