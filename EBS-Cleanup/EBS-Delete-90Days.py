import boto3
import csv
import pandas as pd
from datetime import datetime, timezone, timedelta

# Initialize EC2 client
ec2 = boto3.client('ec2')

def is_available_for_90_days(volume):
    """ Check if volume has been in 'available' state for 90+ days """
    now = datetime.now(timezone.utc)
    if 'CreateTime' in volume and 'Attachments' in volume:
        # If it's unattached, check how long it's been 'available'
        if len(volume['Attachments']) == 0:
            create_time = volume['CreateTime']
            age = now - create_time
            return age.days >= 90
    return False

# Step 1: Retrieve all volumes
def get_old_available_volumes():
    """ Fetch volumes that transitioned to 'available' state 90+ days ago """
    volumes = ec2.describe_volumes()['Volumes']
    return [vol for vol in volumes if is_available_for_90_days(vol)]

# Step 2: Save volume details before deletion
def save_volumes_to_csv(volumes, filename):
    """ Save volume details to a CSV file """
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Volume ID", "Size (GB)", "Created Date", "State", "Age (Days)"])
        now = datetime.now(timezone.utc)
        for vol in volumes:
            age = (now - vol['CreateTime']).days
            writer.writerow([
                vol['VolumeId'], 
                vol['Size'], 
                vol['CreateTime'].strftime('%Y-%m-%d %H:%M:%S %Z'),
                vol['State'],
                age
            ])
    print(f"Volume details saved to {filename}")

# Step 3: Delete volumes that meet the criteria
def delete_old_volumes(volumes):
    """ Delete volumes that have been in 'available' state for 90+ days """
    deleted_volumes = []
    
    for vol in volumes:
        volume_id = vol['VolumeId']
        
        try:
            print(f"Deleting Volume: {volume_id}")
            ec2.delete_volume(VolumeId=volume_id)
            deleted_volumes.append({
                "VolumeId": volume_id,
                "Size": vol["Size"],
                "CreateTime": vol["CreateTime"].strftime('%Y-%m-%d %H:%M:%S %Z'),
                "Age (Days)": (datetime.now(timezone.utc) - vol["CreateTime"]).days
            })
        
        except Exception as e:
            print(f"Failed to delete volume {volume_id}: {str(e)}")

    return deleted_volumes

# Step 4: Save deleted volume details
def save_deleted_volumes_to_csv(deleted_volumes, filename):
    """ Save deleted volume details to a CSV file """
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Volume ID", "Size (GB)", "Created Date", "Age (Days)"])
        for vol in deleted_volumes:
            writer.writerow([vol['VolumeId'], vol['Size'], vol['CreateTime'], vol['Age (Days)']])
    print(f"Deleted volume details saved to {filename}")

def main():
    try:
        print("Retrieving volumes that have been 'available' for more than 90 days...")
        old_volumes = get_old_available_volumes()

        total_volumes = len(old_volumes)
        if total_volumes == 0:
            print("No volumes found that meet the criteria.")
            return

        print(f"Found {total_volumes} volumes eligible for deletion.")

        # Save initial state
        save_volumes_to_csv(old_volumes, "old_available_volumes_before_deletion.csv")

        # Execute deletion
        deleted_volumes = delete_old_volumes(old_volumes)

        # Save details after deletion
        save_deleted_volumes_to_csv(deleted_volumes, "deleted_old_available_volumes.csv")

        print(f"\nTotal volumes deleted: {len(deleted_volumes)}")
        if deleted_volumes:
            print("Deleted Volume IDs:")
            for vol in deleted_volumes:
                print(f"- {vol['VolumeId']} (Created: {vol['CreateTime']})")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
