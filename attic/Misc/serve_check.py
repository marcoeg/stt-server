import ray
from ray import serve
import os
import signal
import time
import requests
from whisper_serve.models import ModelLoader, WhisperTranscriber
from whisper_serve.api import WhisperAPI
from whisper_serve.config import config
from whisper_serve.logger import logger

# Global flag for graceful shutdown
running = True


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global running
    logger.info("Received shutdown signal. Cleaning up...")
    running = False

def check_deployment_health(name, timeout=30):
    """Check if a deployment becomes healthy within the timeout period."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            # Retrieve the current status of Ray Serve
            app_status = serve.status()
            logger.info(f"Full Serve status: {app_status}")

            # Check if the application contains the deployment
            if "whisper_service" in app_status.applications:
                app_overview = app_status.applications["whisper_service"]
                deployments_status = app_overview.deployments

                if name in deployments_status:
                    deployment_status = deployments_status[name]
                    logger.info(f"Deployment {name} status: {deployment_status.status}")

                    # Check if the deployment is healthy
                    if deployment_status.status == "HEALTHY":
                        return True
                    elif deployment_status.message:
                        logger.error(f"Deployment {name} message: {deployment_status.message}")
                else:
                    logger.warning(f"Deployment {name} not found in 'whisper_service' deployments.")
            else:
                logger.warning("Application 'whisper_service' not found.")
            time.sleep(2)
        except Exception as e:
            logger.warning(f"Health check error: {str(e)}")
            time.sleep(2)  # Prevent rapid looping in case of continuous errors
    return False

def create_deployment():
    """Create and deploy the Whisper service."""
    retries = 3
    initial_replicas = 2

    # Initialize ModelLoader
    logger.info("Initializing ModelLoader...")
    model_loader = ModelLoader.remote()
    for attempt in range(1, retries + 1):
        try:
            ray.get(model_loader.load_model.remote(config["model"]["size"]))
            logger.info(f"Model '{config['model']['size']}' loaded successfully.")
            break
        except Exception as e:
            logger.error(f"Attempt {attempt}/{retries} to load model failed: {e}")
            if attempt == retries:
                logger.error("Exhausted all retries for model loading. Aborting deployment.")
                raise

    # Deploy WhisperTranscriber
    try:
        logger.info("Creating WhisperTranscriber deployment...")
        transcriber = WhisperTranscriber.options(
            name="WhisperTranscriber",
            num_replicas=initial_replicas,
            ray_actor_options={
                "num_cpus": config["deployment"]["cpu_per_replica"],
                "num_gpus": config["deployment"]["gpu_per_replica"],
                "runtime_env": {
                    "env_vars": {
                        "RAY_CLIENT_MODE": "0",
                        "CUDA_VISIBLE_DEVICES": "0",  # Explicitly set GPU device
                    }
                },
            },
        ).bind(
            model_size=config["model"]["size"], model_loader=model_loader
        )
        logger.info("WhisperTranscriber deployment created successfully.")
    except Exception as e:
        logger.error(f"Failed to create WhisperTranscriber deployment: {e}")
        raise

    # Bind and deploy WhisperAPI
    try:
        logger.info("Binding and deploying WhisperAPI...")
        api = WhisperAPI.bind(transcriber)
        serve.run(api, route_prefix="/", name="whisper_service", blocking=False)
        logger.info("Service deployed successfully. Checking health...")

        # Health check
        if not check_deployment_health("WhisperTranscriber"):
            logger.error("WhisperTranscriber deployment is unhealthy.")
            return
        logger.info(f"Service is running at http://{config['server']['host']}:{config['server']['port']}")
    except Exception as e:
        logger.error(f"Failed to deploy WhisperAPI: {e}")
        raise


def create_deployment0():
    """Create and deploy the Whisper service."""
    retries = 3
    initial_replicas = 2

    # Initialize ModelLoader
    logger.info("Initializing ModelLoader...")
    model_loader = ModelLoader.remote()
    for attempt in range(1, retries + 1):
        try:
            ray.get(model_loader.load_model.remote(config["model"]["size"]))
            logger.info(f"Model '{config['model']['size']}' loaded successfully.")
            break
        except Exception as e:
            logger.error(f"Attempt {attempt}/{retries} to load model failed: {e}")
            if attempt == retries:
                logger.error("Exhausted all retries for model loading. Aborting deployment.")
                raise

    # Log available GPUs for debugging
    gpus = [
        node for node in ray.nodes() if any("GPU" in resource for resource in node["Resources"])
    ]
    logger.info(f"Available GPUs: {gpus}")

    # Deploy WhisperTranscriber
    try:
        logger.info("Creating WhisperTranscriber deployment...")
        deployment_options = {
            "name": "WhisperTranscriber",
            "num_replicas": initial_replicas,
            "ray_actor_options": {
                "num_cpus": config["deployment"]["cpu_per_replica"],
                "num_gpus": config["deployment"]["gpu_per_replica"],
                "runtime_env": {
                    "env_vars": {
                        "RAY_CLIENT_MODE": "0",
                        "CUDA_VISIBLE_DEVICES": "0",  # Explicitly set GPU device
                    }
                },
            },
        }
        transcriber = WhisperTranscriber.options(**deployment_options).bind(
            model_size=config["model"]["size"], model_loader=model_loader
        )
        logger.info("WhisperTranscriber deployment created successfully.")
    except Exception as e:
        logger.error(f"Failed to create WhisperTranscriber deployment: {e}")
        raise

    # Create and deploy WhisperAPI
    try:
        logger.info("Binding and deploying WhisperAPI...")
        api = WhisperAPI.bind(transcriber)
        serve.run(api, route_prefix="/", name="whisper_service", blocking=False)
        logger.info("Service deployed successfully. Checking health...")

        # Health check
        if not check_deployment_health("WhisperTranscriber"):
            logger.error("WhisperTranscriber deployment is unhealthy.")
            return
        logger.info(f"Service is running at http://{config['server']['host']}:{config['server']['port']}")
    except Exception as e:
        logger.error(f"Failed to deploy WhisperAPI: {e}")
        raise


def heartbeat_monitor():
    """Monitor the service health."""
    while running:
        try:
            # Use serve.status() to list deployments
            app_status = serve.status()

            if "whisper_service" in app_status.applications:
                deployments = app_status.applications["whisper_service"].deployments

                for name, status in deployments.items():
                    logger.info(f"Deployment {name} status: {status.status}")
            else:
                logger.warning("Application 'whisper_service' not found.")
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
