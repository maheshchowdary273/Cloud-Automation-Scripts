import boto3
import csv
import pandas as pd

# Initialize EC2 client
ec2 = boto3.client('ec2')

# Retrieve all volumes
volumes = ec2.describe_volumes()['Volumes']

# Calculate total number of volumes and total size in GB
total_volumes = len(volumes)
total_size_gb = sum(v['Size'] for v in volumes)

# Save results to CSV
csv_filename = "total_ebs_volumes.csv"
with open(csv_filename, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Volume ID", "Size (GB)", "State", "Created Date"])
    for vol in volumes:
        writer.writerow([vol['VolumeId'], vol['Size'], vol['State'], vol['CreateTime']])

print(f"Data saved to {csv_filename}")

# Save results to Excel
excel_filename = "total_ebs_volumes.xlsx"
df = pd.DataFrame([
    {"VolumeId": v["VolumeId"], "Size": v["Size"], "State": v["State"], "CreateTime": v["CreateTime"].replace(tzinfo=None)}
    for v in volumes
])
df.to_excel(excel_filename, index=False)

print(f"Data saved to {excel_filename}")

# Summary print
print(f"Total EBS volumes: {total_volumes}")
print(f"Total size of all volumes: {total_size_gb} GB")
