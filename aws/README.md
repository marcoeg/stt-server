Here's a comprehensive README.md for the Ray cluster infrastructure setup:

```markdown
# Ray Cluster AWS Infrastructure Setup

This repository contains CloudFormation templates for setting up the required AWS infrastructure for a Ray cluster. The infrastructure includes VPC, subnet, security groups, and IAM roles required to run a Ray cluster on AWS.

## Prerequisites

- AWS CLI installed and configured
- Appropriate AWS permissions to create:
  - VPC and associated networking resources
  - Security Groups
  - IAM Roles and Instance Profiles
  - CloudFormation stacks
- An existing EC2 key pair in your target region

## Infrastructure Overview

The CloudFormation template (`ray-cluster.yaml`) creates the following resources:

- **VPC** with:
  - Public subnet
  - Internet Gateway
  - Route table with internet access
- **Security Group** with rules for:
  - SSH (port 22)
  - Ray dashboard (port 8265)
  - Ray GCS (port 6379)
  - Ray client (port 10001)
  - Ray worker ports (10000-19999)
  - Internal cluster communication
- **IAM Role and Instance Profile** with:
  - EC2 full access
  - S3 full access
  - Custom policies for Ray autoscaling

## Quick Start
1. Insure the account has appropriate AWS permissions

```
chmod +x check_permissions.sh
./check_permissions.sh
```

2. Create a parameters file `params.json`:
```json
{
  "Parameters": {
    "Environment": "production",
    "ProjectName": "ray-cluster",
    "KeyPairName": "your-key-pair-name",
    "AllowedIpRange": "0.0.0.0/0",
    "VpcCidr": "172.30.0.0/16",
    "SubnetCidr": "172.30.0.0/24",
    "AvailabilityZone": "us-west-2a",
    "RayAmiId": "ami-05c1fa8c9881244b6"
  }
}
```

3. Deploy the stack:
```bash
aws cloudformation create-stack \
  --stack-name ray-cluster-infrastructure \
  --template-body file://ray-cluster.yaml \
  --parameters file://params.json \
  --capabilities CAPABILITY_NAMED_IAM
```

4. Monitor the stack creation:
```bash
aws cloudformation describe-stacks \
  --stack-name ray-cluster-infrastructure \
  --query 'Stacks[0].StackStatus'
```

## Parameters

| Parameter | Description | Default | Required |
|-----------|-------------|---------|----------|
| Environment | Deployment environment | production | Yes |
| ProjectName | Project name for resource tagging | ray-cluster | Yes |
| KeyPairName | EC2 key pair name | - | Yes |
| AllowedIpRange | CIDR block for security group access | 0.0.0.0/0 | Yes |
| VpcCidr | CIDR block for VPC | 172.30.0.0/16 | Yes |
| SubnetCidr | CIDR block for Subnet | 172.30.0.0/24 | Yes |
| AvailabilityZone | AZ for the subnet | us-west-2a | Yes |
| RayAmiId | AMI ID for Ray nodes | ami-05c1fa8c9881244b6 | Yes |

## Stack Outputs

The stack provides several outputs that can be used in your Ray cluster configuration:

- VpcId
- SubnetId
- SecurityGroupId
- InstanceProfileArn
- InstanceProfileName
- RayRoleName

To view the outputs:
```bash
aws cloudformation describe-stacks \
  --stack-name ray-cluster-infrastructure \
  --query 'Stacks[0].Outputs'
```

## Using with Ray

After the infrastructure is created, use the outputs in your Ray cluster configuration file:

```yaml
# cluster.yaml
cluster_name: ray-cluster
provider:
    type: aws
    region: us-west-2
    availability_zone: us-west-2a
    cache_stopped_nodes: False

auth:
    ssh_user: ubuntu
    ssh_private_key: ~/.ssh/your-key-pair.pem

head_node_type: head_node
available_node_types:
    head_node:
        node_config:
            SubnetId: <SubnetId from stack output>
            SecurityGroupIds: ["<SecurityGroupId from stack output>"]
            IamInstanceProfile:
                Arn: <InstanceProfileArn from stack output>
```

## Clean Up

To delete the stack and all associated resources:
```bash
aws cloudformation delete-stack \
  --stack-name ray-cluster-infrastructure
```

## Security Considerations

- The default `AllowedIpRange` is set to `0.0.0.0/0`. For production environments, restrict this to your specific IP ranges.
- The template creates IAM roles with EC2 and S3 full access. Consider restricting these permissions based on your needs.
- Review and modify the security group rules according to your security requirements.

## Troubleshooting

1. Stack creation fails with permissions error:
   - Ensure you have the necessary AWS permissions
   - Check if the role names already exist in your account

2. Resources not deleted properly:
   - Ensure no resources are in use before deletion
   - Delete any dependent resources manually if needed
