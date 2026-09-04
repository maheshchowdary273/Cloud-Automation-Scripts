import boto3
import csv
import pandas as pd

# Initialize EC2 client
ec2 = boto3.client('ec2')

# Retrieve all volumes
volumes = ec2.describe_volumes()['Volumes']

# Filter volumes in "in-use" state
used_volumes = [v for v in volumes if v['State'] == 'in-use']

# Calculate total number of used volumes and their total size in GB
total_used_volumes = len(used_volumes)
total_used_size_gb = sum(v['Size'] for v in used_volumes)

# Save results to CSV
csv_filename = "used_volumes.csv"
with open(csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Volume ID", "Size (GB)", "Created Date"])
    for vol in used_volumes:
        writer.writerow([vol['VolumeId'], vol['Size'], vol['CreateTime']])

print(f"Data saved to {csv_filename}")

# Save results to Excel
excel_filename = "used_volumes.xlsx"
df = pd.DataFrame([
    {"VolumeId": v["VolumeId"], "Size": v["Size"], "CreateTime": v["CreateTime"].replace(tzinfo=None)}
    for v in used_volumes
])
df.to_excel(excel_filename, index=False)

print(f"Data saved to {excel_filename}")

# Summary print
print(f"Total used volumes: {total_used_volumes}")
print(f"Total size of used volumes: {total_used_size_gb} GB")
