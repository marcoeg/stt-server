import ray
import os

# Connect to the Ray cluster
ray.init(
    address=f"ray://{os.getenv('RAY_HEAD_ADDRESS').split(':')[0]}:10001",
    )
   # address="ray://52.34.247.77:10001"

@ray.remote
def say_hello():
    return "Hello, Ray Cluster!"

if __name__ == "__main__":
    # Run the remote function
    result = ray.get(say_hello.remote())
    print(result)  # Should print: "Hello, Ray Cluster!"
    
    tasks = [say_hello.remote() for _ in range(10)]
    results = ray.get(tasks)
    print(results)  # Should print "Hello, Ray Cluster!" 10 times

    # Shutdown Ray
    ray.shutdown()
