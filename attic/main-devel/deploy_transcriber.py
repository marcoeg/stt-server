import ray
from ray import serve
from whisper_serve.models import WhisperTranscriber, ModelLoader
import os

# Start Ray Serve
head_ip = os.getenv('RAY_HEAD_ADDRESS', '').split(':')[0]
    
# Initialize Ray with GCS address
ray.init(
        address=f"ray://{head_ip}:10001"
        )

serve.start(detached=True)

# Initialize ModelLoader
model_loader = ModelLoader.remote()

# Deploy WhisperTranscriber
transcriber = WhisperTranscriber.options(
    name="WhisperTranscriber",
    num_replicas=1,
    ray_actor_options={
        "num_cpus": 1,
        "num_gpus": 0,  # Adjust based on your setup
    }
).bind(
    model_size="base",
    model_loader=model_loader,
)

serve.run(transcriber, route_prefix="/transcriber")
