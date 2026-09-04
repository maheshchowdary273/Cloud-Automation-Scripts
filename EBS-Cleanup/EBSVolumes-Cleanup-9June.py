"""Created by : Mahesh.chowdary@sandisk.com
Used for EBS Volumes deletion after unused/Available state > 30 Days
"""

import boto3
import pandas as pd
from datetime import datetime, timezone

# Generate current timestamp for subject
current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

# AWS Clients
ec2 = boto3.client('ec2')
s3 = boto3.client('s3')
sns = boto3.client('sns')

BUCKET_NAME = "sd-cs-ebsvolumes-deletion-1month"
SNS_TOPIC_ARN = "arn:aws:sns:us-west-2:891376977848:SD-CS-EBS-Deletion-30Days"


def get_timestamp():
    """Generate a timestamp for file names."""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

def save_to_s3_excel(data, prefix):
    """Save data to S3 in Excel format with a timestamped filename."""
    timestamp = get_timestamp()
    file_name = f"{prefix}_{timestamp}.xlsx"
    excel_file = f"/tmp/{file_name}"  # Temporary storage in Lambda

    # Convert datetime fields to timezone-unaware format
    for vol in data:
        if isinstance(vol.get("CreateTime"), datetime):
            vol["CreateTime"] = vol["CreateTime"].replace(tzinfo=None)  # Make datetime naive

    df = pd.DataFrame(data)
    df.to_excel(excel_file, index=False)
    s3.upload_file(excel_file, BUCKET_NAME, file_name)
    print(f"Saved {file_name} to S3 (Excel).")

def filter_old_volumes(event):
    """Retrieve and filter old volumes available for more than X days."""
    now = datetime.now(timezone.utc)
    days_threshold = event.get("days_threshold", 30)  # Default to 30 days if not provided

    response = ec2.describe_volumes()
    volumes = response["Volumes"]

    old_volumes = []
    for vol in volumes:
        create_time = vol['CreateTime']

        # Ensure `CreateTime` is properly timezone-aware
        if create_time.tzinfo is None:  
            create_time = create_time.replace(tzinfo=timezone.utc)

        # Filter volumes that have been available for more than `days_threshold` days
        if vol['State'] == 'available' and (now - create_time).days >= days_threshold:
            old_volumes.append(vol)
    
    return old_volumes

def delete_volumes(old_volumes):
    """Delete only volumes from the filtered old volumes list."""
    deleted_volumes = []
    for vol in old_volumes:
        volume_id = vol["VolumeId"]
        try:
            ec2.delete_volume(VolumeId=volume_id)
            vol["DeletedAt"] = datetime.now(timezone.utc).isoformat()
            deleted_volumes.append(vol)
            print(f"Deleted Volume: {volume_id}")
        except Exception as e:
            print(f"Error deleting {volume_id}: {str(e)}")
    return deleted_volumes

def send_sns_notification(old_volumes, deleted_volumes):
    """Send SNS notification with deletion summary including Volume IDs, Sizes, and Deletion timestamps."""
    
    deleted_volumes_info = [
        f"{vol['VolumeId']} (Size: {vol['Size']} GB, Deleted At: {vol['DeletedAt']})"
        for vol in deleted_volumes
    ]  # Extract Volume ID, Size, and Deleted Timestamp

    message = f"""EBS Volume Deletion Summary:
    - Old Volumes Found > 30 Days: {len(old_volumes)}
    - Volumes Deleted: {len(deleted_volumes)}
    - Deleted Volume Details: {', '.join(deleted_volumes_info)}
    """

    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Message=message,
        Subject=f"EBS Volume Deletion Notification - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )
    print("SNS Notification Sent.")


def lambda_handler(event, context):
    """AWS Lambda entry function."""
    print("Filtering volumes available for more than 90 days...")
    old_volumes = filter_old_volumes(event)
    
    save_to_s3_excel(old_volumes, "old_volumes")

    print("Deleting only old volumes...")
    deleted_volumes = delete_volumes(old_volumes)
    
    save_to_s3_excel(deleted_volumes, "deleted_volumes")

    # Send SNS notification after deletion
    send_sns_notification(old_volumes, deleted_volumes)

    return {
        "status": "Success",
        "old_volumes": len(old_volumes),
        "deleted_volumes": len(deleted_volumes)
    }
