import boto3
from datetime import datetime, timedelta

# Initialize EC2 client
ec2_client = boto3.client('ec2')

def get_unattached_old_volumes():
    """ Fetch EBS volumes older than 180 days and unattached """
    volumes = ec2_client.describe_volumes()['Volumes']
    
    old_unattached_volumes = []
    cutoff_date = datetime.utcnow() - timedelta(days=180)

    for volume in volumes:
        create_time = volume['CreateTime']
        state = volume['State']  # Check attachment status
        if create_time < cutoff_date and state == 'available':
            old_unattached_volumes.append(volume['VolumeId'])

    return old_unattached_volumes

def delete_unattached_old_volumes():
    """ Delete unattached volumes older than 180 days """
    old_unattached_volumes = get_unattached_old_volumes()

    for volume_id in old_unattached_volumes:
        print(f"Deleting unattached volume: {volume_id}")
        ec2_client.delete_volume(VolumeId=volume_id)

    return f"Deleted {len(old_unattached_volumes)} unattached old volumes."

# Execute deletion
delete_unattached_old_volumes()
