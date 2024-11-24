#!/bin/bash

# Output file
OUTPUT_FILE="ray_cluster_aws_config_dump_$(date +%Y%m%d).txt"

echo "Ray Cluster AWS Configuration Dump - $(date)" > $OUTPUT_FILE
echo "=========================================" >> $OUTPUT_FILE

# IAM Role and Policies
echo "\n=== IAM Configuration ===" >> $OUTPUT_FILE
echo "\n--- Instance Profile ---" >> $OUTPUT_FILE
aws iam get-instance-profile --instance-profile-name ray-autoscaler-v1 >> $OUTPUT_FILE

echo "\n--- Attached Role Policies ---" >> $OUTPUT_FILE
aws iam list-attached-role-policies --role-name ray-autoscaler-v1 >> $OUTPUT_FILE

echo "\n--- Custom Policy (ray-autoscaler-policy) ---" >> $OUTPUT_FILE
aws iam get-policy-version \
    --policy-arn arn:aws:iam::892335585962:policy/ray-autoscaler-policy \
    --version-id v1 >> $OUTPUT_FILE

echo "\n--- Inline Role Policy ---" >> $OUTPUT_FILE
aws iam get-role-policy \
    --role-name ray-autoscaler-v1 \
    --policy-name permissions-ray-cluster >> $OUTPUT_FILE

# VPC Configuration
echo "\n=== VPC Configuration ===" >> $OUTPUT_FILE
echo "\n--- Subnet Details ---" >> $OUTPUT_FILE
aws ec2 describe-subnets --subnet-ids subnet-c00ae9a6 >> $OUTPUT_FILE

echo "\n--- VPC Details ---" >> $OUTPUT_FILE
aws ec2 describe-vpcs --vpc-ids vpc-ace332ca >> $OUTPUT_FILE

# Internet Gateway
echo "\n=== Internet Gateway ===" >> $OUTPUT_FILE
aws ec2 describe-internet-gateways \
    --filters "Name=attachment.vpc-id,Values=vpc-ace332ca" >> $OUTPUT_FILE

# Route Tables
echo "\n=== Route Tables ===" >> $OUTPUT_FILE
aws ec2 describe-route-tables \
    --filters "Name=association.subnet-id,Values=subnet-c00ae9a6" >> $OUTPUT_FILE

# Security Groups
echo "\n=== Security Groups ===" >> $OUTPUT_FILE
aws ec2 describe-security-groups --group-ids sg-030176ebd4455dcc5 >> $OUTPUT_FILE

# AMI Details
echo "\n=== AMI Details ===" >> $OUTPUT_FILE
aws ec2 describe-images --image-ids ami-05c1fa8c9881244b6 >> $OUTPUT_FILE

# Add summary of key configuration items
echo "\n=== Quick Reference ===" >> $OUTPUT_FILE
echo "VPC ID: vpc-ace332ca" >> $OUTPUT_FILE
echo "Subnet ID: subnet-c00ae9a6" >> $OUTPUT_FILE
echo "Security Group ID: sg-030176ebd4455dcc5" >> $OUTPUT_FILE
echo "AMI ID: ami-05c1fa8c9881244b6" >> $OUTPUT_FILE
echo "Instance Profile: ray-autoscaler-v1" >> $OUTPUT_FILE
echo "Region: us-west-2" >> $OUTPUT_FILE
echo "Availability Zone: us-west-2a" >> $OUTPUT_FILE

echo "\n=== Network Configuration Requirements ===" >> $OUTPUT_FILE
echo "Required open ports:" >> $OUTPUT_FILE
echo "- 22 (SSH)" >> $OUTPUT_FILE
echo "- 6379 (Ray GCS)" >> $OUTPUT_FILE
echo "- 8265 (Ray Dashboard)" >> $OUTPUT_FILE
echo "- 10001 (Ray Client)" >> $OUTPUT_FILE
echo "- 10000-19999 (Ray Worker Ports)" >> $OUTPUT_FILE
echo "- All internal traffic between cluster nodes" >> $OUTPUT_FILE

echo "\nConfiguration dumped to $OUTPUT_FILE"