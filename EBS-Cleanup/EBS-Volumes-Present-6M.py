import boto3
import csv
import pandas as pd
from datetime import datetime, timedelta, timezone

# Initialize EC2 client
ec2 = boto3.client('ec2')

# Define the date range (from now to 6 months ago)
six_months_ago = datetime.now(timezone.utc) - timedelta(days=6*30)

# Retrieve all volumes
volumes = ec2.describe_volumes()['Volumes']

# Filter unused volumes created in the last six months
filtered_volumes = [
    v for v in volumes
    if v['State'] == 'available' and v['CreateTime'].replace(tzinfo=timezone.utc) >= six_months_ago
]

# Calculate total number of volumes and total size in GB
total_volumes = len(filtered_volumes)
total_size_gb = sum(v['Size'] for v in filtered_volumes)

# Save results to CSV
csv_filename = "unused_recent_volumes.csv"
with open(csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Volume ID", "Size (GB)", "Created Date"])
    for vol in filtered_volumes:
        writer.writerow([vol['VolumeId'], vol['Size'], vol['CreateTime']])

print(f"Data saved to {csv_filename}")

# Save results to Excel
excel_filename = "unused_recent_volumes.xlsx"
df = pd.DataFrame([
    {"VolumeId": v["VolumeId"], "Size": v["Size"], "CreateTime": v["CreateTime"].replace(tzinfo=None)}
    for v in filtered_volumes
])
df.to_excel(excel_filename, index=False)

print(f"Data saved to {excel_filename}")

# Summary print
print(f"Total unused volumes created within the last 6 months: {total_volumes}")
print(f"Total size of these volumes: {total_size_gb} GB")

