import boto3
import csv
from datetime import datetime, timezone

# Initialize EC2 client
ec2 = boto3.client('ec2')

def is_available_for_days(volume, days):
    """Check if volume has been in 'available' state for the specified number of days."""
    now = datetime.now(timezone.utc)
    if 'CreateTime' in volume and 'Attachments' in volume:
        if len(volume['Attachments']) == 0:
            age = now - volume['CreateTime']
            return age.days >= days
    return False

def get_old_available_volumes(days):
    """Fetch volumes that transitioned to 'available' state X days ago."""
    volumes = ec2.describe_volumes()['Volumes']
    return [vol for vol in volumes if is_available_for_days(vol, days)]

def delete_old_volumes(volumes):
    """Delete volumes that have been in 'available' state for X days."""
    deleted_volumes = []
    for vol in volumes:
        volume_id = vol['VolumeId']
        try:
            print(f"Deleting Volume: {volume_id}")
            ec2.delete_volume(VolumeId=volume_id)
            deleted_volumes.append(volume_id)
        except Exception as e:
            print(f"Failed to delete volume {volume_id}: {str(e)}")
    return deleted_volumes

def lambda_handler(event, context):
    """AWS Lambda handler function."""
    try:
        # Get threshold days from the event payload
        days_threshold = event.get('days_threshold', 30)  # Default to 30 days

        print(f"Retrieving volumes older than {days_threshold} days...")
        old_volumes = get_old_available_volumes(days_threshold)

        if not old_volumes:
            print("No volumes found that meet the criteria.")
            return {"status": "No volumes eligible for deletion"}

        print(f"Found {len(old_volumes)} volumes eligible for deletion.")

        # Execute deletion process
        deleted_volumes = delete_old_volumes(old_volumes)

        return {
            "status": "Deletion completed",
            "deleted_volumes": deleted_volumes
        }

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return {"status": "Error", "message": str(e)}
