import boto3

# Initialize EC2 client
ec2_client = boto3.client('ec2')

def get_total_ebs_volume_size():
    # Retrieve all EBS volumes
    volumes = ec2_client.describe_volumes(Filters=[{'Name': 'status', 'Values': ['in-use']}])

    # Calculate total size
    total_size = sum(volume['Size'] for volume in volumes['Volumes'])

    return total_size

# Run the function
total_volume_size = get_total_ebs_volume_size()
print(f"Total size of EBS volumes in 'in-use' state: {total_volume_size} GB")
