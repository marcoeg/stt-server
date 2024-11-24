"""
AWS EFS setup script for Whisper Service cluster.

This script creates and configures EFS for shared model storage across the cluster.

Author: Marco Graziano (marco@graziano.com)
Copyright (c) 2024 Graziano Labs Corp. All rights reserved.
"""

import boto3
import click
import json
from typing import Dict, Any
import time

def create_efs(cluster_config: Dict[str, Any], vpc_id: str, subnet_id: str) -> str:
    """Create EFS filesystem and mount targets"""
    efs = boto3.client('efs')
    ec2 = boto3.client('ec2')
    
    # Create security group for EFS
    sg_response = ec2.create_security_group(
        GroupName='whisper-efs-sg',
        Description='Security group for Whisper Service EFS',
        VpcId=vpc_id
    )
    sg_id = sg_response['GroupId']
    
    # Allow NFS traffic from the VPC
    ec2.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {
                'FromPort': 2049,
                'ToPort': 2049,
                'IpProtocol': 'tcp',
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }
        ]
    )
    
    # Create EFS filesystem
    response = efs.create_file_system(
        PerformanceMode='generalPurpose',
        ThroughputMode='bursting',
        Encrypted=True,
        Tags=[
            {
                'Key': 'Name',
                'Value': 'whisper-service-efs'
            }
        ]
    )
    fs_id = response['FileSystemId']
    
    # Wait for EFS to be available
    while True:
        response = efs.describe_file_systems(FileSystemId=fs_id)
        if response['FileSystems'][0]['LifeCycleState'] == 'available':
            break
        time.sleep(5)
    
    # Create mount target
    efs.create_mount_target(
        FileSystemId=fs_id,
        SubnetId=subnet_id,
        SecurityGroups=[sg_id]
    )
    
    return fs_id

@click.command()
@click.option('--config', default='config/cluster.json', help='Cluster configuration file')
@click.option('--vpc-id', required=True, help='VPC ID for EFS')
@click.option('--subnet-id', required=True, help='Subnet ID for EFS mount target')
def setup_efs(config: str, vpc_id: str, subnet_id: str) -> None:
    """Setup EFS for the Whisper Service cluster"""
    
    # Load cluster configuration
    with open(config, 'r') as f:
        cluster_config = json.load(f)
    
    click.echo("Creating EFS filesystem...")
    fs_id = create_efs(cluster_config, vpc_id, subnet_id)
    
    click.echo("\nEFS setup complete!")
    click.echo(f"Filesystem ID: {fs_id}")
    
    # Generate mount commands
    region = cluster_config['deployment']['cluster']['aws_region']
    mount_commands = f"""
    # Run these commands on each cluster node:
    
    # 1. Install EFS utilities
    sudo apt-get update
    sudo apt-get -y install amazon-efs-utils
    
    # 2. Create mount point
    sudo mkdir -p /shared/models
    sudo mkdir -p /shared/logs
    
    # 3. Add to /etc/fstab
    echo "{fs_id}.efs.{region}.amazonaws.com:/ /shared efs _netdev,tls,iam 0 0" | sudo tee -a /etc/fstab
    
    # 4. Mount EFS
    sudo mount -a
    
    # 5. Set permissions
    sudo chown -R ubuntu:ubuntu /shared
    """
    
    click.echo("\nMount Instructions:")
    click.echo(mount_commands)
    
    # Update cluster config with EFS info
    cluster_config['deployment']['storage'] = {
        'type': 'efs',
        'fs_id': fs_id,
        'mount_point': '/shared',
        'region': region
    }
    
    # Save updated config
    with open(config, 'w') as f:
        json.dump(cluster_config, f, indent=4)
    
    click.echo("\nConfiguration updated with EFS details.")
    click.echo("\nNote: Add these Ray cluster initialization commands to cluster.yaml:")
    click.echo("""
    setup_commands:
        - sudo apt-get update
        - sudo apt-get -y install amazon-efs-utils
        - sudo mkdir -p /shared/models
        - sudo mkdir -p /shared/logs
        - echo "${fs_id}.efs.{region}.amazonaws.com:/ /shared efs _netdev,tls,iam 0 0" | sudo tee -a /etc/fstab
        - sudo mount -a
        - sudo chown -R ubuntu:ubuntu /shared
    """.format(fs_id=fs_id, region=region))

if __name__ == '__main__':
    setup_efs()