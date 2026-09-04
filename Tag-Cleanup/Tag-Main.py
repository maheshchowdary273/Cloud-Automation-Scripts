import boto3
import botocore
import re
import pandas as pd
from boto3.session import Session
from concurrent.futures import ThreadPoolExecutor, as_completed

# 1) AWS SSO Profile & clients
session = Session(profile_name='M')
resource_explorer = session.client('resource-explorer-2')

# 2) Default tags
DEFAULT_TAGS = {
    'Application': '',
    'Cost center': '',
    'Department': '',
    'Environment': '',
    'Name': '',
    'Owner': '',
    'Region': ''   # overwritten per-resource
}

view_arn = (
    #'arn:aws:resource-explorer-2:us-west-2:*:view/all-resources/*-a810-46f7-*-*'
)

# 3) Plugin registry
TAGGING_PLUGINS = {}

def register_plugin(service_name):
    def decorator(func):
        TAGGING_PLUGINS[service_name] = func
        return func
    return decorator

@register_plugin('s3')
def tag_s3(arn, region, tags):
    bucket = arn.split(':')[-1]
    # skip dashboards / invalid names
    if '/' in bucket or bucket.startswith('storage-lens'):
        reason = f"invalid-bucket:{bucket}"
        print(f"⚠️ Skipping S3 resource — {reason}")
        return False, reason
    try:
        s3 = session.client('s3', region_name=region)
        s3.put_bucket_tagging(
            Bucket=bucket,
            Tagging={'TagSet': [{'Key': k, 'Value': v} for k, v in tags.items()]}
        )
        print(f"🧩 Tagged S3 bucket — {bucket} in {region}")
        return True, None
    except Exception as e:
        reason = str(e)
        print(f"❌ S3 tagging failed for {bucket}: {reason}")
        return False, reason

SERVICE_LINKED_PREFIXES = [
    "aws-service-role/",
    "service-role/"
]

@register_plugin('iam')
def tag_iam(arn, region, tags):
    """
    Unified IAM tagging: roles, policies, SAML and OIDC providers.
    Skips AWS-managed service-linked roles and over-long names.
    """
    resource_path = arn.split(':')[-1]
    try:
        res_type, res_name = resource_path.split('/', 1)
    except ValueError:
        reason = f"UnsupportedIAMFormat:{resource_path}"
        print(f"⚠️ Skipping IAM resource — {reason}")
        return False, reason

    # Skip service-linked roles
    if res_type == 'role' and any(res_name.startswith(p) for p in SERVICE_LINKED_PREFIXES):
        reason = f"ServiceLinkedRole:{res_name}"
        print(f"⚠️ Skipping AWS-managed service role — {reason}")
        return False, reason

    # Enforce IAM role name length
    if res_type == 'role' and len(res_name) > 64:
        reason = f"ValidationError:RoleNameTooLong:{res_name}"
        print(f"⚠️ Skipping IAM role — name too long: {res_name}")
        return False, reason

    iam = session.client('iam')
    tag_list = [{'Key': k, 'Value': v} for k, v in tags.items()]

    try:
        if res_type == 'role':
            iam.tag_role(RoleName=res_name, Tags=tag_list)
        elif res_type == 'policy':
            iam.tag_policy(PolicyArn=arn, Tags=tag_list)
        elif res_type == 'saml-provider':
            iam.tag_saml_provider(SAMLProviderArn=arn, Tags=tag_list)
        elif res_type == 'oidc-provider':
            iam.tag_open_id_connect_provider(
                OpenIDConnectProviderArn=arn, Tags=tag_list
            )
        else:
            reason = f"UnsupportedIAMType:{res_type}"
            print(f"⚠️ Skipping IAM {res_type} — not supported")
            return False, reason

        print(f"🧩 Tagged IAM {res_type} — {res_name}")
        return True, None

    except botocore.exceptions.ClientError as e:
        code = e.response['Error']['Code']
        if code in ("NoSuchEntity", "UnmodifiableEntity", "ValidationError"):
            reason = f"{code}:{res_name}"
            print(f"⚠️ {reason}")
            return False, reason
        msg = e.response['Error'].get('Message', str(e))
        reason = f"{code}:{msg}"
        print(f"❌ Unexpected IAM error for {res_name}: {reason}")
        return False, reason

@register_plugin('ec2')
def tag_ec2(arn, region, tags):
    resource_id = arn.split('/')[-1]
    ec2 = session.client('ec2', region_name=region)
    try:
        ec2.create_tags(
            Resources=[resource_id],
            Tags=[{'Key': k, 'Value': v} for k, v in tags.items()]
        )
        print(f"🧩 Tagged EC2/VPC resource — {resource_id} in {region}")
        return True, None
    except Exception as e:
        reason = str(e)
        print(f"❌ EC2 tagging failed for {resource_id}: {reason}")
        return False, reason

# 4) Helpers
def get_region_from_arn(arn):
    m = re.match(r'^arn:aws:[^:]+:([^:]+):', arn)
    return m.group(1) if m else 'us-east-1'

def get_service_from_arn(arn):
    m = re.match(r'^arn:aws:([^:]+):', arn)
    return m.group(1) if m else 'unknown'

# 5) Discover resources
def discover_resources():
    print("📍 Discovering resources...")
    resources, token = [], None
    while True:
        params = {'QueryString': '', 'ViewArn': view_arn}
        if token:
            params['NextToken'] = token
        resp = resource_explorer.search(**params)
        resources.extend(resp.get('Resources', []))
        token = resp.get('NextToken')
        if not token:
            break
    print(f"🔎 Found {len(resources)} resources.")
    return resources

