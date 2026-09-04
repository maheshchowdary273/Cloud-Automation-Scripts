import boto3
import csv
import pandas as pd

# Initialize EC2 client
ec2 = boto3.client('ec2')

# Step 1: Retrieve all volumes
def get_all_volumes():
    """ Fetch all EBS volumes """
    volumes = ec2.describe_volumes()['Volumes']
    return volumes

# Step 2: Save initial volume details (before deletion)
def save_volumes_to_csv(volumes, filename):
    """ Save volume details to a CSV file """
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Volume ID", "Size (GB)", "Created Date", "State"])
        for vol in volumes:
            writer.writerow([
                vol['VolumeId'], 
                vol['Size'], 
                vol['CreateTime'].strftime('%Y-%m-%d %H:%M:%S %Z'),  # Convert datetime to string
                vol['State']
            ])
    print(f"Volume details saved to {filename}")

def save_volumes_to_excel(volumes, filename):
    """ Save volume details to an Excel file """
    df = pd.DataFrame([
        {
            "VolumeId": v["VolumeId"],
            "Size": v["Size"],
            "CreateTime": v["CreateTime"].strftime('%Y-%m-%d %H:%M:%S %Z'),  # Convert datetime to string
            "State": v["State"]
        }
        for v in volumes
    ])
    df.to_excel(filename, index=False)
    print(f"Volume details saved to {filename}")

# Step 3: Delete all retrieved volumes
def delete_all_volumes(volumes):
    """ Delete all volumes retrieved """
    deleted_volumes = []

    for vol in volumes:
        volume_id = vol['VolumeId']
        
        try:
            print(f"Deleting Volume: {volume_id}")
            ec2.delete_volume(VolumeId=volume_id)
            deleted_volumes.append({
                "VolumeId": volume_id,
                "Size": vol["Size"],
                "CreateTime": vol["CreateTime"].strftime('%Y-%m-%d %H:%M:%S %Z')  # Convert datetime to string
            })
        
        except Exception as e:
            print(f"Failed to delete volume {volume_id}: {str(e)}")

    return deleted_volumes

# Step 4: Save deleted volume details (after deletion)
def save_deleted_volumes_to_csv(deleted_volumes, filename):
    """ Save deleted volume details to a CSV file """
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Volume ID", "Size (GB)", "Created Date"])
        for vol in deleted_volumes:
            writer.writerow([vol['VolumeId'], vol['Size'], vol['CreateTime']])
    print(f"Deleted volume details saved to {filename}")

def save_deleted_volumes_to_excel(deleted_volumes, filename):
    """ Save deleted volume details to an Excel file """
    df = pd.DataFrame(deleted_volumes)
    df.to_excel(filename, index=False)
    print(f"Deleted volume details saved to {filename}")

def main():
    try:
        # Execute retrieval and save details before deletion
        print("Retrieving volumes...")
        volumes = get_all_volumes()
        
        print(f"Found {len(volumes)} volumes")
        
        # Save initial state
        save_volumes_to_csv(volumes, "all_volumes_before_deletion.csv")
        save_volumes_to_excel(volumes, "all_volumes_before_deletion.xlsx")

        # Execute deletion
        deleted_volumes = delete_all_volumes(volumes)

        # Save details after deletion
        save_deleted_volumes_to_csv(deleted_volumes, "deleted_volumes.csv")
        save_deleted_volumes_to_excel(deleted_volumes, "deleted_volumes.xlsx")

        # Summary print
        deleted_count = len(deleted_volumes)
        print(f"\nTotal volumes deleted: {deleted_count}")
        if deleted_count > 0:
            print("Deleted Volume IDs:")
            for vol in deleted_volumes:
                print(f"- {vol['VolumeId']}")
                
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
