
import boto3
import csv

region = "us-west-2"  # Replace with your region
identity_store_id = "d-*"  # Replace with your actual Identity Store ID

identitystore = boto3.client('identitystore', region_name=region)

def list_users_in_groups_to_csv():
    users_in_groups = {}

    # List all groups
    groups = []
    paginator = identitystore.get_paginator('list_groups')
    for page in paginator.paginate(IdentityStoreId=identity_store_id):
        groups.extend(page['Groups'])

    # For each group, get its members
    for group in groups:
        group_id = group['GroupId']
        group_name = group['DisplayName']
        members = identitystore.list_group_memberships(
            IdentityStoreId=identity_store_id,
            GroupId=group_id
        )

        for member in members['GroupMemberships']:
            user_id = member['MemberId']['UserId']
            if user_id not in users_in_groups:
                users_in_groups[user_id] = []
            users_in_groups[user_id].append(group_name)

    # Write to CSV
    with open("iam_identitycenter_users_groups.csv", "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Username", "Groups"])

        for user_id, group_names in users_in_groups.items():
            user_details = identitystore.describe_user(
                IdentityStoreId=identity_store_id,
                UserId=user_id
            )
            username = user_details['UserName']
            writer.writerow([username, ", ".join(group_names)])

    print("✅ Export complete! File saved as iam_identitycenter_users_groups.csv")

list_users_in_groups_to_csv()