# 6) Inspect & compute tags
def inspect_resource(r):
    arn = r['Arn']
    region = get_region_from_arn(arn)
    svc = get_service_from_arn(arn)
    existing = {}

    try:
        tg = session.client('resourcegroupstaggingapi', region_name=region)
        resp = tg.get_resources(ResourceARNList=[arn])
        mappings = resp.get('ResourceTagMappingList', [])
        if mappings:
            for t in mappings[0].get('Tags', []):
                existing[t['Key']] = t['Value']

        if 'terraform' in existing.get('ManagedBy', '').lower():
            return {'Arn': arn, 'Region': region, 'Service': svc, 'Reason': 'Terraform-managed'}

        to_add = {}
        changed = {}
        for key, default in DEFAULT_TAGS.items():
            desired = region if key == 'Region' else default
            current = existing.get(key)
            if current != desired:
                to_add[key] = desired
                changed[key] = desired

        if not to_add:
            return {'Arn': arn, 'Region': region, 'Service': svc, 'Reason': 'Already matching'}

        return {
            'Arn': arn,
            'Region': region,
            'Service': svc,
            'ExistingTags': existing,
            'TagsToAdd': to_add,
            'ChangedTags': changed
        }

    except Exception as e:
        reason = str(e)
        return {'Arn': arn, 'Region': region, 'Service': svc, 'Reason': f'Inspect error:{reason}'}

# 7) Identify tag updates
def identify(resources):
    print("📍 Identifying tag updates…")
    to_tag, skipped = [], []
    with ThreadPoolExecutor(max_workers=15) as ex:
        futures = [ex.submit(inspect_resource, r) for r in resources]
        for fut in as_completed(futures):
            res = fut.result()
            if 'TagsToAdd' in res:
                to_tag.append(res)
            else:
                skipped.append(res)
    print(f"🧮 To tag: {len(to_tag)} | Skipped: {len(skipped)}")
    return to_tag, skipped

# 8) Tag a single resource
def tag_resource(res):
    arn, region, tags = res['Arn'], res['Region'], res['TagsToAdd']
    svc = get_service_from_arn(arn)
    if svc in TAGGING_PLUGINS:
        return TAGGING_PLUGINS[svc](arn, region, tags)
    else:
        try:
            tg = session.client('resourcegroupstaggingapi', region_name=region)
            tg.tag_resources(ResourceARNList=[arn], Tags=tags)
            print(f"🔧 Tagged via default — {svc} in {region}")
            return True, None
        except Exception as e:
            reason = str(e)
            print(f"❌ Default tagging failed for {arn}: {reason}")
            return False, reason

# 9) Apply tags
def apply_tags(to_tag):
    print("📍 Applying tags…")
    successes, failures = [], []
    future_map = {}
    with ThreadPoolExecutor(max_workers=15) as ex:
        for r in to_tag:
            fut = ex.submit(tag_resource, r)
            future_map[fut] = r
        for fut in as_completed(future_map):
            r = future_map[fut]
            ok, reason = fut.result()
            if ok:
                successes.append(r)
            else:
                r['Reason'] = reason
                failures.append(r)
    print(f"✅ Tagged: {len(successes)} | ❌ Failed: {len(failures)}")
    return successes, failures

# 10) Export reports
def export_reports(successes, skipped, failures):
    print("📍 Exporting reports…")

    # successes
    pd.DataFrame([{
        'ARN': r['Arn'],
        'Region': r['Region'],
        'Service': r['Service'],
        'Changed Tags': r.get('ChangedTags', {}),
        'Existing Tags': r.get('ExistingTags', {})
    } for r in successes]).to_excel('tagging_report.xlsx', index=False)

    # skipped vs. failures
    pd.DataFrame(skipped).to_excel('skipped_resources.xlsx', index=False)
    pd.DataFrame(failures).to_excel('failed_resources.xlsx', index=False)

    # combined untaggable (for validation error extraction)
    untaggable = pd.DataFrame(skipped + failures)
    untaggable.to_excel('untaggable_resources.xlsx', index=False)

    # summary
    total = len(successes) + len(skipped) + len(failures)
    summary = pd.DataFrame({
        'Metric': ['Total Resources', 'Successfully Tagged', 'Skipped', 'Failed'],
        'Count': [total, len(successes), len(skipped), len(failures)]
    })
    with pd.ExcelWriter('report_summary.xlsx') as writer:
        summary.to_excel(writer, sheet_name='Summary', index=False)

    print("📁 Reports saved.")

# 11) Extract ValidationError ARNs & role names
def extract_validation_errors(report_file='untaggable_resources.xlsx'):
    df = pd.read_excel(report_file)
    val_errs = df[df['Reason'].str.startswith('ValidationError')]
    print("\n🔍 Validation Errors Found:")
    print("ARNs with ValidationError:")
    print(val_errs['Arn'].to_list(), "\n")
    role_names = val_errs['Arn'].apply(lambda arn: arn.split('/')[-1])
    print("Role names with ValidationError:")
    print(role_names.to_list())

# 12) Console summary
def display_summary(successes, skipped, failures):
    total = len(successes) + len(skipped) + len(failures)
    print("\n🔔 Final Summary:")
    print(f"🔹 Total processed: {total}")
    print(f"✅ Tagged: {len(successes)}")
    print(f"🚫 Skipped: {len(skipped)}")
    print(f"❌ Failed: {len(failures)}")

# 13) Main
def main():
    resources = discover_resources()
    to_tag, skipped_inspect = identify(resources)
    successes, failures = apply_tags(to_tag)
    export_reports(successes, skipped_inspect, failures)
    display_summary(successes, skipped_inspect, failures)
    extract_validation_errors()  # print out ValidationError ARNs & role names

if __name__ == '__main__':
    main()
