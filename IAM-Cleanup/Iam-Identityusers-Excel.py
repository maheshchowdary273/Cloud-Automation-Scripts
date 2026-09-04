import boto3
from openpyxl import Workbook

region = "us-west-2"  # Replace with your AWS region
identity_store_id = "d-*"  # Replace with your Identity Store ID

identitystore = boto3.client('identitystore', region_name=region)

def list_users_in_groups_to_xlsx():
    users_in_groups = {}

    # List all groups
    groups = []
    paginator = identitystore.get_paginator('list_groups')
    for page in paginator.paginate(IdentityStoreId=identity_store_id):
        groups.extend(page['Groups'])

    # For each group, get members
    for group in groups:
        group_id = group['GroupId']
        group_name = group['DisplayName']
        memberships = identitystore.list_group_memberships(
            IdentityStoreId=identity_store_id,
            GroupId=group_id
        )
        for membership in memberships['GroupMemberships']:
            user_id = membership['MemberId']['UserId']
            if user_id not in users_in_groups:
                users_in_groups[user_id] = []
            users_in_groups[user_id].append(group_name)

    # Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "IAM Identity Center Users"

    # Header row
    ws.append(["Username", "Groups"])

    for user_id, group_names in users_in_groups.items():
        user_details = identitystore.describe_user(
            IdentityStoreId=identity_store_id,
            UserId=user_id
        )
        username = user_details['UserName']
        ws.append([username, ", ".join(group_names)])

    wb.save("iam_identitycenter_users_groups.xlsx")
    print("✅ XLSX file created: iam_identitycenter_users_groups.xlsx")

list_users_in_groups_to_xlsx()
