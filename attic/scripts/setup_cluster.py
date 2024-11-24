"""
AWS Cluster setup script for Whisper Service.

This script handles the creation and configuration of an AWS Ray cluster.

Author: Marco Graziano (marco@graziano.com)
Copyright (c) 2024 Graziano Labs Corp. All rights reserved.
"""

import boto3
import click
import json
import yaml
import os
from pathlib import Path

@click.command()
@click.option('--config', default='config/cluster.json', help='Cluster configuration file')
@click.option('--key-name', required=True, help='AWS EC2 key pair name')
@click.option('--vpc-id', required=True, help='AWS VPC ID')
@click.option('--subnet-id', required=True, help='AWS Subnet ID')
def setup_cluster(config, key_name, vpc_id, subnet_id):
    """Setup Ray cluster on AWS"""
    
    # Load configuration
    with open(config, 'r') as f:
        config = json.load(f)
    
    cluster_config = config['deployment']['cluster']
    
    # Generate Ray cluster configuration
    ray_config = {
        "cluster_name": "whisper-serve-cluster",
        "min_workers": 0,
        "max_workers": sum(node["num_nodes"] for node in cluster_config["worker_nodes"]),
        "provider": {
            "type": "aws",
            "region": cluster_config["aws_region"],
            "availability_zone": cluster_config["availability_zone"],
            "cache_stopped_nodes": False,
            "key_pair": {
                "key_name": key_name
            }
        },
        "auth": {
            "ssh_user": "ubuntu"
        },
        "head_node": {
            "InstanceType": cluster_config["head_node"]["instance_type"],
            "ImageId": "ami-0c55b159cbfafe1f0",  # Ubuntu 20.04
            "SecurityGroupIds": ["sg-create-later"],
            "SubnetId": subnet_id,
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/sda1",
                    "Ebs": {
                        "VolumeSize": 100
                    }
                }
            ]
        },
        "worker_nodes": {}
    }
    
    # Add worker node configurations
    for worker in cluster_config["worker_nodes"]:
        ray_config["worker_nodes"][worker["name"]] = {
            "InstanceType": worker["instance_type"],
            "ImageId": "ami-0c55b159cbfafe1f0",
            "SubnetId": subnet_id,
            "SecurityGroupIds": ["sg-create-later"],
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/sda1",
                    "Ebs": {
                        "VolumeSize": 100
                    }
                }
            ]
        }
        
    # Save Ray cluster configuration
    with open('cluster.yaml', 'w') as f:
        yaml.dump(ray_config, f)
    
    click.echo("Generated cluster configuration. To deploy:")
    click.echo("\n1. Create security group:")
    click.echo("aws ec2 create-security-group --group-name ray-sg --description 'Ray security group' --vpc-id " + vpc_id)
    
    click.echo("\n2. Add inbound rules:")
    click.echo("aws ec2 authorize-security-group-ingress --group-id <sg-id> --protocol tcp --port 22 --cidr 0.0.0.0/0")
    click.echo("aws ec2 authorize-security-group-ingress --group-id <sg-id> --protocol tcp --port 6379 --cidr 0.0.0.0/0")
    click.echo("aws ec2 authorize-security-group-ingress --group-id <sg-id> --protocol tcp --port 8265 --cidr 0.0.0.0/0")
    click.echo("aws ec2 authorize-security-group-ingress --group-id <sg-id> --protocol tcp --port 10001 --cidr 0.0.0.0/0")
    
    click.echo("\n3. Update cluster.yaml with security group ID")
    
    click.echo("\n4. Start cluster:")
    click.echo("ray up cluster.yaml")
    
    click.echo("\n5. Set environment variable:")
    click.echo("export RAY_HEAD_ADDRESS=<head-node-ip>:10001")

if __name__ == '__main__':
    setup_cluster()