import boto3
import csv
from datetime import datetime, timedelta

# Initialize the EC2 client
ec2_client = boto3.client('ec2')

# Calculate the date 6 months ago
six_months_ago = datetime.utcnow() - timedelta(days=180)

# Retrieve all snapshots for the account
snapshots = ec2_client.describe_snapshots(OwnerIds=['self'])['Snapshots']

# Filter snapshots older than 6 months
old_snapshots = []
for snapshot in snapshots:
    snapshot_id = snapshot['SnapshotId']
    creation_date = snapshot['StartTime'].replace(tzinfo=None)  # Remove timezone for comparison
    
    if creation_date < six_months_ago:
        old_snapshots.append([snapshot_id, str(creation_date)])

# Define CSV file name
csv_filename = "old_ebs_snapshots.csv"

# Write data to CSV file
with open(csv_filename, mode="w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["Snapshot ID", "Creation Date"])  # Write header
    writer.writerows(old_snapshots)  # Write data

# Print the summary
snapshot_count = len(old_snapshots)
if snapshot_count > 0:
    print(f"Total snapshots older than 6 months: {snapshot_count}")
    print(f"Data exported to {csv_filename}")
else:
    print("No snapshots older than 6 months found.")
