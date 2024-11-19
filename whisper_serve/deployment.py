"""
Deployment factory and configuration management for Whisper Service.

This module handles deployment configuration and initialization for both
local and cluster deployments.

Author: Marco Graziano (marco@graziano.com)
Copyright (c) 2024 Graziano Labs Corp. All rights reserved.
"""

import os
import json
from typing import Dict, Any, Optional
import ray
from .logger import logger
from .config import Config

class DeploymentManager:
    def __init__(self, config_path: str):
        self.config = Config(config_path)
        self.deployment_mode = self.config["deployment"]["mode"]
        self.cluster_initialized = False

    def init_ray(self) -> None:
        """Initialize Ray based on deployment mode"""
        if ray.is_initialized():
            ray.shutdown()

        if self.deployment_mode == "local":
            self._init_local()
        else:
            self._init_cluster()

    def _init_local(self) -> None:
        """Initialize Ray for local deployment"""
        ray.init(
            num_cpus=self.config["server"]["num_cpus"],
            runtime_env={
                "env_vars": {
                    "PYTORCH_ENABLE_MPS_FALLBACK": "1"
                }
            }
        )
        logger.info("Initialized Ray for local deployment")

    def _init_cluster(self) -> None:
        """Initialize Ray for cluster deployment"""
        if not self.cluster_initialized:
            cluster_config = self.config["deployment"]["cluster"]
            address = os.getenv("RAY_HEAD_ADDRESS")
            if not address:
                raise ValueError("RAY_HEAD_ADDRESS environment variable not set")

            ray.init(
                address=f"ray://{address}",
                runtime_env={
                    "working_dir": ".",
                    "env_vars": {
                        "PYTORCH_ENABLE_MPS_FALLBACK": "1",
                        "AWS_DEFAULT_REGION": cluster_config["aws_region"]
                    }
                }
            )
            self.cluster_initialized = True
            logger.info(f"Initialized Ray for cluster deployment at {address}")

    def get_deployment_config(self) -> Dict[str, Any]:
        """Get deployment-specific configuration"""
        base_config = {
            "num_replicas": self.config["deployment"]["num_replicas"],
            "cpu_per_replica": self.config["deployment"]["cpu_per_replica"],
            "gpu_per_replica": self.config["deployment"]["gpu_per_replica"],
            "max_concurrent_queries": self.config["deployment"]["max_concurrent_queries"]
        }

        if self.deployment_mode == "cluster":
            # Add cluster-specific configurations
            base_config.update({
                "ray_actor_options": {
                    "runtime_env": {
                        "working_dir": ".",
                        "pip": ["openai-whisper", "soundfile"]
                    }
                }
            })

        return base_config

    def check_health(self) -> bool:
        """Check deployment health"""
        try:
            nodes = ray.nodes()
            if not nodes:
                return False
            
            # Check if required number of nodes are available
            if self.deployment_mode == "cluster":
                required_nodes = (
                    1 +  # Head node
                    sum(node["num_nodes"] for node in 
                        self.config["deployment"]["cluster"]["worker_nodes"])
                )
                if len(nodes) < required_nodes:
                    logger.warning(f"Expected {required_nodes} nodes, found {len(nodes)}")
                    return False

            return all(node["alive"] for node in nodes)
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False

    def cleanup(self) -> None:
        """Cleanup resources"""
        if ray.is_initialized():
            ray.shutdown()
            logger.info("Ray resources cleaned up")
            