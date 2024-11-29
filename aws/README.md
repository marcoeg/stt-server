# AWS Ray Cluster Infrastructure Summary

Author: Marco Graziano (marco@graziano.com)  
Copyright (c) 2024 Graziano Labs Corp. All rights reserved.

## Overview
This infrastructure setup is designed for a Ray cluster deployment in AWS, with the following key components:

- VPC with public subnet
- Security groups for cluster communication
- IAM roles and policies for Ray autoscaling
- EFS integration for shared storage
- Deep Learning AMI base configuration

## Current Infrastructure Details

### Network Configuration
- VPC: vpc-ace332ca (172.30.0.0/16)
- Subnet: subnet-c00ae9a6 (172.30.0.0/24) in us-west-2a
- Internet Gateway: igw-fc981b9b
- Route Table: Configured for internet access via IGW

### Security
- Security Group: sg-030176ebd4455dcc5 (ray-sg)
- Open Ports:
  - 22 (SSH)
  - 6379 (Ray GCS)
  - 8265 (Ray Dashboard)
  - 8000 (Custom)
  - 10001 (Ray Client)
  - 10000-19999 (Ray Worker Ports)
  - ICMP allowed
  - All internal traffic between cluster nodes

### IAM Configuration
- Instance Profile: ray-autoscaler-v1
- Attached Policies:
  - ray-autoscaler-policy (Custom)
  - EFSAccessPolicy (Custom)
  - AmazonEC2FullAccess
  - AmazonS3FullAccess

### Compute
- AMI: ami-05c1fa8c9881244b6 (Deep Learning Base AMI with NVIDIA driver)
- Instance Types:
  - Development: t3.xlarge
  - Staging/Production: c5.2xlarge

## CloudFormation Template Modifications

To incorporate the EFS configurations and security group rules from the addendum, here are the necessary modifications to the CloudFormation template:

1. Add EFS Security Group to the Resources section:

```yaml
  EFSSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Security group for EFS mount targets
      VpcId: !Ref RayVPC
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 2049
          ToPort: 2049
          SourceSecurityGroupId: !Ref RaySecurityGroup
      Tags:
        - Key: Name
          Value: !Sub ${ProjectName}-efs-sg
        - Key: Environment
          Value: !Ref Environment
```

2. Add EFS Policy to the IAM Role:

```yaml
      Policies:
        # Add this to existing policies in RayInstanceRole
        - PolicyName: EFSAccessPolicy
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - elasticfilesystem:ClientMount
                  - elasticfilesystem:ClientWrite
                  - elasticfilesystem:ClientRootAccess
                Resource: arn:aws:elasticfilesystem:us-west-2:892335585962:file-system/fs-08e6f8d79aaa5fd6e
```

3. Add NFS port to Ray Security Group:

```yaml
  RaySecurityGroup:
    Properties:
      SecurityGroupIngress:
        # Add this to existing ingress rules
        - IpProtocol: tcp
          FromPort: 2049
          ToPort: 2049
          CidrIp: !Ref AllowedIpRange
```

## Deployment Instructions

1. Update the CloudFormation template with the modifications above.

2. Deploy or update the stack using AWS CLI:
```bash
aws cloudformation deploy \
  --template-file ray-cluster.yaml \
  --stack-name ray-cluster \
  --parameter-overrides \
    Environment=production \
    ProjectName=ray-cluster \
    KeyPairName=your-key-pair \
    AllowedIpRange=0.0.0.0/0 \
  --capabilities CAPABILITY_NAMED_IAM
```

3. After deployment, verify EFS mount on worker nodes:
```bash
sudo mkdir -p /shared
sudo mount -t efs -o tls fs-08e6f8d79aaa5fd6e:/ /shared
```
> In the current implementation the `/shared` filesystem is not used.

## Security Considerations

1. The current setup allows access from 0.0.0.0/0 to several ports. Consider restricting this to specific IP ranges in production.
2. EFS mount uses TLS for security in transit.
3. IAM roles follow principle of least privilege but could be further restricted based on specific needs.

## Monitoring and Maintenance

1. Monitor EFS mount status using:
```bash
sudo systemctl status amazon-efs-mount-watchdog.service
```

2. Check security group configurations:
```bash
aws ec2 describe-security-groups \
    --group-ids sg-030176ebd4455dcc5 \
    --region us-west-2
```
For installing amazon-efs-utils on Ubuntu 20.04 (which the Deep Learning AMI uses), is needed to build them from source:

```
sudo apt-get update
sudo apt-get -y install binutils git make
git clone https://github.com/aws/efs-utils
cd efs-utils
./build-deb.sh
sudo apt-get -y install ./build/amazon-efs-utils*deb
```

## Auditing

The `ray_cluster_aws_config_dump_[date].txt` file contains a detailed snapshot of the AWS infrastructure configuration for a Ray cluster taken [date] with the following script:
```
./scripts/dump_ray_config.sh
```
The output file is for auditing and it includes:

- IAM configuration with instance profile details and attached policies
- VPC configuration showing subnet details and CIDR blocks
- Network components including internet gateway and route tables
- Security group rules listing all open ports and allowed traffic
- AMI details for the Deep Learning Base AMI with NVIDIA drivers
- Quick reference section with key resource IDs and configuration requirements
- Required ports list for Ray cluster functionality

The file serves as an infrastructure audit document, showing the complete AWS setup supporting the Ray cluster deployment.

## Future Improvements

1. Consider implementing private subnets with NAT Gateway for worker nodes
2. Add backup policy for EFS
3. Implement more granular security group rules
4. Add monitoring and alerting for the Ray cluster
5. Consider using AWS Secrets Manager for sensitive configurations