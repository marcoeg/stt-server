@serve.deployment
class WhisperTranscriber:
    def __init__(self, model_size: str = "base", device: str = "cpu"):
        self.transcriber = None
        try:
            if device == "cuda":
                import torch
                cuda_available = torch.cuda.is_available()
                device_id = 0 if cuda_available else -1
            else:
                device_id = -1
            
            self.transcriber = pipeline(
                "automatic-speech-recognition",
                model=f"openai/whisper-{model_size}",
                device=device_id,
            )
        except Exception as e:
            logger.error(f"Init error: {str(e)}")

    def _safe_transcribe(self, file_path):
        """Wrapper to ensure no exceptions escape"""
        try:
            return {"success": True, "result": self.transcriber(file_path)}
        except:
            return {"success": False, "error": "Model inference failed"}

    async def __call__(self, audio_data: bytes) -> dict:
        if self.transcriber is None:
            return {"success": False, "error": "Model not initialized"}

        import tempfile
        import os
        tmp_file_path = None

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                tmp_file.write(audio_data)
                tmp_file_path = tmp_file.name

            transcribe_result = self._safe_transcribe(tmp_file_path)
            if not transcribe_result["success"]:
                return transcribe_result

            return {
                "success": True, 
                "text": transcribe_result["result"]["text"]
            }

        except:
            return {"success": False, "error": "Processing failed"}
        
        finally:
            if tmp_file_path and os.path.exists(tmp_file_path):
                try:
                    os.unlink(tmp_file_path)
                except:
                    pass


@serve.deployment
@serve.ingress(app)
class WhisperAPI:
    def __init__(self, transcriber: WhisperTranscriber):
        self.transcriber = transcriber

    @app.post("/transcribe")
    async def transcribe(self, audio_file: UploadFile = File(...)):
        if not audio_file:
            return {"error": "No file provided"}

        try:
            audio_data = await audio_file.read()
        except:
            return {"error": "Failed to read file"}

        if not audio_data:
            return {"error": "Empty file"}

        try:
            result = await self.transcriber.remote(audio_data)
        except:
            return {"error": "Transcription service unavailable"}

        if not result.get("success"):
            return {"error": result.get("error", "Unknown error")}

        return {"transcription": result["text"]}

    @app.get("/health")
    async def health(self):
        return {"status": "healthy"}

# Define the deployments
transcriber = WhisperTranscriber.options(
    name="WhisperTranscriber",
    ray_actor_options={"num_cpus": 2, "num_gpus": 1}
).bind(model_size="base", device="cuda")

app = WhisperAPI.options(
    name="WhisperAPI",
    ray_actor_options={"num_cpus": 1}
).bind(transcriber)