import ray
ray.init(address="ray://35.87.82.33:10001")
print(ray.cluster_resources())
