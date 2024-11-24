#!/bin/bash

# Output file for diagnostics
OUTPUT_FILE="aws_network_diagnostics.txt"
REGION="us-west-2"
INSTANCE_ID="i-0e44381d39d3eeb24"  # Replace with your instance ID
SUBNET_ID="subnet-c00ae9a6"        # Replace with your subnet ID
VPC_ID="vpc-ace332ca"             # Replace with your VPC ID
SECURITY_GROUP_ID="sg-030176ebd4455dcc5" # Replace with your security group ID

echo "AWS Network Diagnostics Script" > $OUTPUT_FILE
echo "Generated on: $(date)" >> $OUTPUT_FILE
echo "===================================" >> $OUTPUT_FILE

# Instance details
echo "1. Instance Details" >> $OUTPUT_FILE
aws ec2 describe-instances --instance-ids $INSTANCE_ID --region $REGION \
  --query "Reservations[].Instances[].[InstanceId,PublicIpAddress,PrivateIpAddress,State.Name]" \
  --output table >> $OUTPUT_FILE 2>&1

# Security Groups
echo -e "\n2. Security Group Details (ID: $SECURITY_GROUP_ID)" >> $OUTPUT_FILE
aws ec2 describe-security-groups --group-ids $SECURITY_GROUP_ID --region $REGION >> $OUTPUT_FILE 2>&1

# Network ACLs
echo -e "\n3. Network ACLs Associated with Subnet $SUBNET_ID" >> $OUTPUT_FILE
aws ec2 describe-network-acls --filters "Name=association.subnet-id,Values=$SUBNET_ID" --region $REGION >> $OUTPUT_FILE 2>&1

# Route Tables
echo -e "\n4. Route Table Associated with Subnet $SUBNET_ID" >> $OUTPUT_FILE
aws ec2 describe-route-tables --filters "Name=association.subnet-id,Values=$SUBNET_ID" --region $REGION >> $OUTPUT_FILE 2>&1

# Subnet details
echo -e "\n5. Subnet Details (ID: $SUBNET_ID)" >> $OUTPUT_FILE
aws ec2 describe-subnets --subnet-ids $SUBNET_ID --region $REGION >> $OUTPUT_FILE 2>&1

# VPC details
echo -e "\n6. VPC Details (ID: $VPC_ID)" >> $OUTPUT_FILE
aws ec2 describe-vpcs --vpc-ids $VPC_ID --region $REGION \
  --query "Vpcs[0].{DNSHostnames:EnableDnsHostnames,DNSResolution:EnableDnsSupport}" >> $OUTPUT_FILE 2>&1

# Elastic IP addresses
echo -e "\n7. Elastic IP Addresses" >> $OUTPUT_FILE
aws ec2 describe-addresses --region $REGION >> $OUTPUT_FILE 2>&1

# Internet Gateway
echo -e "\n8. Internet Gateways Associated with VPC $VPC_ID" >> $OUTPUT_FILE
aws ec2 describe-internet-gateways --filters "Name=attachment.vpc-id,Values=$VPC_ID" --region $REGION >> $OUTPUT_FILE 2>&1

# DNS Resolution Test
echo -e "\n9. DNS Resolution Test (from instance)" >> $OUTPUT_FILE
cat << EOF >> $OUTPUT_FILE
# Run the following commands manually from the EC2 instance:
# nslookup developer.download.nvidia.com
# ping developer.download.nvidia.com
EOF

# IP Tables Dump (Run Manually)
echo -e "\n10. Local Networking Configuration (to be run manually)" >> $OUTPUT_FILE
cat << EOF >> $OUTPUT_FILE
# Run the following commands manually from the EC2 instance:
# sudo iptables -L -v -n
# sudo systemctl status systemd-networkd
EOF

echo -e "\nDiagnostic information saved to $OUTPUT_FILE"
