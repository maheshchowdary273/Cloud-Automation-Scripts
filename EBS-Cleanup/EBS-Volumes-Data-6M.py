import boto3
import csv
import pandas as pd
from datetime import datetime, timedelta, timezone

# Initialize EC2 client
ec2 = boto3.client('ec2')

# Define the date threshold (six months ago) with proper timezone handling
six_months_ago = datetime.now(timezone.utc) - timedelta(days=6*30)

# Retrieve all volumes
volumes = ec2.describe_volumes()['Volumes']

# Filter volumes
filtered_volumes = [
    v for v in volumes
    if v['State'] == 'available' and v['CreateTime'].replace(tzinfo=timezone.utc) < six_months_ago
]

# Save results to CSV
csv_filename = "unused_volumes.csv"
with open(csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Volume ID", "Size (GB)", "Created Date"])
    for vol in filtered_volumes:
        writer.writerow([vol['VolumeId'], vol['Size'], vol['CreateTime']])

print(f"Data saved to {csv_filename}")

# Save results to Excel
excel_filename = "unused_volumes.xlsx"
#df = pd.DataFrame(filtered_volumes, columns=["VolumeId", "Size", "CreateTime"])
df = pd.DataFrame([
    {"VolumeId": v["VolumeId"], "Size": v["Size"], "CreateTime": v["CreateTime"].replace(tzinfo=None)}
    for v in filtered_volumes
])

df.to_excel(excel_filename, index=False)

print(f"Data saved to {excel_filename}")

# Summary print
print(f"Total unused volumes older than 6 months: {len(filtered_volumes)}")
print(f"Total size of these volumes: {sum(v['Size'] for v in filtered_volumes)} GB")