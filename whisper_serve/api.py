from ray import serve
from ray.serve.handle import DeploymentHandle
from starlette.requests import Request
import json

@serve.deployment
class RootApp:
    def __init__(self, whisper_model: DeploymentHandle, llama_model: DeploymentHandle):
        self.whisper_model = whisper_model
        self.llama_model = llama_model

    async def __call__(self, request: Request):
        path = request.url.path
        if path == "/transcribe":
            form = await request.form()
            audio_file = form["audio_file"]
            audio_data = await audio_file.read()
            result = await self.whisper_model.transcribe.remote(audio_data)
            return result

        elif path == "/generate":
            body = await request.body()
            data = json.loads(body)
            prompt = data.get("prompt", "")
            result = await self.llama_model.generate.remote(prompt)
            return result

        else:
            return {"error": "Invalid endpoint"}
