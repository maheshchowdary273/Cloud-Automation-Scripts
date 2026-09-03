#!/bin/bash

INSTANCE_ARN="Replace_with_your_instance_arn SSO Integration id"
IDENTITY_STORE_ID="Replace_with_your_identity_store_id"  
CSV_FILE="ad_group_permissions.csv" #Download CSV file containing AD group permissions
EXCEL_FILE="ad_group_permissions.xlsx"

echo "S.No,AD Group,Account ID,Account Name,Permission Set" > $CSV_FILE
SN=1  # Serial number counter

# Fetch all AD groups
aws identitystore list-groups --identity-store-id "$IDENTITY_STORE_ID" | jq -r '.Groups[] | "\(.GroupId),\(.DisplayName)"' > ad_groups.tmp

# Fetch all permission sets
aws sso-admin list-permission-sets --instance-arn "$INSTANCE_ARN" | jq -r '.PermissionSets[]' > permission_sets.tmp

# Loop through each AD group
while IFS=',' read -r GROUP_ID GROUP_NAME; do
    # Fetch accounts linked to this AD group
    aws identitystore list-group-memberships --identity-store-id "$IDENTITY_STORE_ID" --group-id "$GROUP_ID" | jq -r '.GroupMemberships[].MemberId' | while read -r ACCOUNT_ID; do

        # Ensure Account ID format is valid (12-digit numeric)
        if [[ ! "$ACCOUNT_ID" =~ ^[0-9]{12}$ ]]; then
            echo "Skipping invalid Account ID: $ACCOUNT_ID"
            continue
        fi

        # Get the account name
        ACCOUNT_NAME=$(aws organizations describe-account --account-id "$ACCOUNT_ID" 2>/dev/null | jq -r '.Account.Name')

        # Check for errors in Account Name retrieval
        [[ -z "$ACCOUNT_NAME" || "$ACCOUNT_NAME" == "null" ]] && ACCOUNT_NAME="Unknown Account"

        # Loop through permission sets
        while read -r PERMISSION_SET_ARN; do
            PERMISSION_NAME=$(aws sso-admin describe-permission-set --instance-arn "$INSTANCE_ARN" --permission-set-arn "$PERMISSION_SET_ARN" | jq -r '.PermissionSet.Name')

            echo "$SN,$GROUP_NAME,$ACCOUNT_ID,$ACCOUNT_NAME,$PERMISSION_NAME" >> $CSV_FILE
            ((SN++))
        done < permission_sets.tmp
    done
done < ad_groups.tmp

# Cleanup temp files
rm ad_groups.tmp permission_sets.tmp

# Convert CSV to Excel
if command -v csvformat &> /dev/null; then
    csvformat -T $CSV_FILE | tee $EXCEL_FILE
    echo "Spreadsheet '$EXCEL_FILE' created successfully!"
else
    echo "csvkit is not installed. Install it using 'pip3 install csvkit' to generate an Excel-compatible file."
fi
