import ray
from ray import serve
import signal
import time
import argparse
from whisper_serve.config import config
from whisper_serve.models import ModelLoader, WhisperTranscriber
from whisper_serve.api import WhisperAPI
from whisper_serve.logger import logger
import os

# Global flag for graceful shutdown
running = True

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global running
    logger.info("Received shutdown signal. Cleaning up...")
    running = False
    
def check_deployment_health(name, timeout=30):
    """Check if a deployment becomes healthy and get detailed error if not."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            status = serve.status()
            if name in status.deployments:
                deployment = status.deployments[name]
                logger.info(f"Deployment {name} details: {deployment}")
                if deployment.message:  # This will show the actual error
                    logger.error(f"Deployment message: {deployment.message}")
                return deployment.status == "HEALTHY"
            time.sleep(2)
        except Exception as e:
            logger.error(f"Health check error: {str(e)}", exc_info=True)
    return False

def create_deployment():
    """Create and deploy the Whisper service with retry and monitoring logic."""
    retries = 3
    initial_replicas = 2

    if ray.is_initialized():
        ray.shutdown()

    head_ip = os.getenv('RAY_HEAD_ADDRESS', '').split(':')[0]
    
    # Initialize Ray with GCS address
    ray.init(
        address=f"ray://{head_ip}:10001",
        runtime_env={
            "env_vars": {
                "RAY_TIMEOUT_MS": "300000",
                "RAY_CLIENT_MODE": "0",
                "RAY_CLIENT_CONNECTION_TIMEOUT_MS": "60000"
            },
            "working_dir": ".",
            "excludes": ["**/venv-3.9/**"]  # Exclude venv files
        },
        _system_config={
            "ray_client_connection_timeout_ms": 60000,
            "ray_client_num_connect_attempts": 5
        },
        ignore_reinit_error=True
    )

    # Start Ray Serve
    serve.start(
        http_options={
            "host": config["server"]["host"],
            "port": config["server"]["port"],
            "location": "EveryNode"
        },
        dedicated_cpu=config["server"].get("dedicated_cpu", False),
        detached=True,
        proxy_location="EveryNode"
    )

    # Add debugging info
    logger.info(f"Ray Dashboard URL: http://{config['server']['host']}:8265")
    logger.info(f"Ray resources: {ray.cluster_resources()}")
    logger.info(f"Ray nodes: {ray.nodes()}")

    # Create model loader with more detailed logging
    model_loader = ModelLoader.remote()
    for attempt in range(retries):
        try:
            ray.get(model_loader.load_model.remote(config["model"]["size"]))
            logger.info("Model loaded successfully")
            break
        except Exception as e:
            logger.error(f"Failed to load model (Attempt {attempt + 1}/{retries}): {str(e)}")
            if attempt == retries - 1:
                raise

    logger.info("Available GPUs: %s", [node for node in ray.nodes() if any('GPU' in resource for resource in node['Resources'])])

    # Deploy Transcriber with detailed error logging
    try:
        deployment_options = {
            "name": "WhisperTranscriber",
            "num_replicas": initial_replicas,
            "ray_actor_options": {
                "num_cpus": config["deployment"]["cpu_per_replica"],
                "num_gpus": config["deployment"]["gpu_per_replica"],
                "runtime_env": {
                    "env_vars": {
                        "RAY_CLIENT_MODE": "0",
                        "CUDA_VISIBLE_DEVICES": "0"  # Explicitly set GPU device
                    }
                }
            }
        }
        logger.info(f"Creating transcriber with options: {deployment_options}")
        
        transcriber = WhisperTranscriber.options(**deployment_options).bind(
            model_size=config["model"]["size"],
            model_loader=model_loader
        )
        logger.info("Transcriber deployment created successfully")
    except Exception as e:
        logger.error(f"Failed to create transcriber deployment: {str(e)}")
        raise

    # Create the API
    api = WhisperAPI.bind(transcriber)

    # Deploy the service with health checks
    for attempt in range(retries):
        try:
            serve.run(
                api,
                route_prefix="/",
                name="whisper_service",
                blocking=False
            )
            logger.info("Initial deployment completed, checking health...")
            
            # Wait for deployment health
            if check_deployment_health("WhisperTranscriber"):
                logger.info(f"Service deployed successfully with {initial_replicas} replicas")
                break
            else:
                # Get detailed status
                try:
                    status = serve.status()
                    if "WhisperTranscriber" in status.deployments:
                        deployment = status.deployments["WhisperTranscriber"]
                        logger.error(f"Deployment failed: {deployment.message}")
                except Exception as status_e:
                    logger.error(f"Failed to get detailed status: {str(status_e)}")
                raise Exception("Deployment health check failed")
                
        except Exception as e:
            logger.error(f"Failed to deploy service (Attempt {attempt + 1}/{retries}): {str(e)}")
            if attempt == retries - 1:
                raise

    logger.info(f"Service running at http://{config['server']['host']}:{config['server']['port']}")

    # Scale replicas after initial stability
    serve.get_deployment("WhisperTranscriber").options(num_replicas=config["deployment"]["num_replicas"]).deploy()

def heartbeat_monitor():
    """Monitor the service health."""
    while running:
        try:
            deployments = serve.list_deployments()
            if not deployments:
                logger.warning("No deployments found. Retrying...")
            for name, deployment in deployments.items():
                logger.info(f"Deployment {name}: {deployment.status}")
        except Exception as e:
            logger.error(f"Heartbeat check failed: {str(e)}")
        time.sleep(10)  # Check every 10 seconds

def main():
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        create_deployment()

        # Start the heartbeat monitor
        while running:
            heartbeat_monitor()
            
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        raise
    finally:
        logger.info("Cleaning up Ray resources...")
        ray.shutdown()
        logger.info("Shutdown complete")

if __name__ == "__main__":
    main()
