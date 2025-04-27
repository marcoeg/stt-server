import modal
from fastapi import UploadFile, Form, File
from typing import Optional

# Define the Modal app
app = modal.App("whisper-ray-distributed")

# Modal image setup
image = (
    modal.Image.debian_slim()
    .pip_install([
        "ray[default]>=2.9.0",
        "torch~=2.2.0",
        "torchaudio",
        "openai-whisper==20231117",
        "soundfile",
        "numpy",
        "fastapi",
        "python-multipart",
    ])
    .apt_install(["ffmpeg", "libsndfile1"])
)

# Ray head node setup function
@app.function(image=image, gpu="a10g", container_idle_timeout=600)
def ray_head():
    """Initialize the Ray head node and return its address."""
    import ray
    import socket

    # Get the public-facing IP of the container
    container_ip = socket.gethostbyname(socket.gethostname())

    # Start Ray in head mode, binding to the container's IP
    ray.init(
        address=None,  # Start as the head node
        _node_ip_address=container_ip,
        log_to_driver=True
    )

    # Construct the cluster address
    head_address = f"{container_ip}:6379"
    print(f"Ray head node initialized at {head_address}")
    return head_address


# Ray worker node setup function
@app.function(image=image, gpu="a10g", container_idle_timeout=600)
def ray_worker(head_address: str):
    """Initialize a Ray worker node."""
    import ray

    # Connect to the existing Ray cluster
    ray.init(address=head_address)
    print(f"Ray worker node initialized and connected to {head_address}")

# Persistent cluster initialization
@app.function(image=image, gpu="a10g", container_idle_timeout=600)
def initialize_cluster():
    """
    Initialize the Ray cluster with a head node and worker nodes.
    Keeps the cluster alive by blocking.
    """
    import os
    import time

    # Get the number of workers from environment variables
    num_workers = int(os.environ.get("NUM_WORKERS", 4))  # Default to 4 workers

    # Start the Ray head node and retrieve its address
    head_address = ray_head.spawn().get()  # Retrieve the container's IP address
    print(f"Ray head node started at {head_address}")

    # Start the worker nodes
    for i in range(num_workers):
        ray_worker.spawn(head_address=head_address)
        print(f"Ray worker node {i+1} started and connected to {head_address}")

    print(f"Ray cluster initialized with {num_workers} workers. Keeping alive.")
    # Block to keep the cluster alive
    while True:
        time.sleep(3600)



# Whisper model actor definition
def create_whisper_actor():
    import ray

    @ray.remote(num_gpus=1)
    class WhisperModelActor:
        def __init__(self, model_size="base"):
            import whisper
            import torch
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model = whisper.load_model(model_size).to(self.device)
            print(f"Model {model_size} loaded on {self.device}")

        def transcribe(self, audio_data, language=None):
            options = {"language": language} if language else {}
            result = self.model.transcribe(audio_data, **options)
            return result["text"]

    return WhisperModelActor

# Web endpoint for transcription
@app.function(image=image, gpu="a10g", container_idle_timeout=600)
@modal.web_endpoint(method="POST")
async def transcribe(
    audio_file: UploadFile = File(...),
    model_size: str = Form("base"),
    language: Optional[str] = Form(None)
):
    """Web endpoint for transcription."""
    import numpy as np
    import soundfile as sf
    import io
    import ray

    try:
        # Read and process audio
        content = await audio_file.read()
        with io.BytesIO(content) as audio_bytes:
            audio_data, _ = sf.read(audio_bytes)
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
            audio_data = audio_data.astype(np.float32)

        # Connect to the cluster and get actor reference
        ray.init(address="auto")
        WhisperModelActor = create_whisper_actor()
        actor = WhisperModelActor.remote(model_size)

        # Transcribe using the actor
        future = actor.transcribe.remote(audio_data, language=language)
        result = ray.get(future)
        return {"text": result}

    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == "__main__":
    modal.serve(app)
