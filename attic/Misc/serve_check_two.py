import ray
from ray import serve
import requests
import os

# Initialize Ray and Serve
ray.init(
    address=f"ray://{os.getenv('RAY_HEAD_ADDRESS')}:10001",
    namespace="serve_test",
)
serve.start(detached=True)

# Minimal GPU Test Deployment
@serve.deployment(ray_actor_options={"num_gpus": 1})
class GPUTestV2:
    def __init__(self):
        import torch
        try:
            # GPU status checks
            self.has_cuda = torch.cuda.is_available()
            self.device_count = torch.cuda.device_count()
            if self.has_cuda:
                self.device_name = torch.cuda.get_device_name(0)
            else:
                self.device_name = "No GPU available"

            # Placeholder for additional model checks
            self.model_loaded = False
            print("Initialization complete: GPU test successful")
        except Exception as e:
            self.has_cuda = False
            self.device_count = 0
            self.device_name = "Initialization failed"
            self.error_message = str(e)
            print(f"Error during GPU test initialization: {e}")

    def __call__(self, request):
        return {
            "has_cuda": self.has_cuda,
            "device_count": self.device_count,
            "device_name": self.device_name,
            "model_loaded": self.model_loaded,
            "error_message": getattr(self, "error_message", None)
        }

# Deploy the test service
try:
    serve.run(GPUTestV2.bind(), route_prefix="/gpu_v2")
    print("Deployed GPUTestV2 successfully.")
except Exception as e:
    print(f"Failed to deploy GPUTestV2: {e}")

# Query the GPU test service
endpoint = f"http://{os.getenv('RAY_HEAD_ADDRESS')}:8000/gpu_v2"
try:
    response = requests.get(endpoint)
    if response.status_code == 200:
        print("GPU Test Results:")
        print(response.json())
    else:
        print(f"Failed to query GPU test. Status Code: {response.status_code}")
        print(f"Response: {response.text}")
except Exception as e:
    print(f"Error querying GPU test: {e}")

# Clean up
print("Shutting down Ray...")
ray.shutdown()
