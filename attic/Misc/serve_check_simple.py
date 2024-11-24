import ray
from ray import serve
import os

ray.init(address=f"ray://{os.getenv('RAY_HEAD_ADDRESS')}:10001", namespace="serve_test")
serve.start(detached=True)

@serve.deployment
def hello(request):
    return {"message": "Hello, Ray Serve!"}

serve.run(hello.bind(), route_prefix="/hello")
print("Service deployed. Test it with:")
print(f"http://{os.getenv('RAY_HEAD_ADDRESS')}:8000/hello")
