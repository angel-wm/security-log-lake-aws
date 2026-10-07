# Setup Guide — Security Log Lake on AWS

This guide reproduces the repository's AWS pipeline from synthetic log generation through Athena results for Power BI.

Commands are written for **PowerShell on Windows**. Run repository-relative commands from the repository root unless a step explicitly changes directories.

## Before you start

### Prerequisites

| Tool or access | Requirement |
| --- | --- |
| Python | 3.10+ on PATH |
| AWS CLI | v2, configured locally |
| Git | Any current version |
| Power BI Desktop | Windows |
| AWS account | Access to S3, Lambda, Athena, IAM, and CloudWatch |

Verify the AWS CLI and active identity:

```powershell
aws --version
aws sts get-caller-identity
```

### Values you must replace

Two checked-in files contain identifiers from the original project environment:

1. `lambda/parser/s3-notification.json` contains the original Lambda function ARN.
2. `athena/queries/01_create_tables.sql` contains the original S3 bucket in each `LOCATION` clause.

Replace those values with identifiers from your AWS account before applying the trigger or creating the Athena tables.

Throughout this guide, set your bucket once:

```powershell
$BUCKET = "YOUR-BUCKET-NAME"
```

> The IAM commands below use `AmazonS3FullAccess` because that is the repository's documented reproduction path. For a production deployment, replace it with a policy scoped to the required bucket and operations.

## Deployment path

1. [Clone and configure AWS](#1-clone-and-configure-aws)
2. [Create the S3 structure](#2-create-the-s3-structure)
3. [Generate and upload logs](#3-generate-and-upload-logs)
4. [Deploy the Lambda parser](#4-deploy-the-lambda-parser)
5. [Configure the S3 trigger](#5-configure-the-s3-trigger)
6. [Create Athena tables and run analytics](#6-create-athena-tables-and-run-analytics)
7. [Prepare Power BI result files](#7-prepare-power-bi-result-files)
8. [Re-run the pipeline](#8-re-run-the-pipeline)
9. [Collaboration workflow](#9-collaboration-workflow)
10. [Troubleshooting](#10-troubleshooting)
11. [Quick reference](#11-quick-reference)

## 1. Clone and configure AWS

Clone the repository:

```powershell
git clone https://github.com/angel-wm/security-log-lake-aws.git
cd security-log-lake-aws
```

Configure the AWS CLI if needed:

```powershell
aws configure
# AWS Access Key ID:     [your key]
# AWS Secret Access Key: [your secret]
# Default region name:   us-east-1
# Default output format: json
```

Verify:

```powershell
aws sts get-caller-identity
```

## 2. Create the S3 structure

S3 prefixes are used as the project folder structure.

Create the required prefixes:

```powershell
aws s3api put-object --bucket $BUCKET --key "raw/firewall/"
aws s3api put-object --bucket $BUCKET --key "raw/vpn/"
aws s3api put-object --bucket $BUCKET --key "raw/vpc-flow/"
aws s3api put-object --bucket $BUCKET --key "processed/firewall/"
aws s3api put-object --bucket $BUCKET --key "processed/vpn/"
aws s3api put-object --bucket $BUCKET --key "processed/vpc-flow/"
aws s3api put-object --bucket $BUCKET --key "curated/"
aws s3api put-object --bucket $BUCKET --key "athena-results/"
```

Configure the Athena workgroup output:

```powershell
aws athena update-work-group `
  --work-group primary `
  --configuration-updates "ResultConfigurationUpdates={OutputLocation=s3://$BUCKET/athena-results/}"
```

Verify both:

```powershell
aws s3 ls s3://$BUCKET --recursive
aws athena get-work-group --work-group primary
```

## 3. Generate and upload logs

Run the generator from the repository root:

```powershell
python ingestion/generate_logs.py
```

Expected result:

- 90 CSV files in `ingestion/sample-logs/`;
- 30 days;
- 3 sources per day;
- 5,000 records per source/day;
- 450,000 total generated records.

Upload each source to the matching raw prefix:

```powershell
aws s3 cp ingestion/sample-logs/ s3://$BUCKET/raw/firewall/ `
  --recursive --exclude "*" --include "firewall_*.csv"

aws s3 cp ingestion/sample-logs/ s3://$BUCKET/raw/vpn/ `
  --recursive --exclude "*" --include "vpn_*.csv"

aws s3 cp ingestion/sample-logs/ s3://$BUCKET/raw/vpc-flow/ `
  --recursive --exclude "*" --include "vpc-flow_*.csv"
```

If the Lambda trigger is already configured, processed files should begin appearing under `processed/`. During an initial deployment, continue with the Lambda steps first.

## 4. Deploy the Lambda parser

### Create the execution role

```powershell
aws iam create-role `
  --role-name security-log-lake-lambda-role `
  --assume-role-policy-document file://lambda/parser/trust-policy.json

aws iam attach-role-policy `
  --role-name security-log-lake-lambda-role `
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy `
  --role-name security-log-lake-lambda-role `
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

Verify:

```powershell
aws iam get-role --role-name security-log-lake-lambda-role
```

### Package and create the function

```powershell
cd lambda/parser
Compress-Archive -Path handler.py -DestinationPath function.zip -Force

$ROLE_ARN = "arn:aws:iam::YOUR-ACCOUNT-ID:role/security-log-lake-lambda-role"

aws lambda create-function `
  --function-name security-log-lake-parser `
  --runtime python3.12 `
  --role $ROLE_ARN `
  --handler handler.lambda_handler `
  --zip-file fileb://function.zip `
  --timeout 60 `
  --memory-size 256 `
  --description "Parses and normalizes raw firewall/VPN/VPC Flow logs"

cd ../..
```

Verify:

```powershell
aws lambda get-function --function-name security-log-lake-parser
```

To update the function after changing `handler.py`:

```powershell
cd lambda/parser
Compress-Archive -Path handler.py -DestinationPath function.zip -Force

aws lambda update-function-code `
  --function-name security-log-lake-parser `
  --zip-file fileb://function.zip

cd ../..
```

## 5. Configure the S3 trigger

First, replace the `LambdaFunctionArn` in `lambda/parser/s3-notification.json` with the ARN of the function created in your AWS account.

Grant S3 permission to invoke Lambda:

```powershell
aws lambda add-permission `
  --function-name security-log-lake-parser `
  --statement-id s3-trigger `
  --action lambda:InvokeFunction `
  --principal s3.amazonaws.com `
  --source-arn arn:aws:s3:::$BUCKET
```

Apply the repository notification configuration:

```powershell
aws s3api put-bucket-notification-configuration `
  --bucket $BUCKET `
  --notification-configuration file://lambda/parser/s3-notification.json
```

Verify the notification and monitor execution:

```powershell
aws s3api get-bucket-notification-configuration --bucket $BUCKET
aws logs tail /aws/lambda/security-log-lake-parser --follow
```

Upload or re-upload a test CSV under the matching `raw/<source>/` prefix and verify that a corresponding object appears under `processed/<source>/`.

## 6. Create Athena tables and run analytics

### Update table locations

Before running the DDL, edit all three `LOCATION` clauses in:

`athena/queries/01_create_tables.sql`

Replace the original project bucket with your bucket:

```text
s3://YOUR-BUCKET-NAME/processed/firewall/
s3://YOUR-BUCKET-NAME/processed/vpn/
s3://YOUR-BUCKET-NAME/processed/vpc-flow/
```

### Create external tables

Run the full contents of `athena/queries/01_create_tables.sql` in the Athena Query Editor.

Expected objects:

- database: `security_log_lake`;
- tables: `firewall_logs`, `vpn_logs`, `vpc_flow_logs`.

### Run Q1–Q9

Run each query block from `athena/queries/02_analytics.sql` separately.

Athena writes result files to:

```text
s3://YOUR-BUCKET-NAME/athena-results/
```

Useful check:

```powershell
aws s3 ls s3://$BUCKET/athena-results/ --recursive
```

## 7. Prepare Power BI result files

Download the nine Athena result CSVs to `powerbi/data/`.

Use the header row to identify which result belongs to which query:

| Header columns | Rename to |
| --- | --- |
| `src_ip, blocked_count` | `q1_top_blocked_ips.csv` |
| `hour, action, total` | `q2_traffic_by_hour.csv` |
| `src_ip, total_bytes` | `q3_top_talkers.csv` |
| `user, failed_attempts` | `q4_vpn_failed_auth.csv` |
| `user, vpn_gateway, total_session_sec, total_bytes` | `q5_vpn_sessions.csv` |
| `dst_port, rejected_count` | `q6_vpc_rejected_ports.csv` |
| `hour, severity, total` | `q7_severity_by_hour.csv` |
| `country_src, denied_count` | `q8_denied_by_country.csv` |
| `day, total_events, allowed, blocked, dropped, reset_count, total_bytes` | `q9_daily_summary.csv` |

To print the first row of each local CSV:

```powershell
cd powerbi/data

Get-ChildItem -Filter "*.csv" | ForEach-Object {
    $header = Get-Content $_.FullName -First 1
    Write-Host "$($_.Name) -> $header"
}
```

Rename the files to the Q1–Q9 names above, then refresh the Power BI model that consumes them.

## 8. Re-run the pipeline

The generator uses a relative output path and no fixed random seed. Always run it from the repository root.

To regenerate data cleanly:

1. Remove the generated local CSVs.

   ```powershell
   Remove-Item ingestion/sample-logs/*.csv
   ```

2. Generate a new dataset.

   ```powershell
   python ingestion/generate_logs.py
   ```

3. Clear source-specific raw and processed objects.

   ```powershell
   aws s3 rm s3://$BUCKET/raw/firewall/ --recursive
   aws s3 rm s3://$BUCKET/raw/vpn/ --recursive
   aws s3 rm s3://$BUCKET/raw/vpc-flow/ --recursive
   aws s3 rm s3://$BUCKET/processed/firewall/ --recursive
   aws s3 rm s3://$BUCKET/processed/vpn/ --recursive
   aws s3 rm s3://$BUCKET/processed/vpc-flow/ --recursive
   ```

4. Recreate the source prefixes.

   ```powershell
   aws s3api put-object --bucket $BUCKET --key "raw/firewall/"
   aws s3api put-object --bucket $BUCKET --key "raw/vpn/"
   aws s3api put-object --bucket $BUCKET --key "raw/vpc-flow/"
   aws s3api put-object --bucket $BUCKET --key "processed/firewall/"
   aws s3api put-object --bucket $BUCKET --key "processed/vpn/"
   aws s3api put-object --bucket $BUCKET --key "processed/vpc-flow/"
   ```

5. Upload each source again using the commands from [Generate and upload logs](#3-generate-and-upload-logs).

6. Verify that processed objects are recreated and rerun the Athena queries.

Do not compare regenerated findings to the committed portfolio metrics as though they should match exactly; the generated events are stochastic.

## 9. Collaboration workflow

The project historically used two working branches:

- `dev-angel`;
- `dev-flavio`.

Both merged into `main` through Pull Requests.

Typical branch refresh:

```powershell
git checkout main
git pull origin main
git checkout dev-angel      # or dev-flavio
git merge main
git push origin dev-angel   # or dev-flavio
```

This section documents the project's collaboration history; it is not required to deploy the pipeline.

## 10. Troubleshooting

### Lambda does not process an uploaded CSV

**Symptom:** a CSV exists under `raw/<source>/`, but no corresponding object appears under `processed/<source>/`.

**Likely causes:**

- the S3 notification was not applied;
- the notification still contains the original Lambda ARN;
- S3 lacks invoke permission for the function;
- the object key does not match the `raw/` prefix and `.csv` suffix filter;
- the Lambda execution failed.

**Resolution:**

1. Inspect the notification:

   ```powershell
   aws s3api get-bucket-notification-configuration --bucket $BUCKET
   ```

2. Inspect Lambda resource policy:

   ```powershell
   aws lambda get-policy --function-name security-log-lake-parser
   ```

3. Tail CloudWatch logs:

   ```powershell
   aws logs tail /aws/lambda/security-log-lake-parser --follow
   ```

4. Correct the ARN, permissions, object path, or runtime error and upload a CSV again.

**Verify:** a processed object appears under the matching `processed/<source>/` prefix.

### Athena tables return no data or point to the wrong bucket

**Symptom:** the tables exist, but queries return no rows or reference another environment.

**Likely cause:** the `LOCATION` values in `athena/queries/01_create_tables.sql` still point to the original project bucket.

**Resolution:** replace all three `LOCATION` values with your processed S3 prefixes and recreate the external tables if necessary.

**Verify:** query a table and confirm rows from your bucket are returned.

### S3 prefixes disappear after recursive deletion

**Symptom:** expected source prefixes no longer appear after cleanup.

**Likely cause:** S3 has no real directories; recursive deletion removed the placeholder objects.

**Resolution:** recreate the required prefixes with `put-object`.

**Verify:** list the bucket recursively and confirm the expected prefix objects exist.

### A nested `ingestion/ingestion/sample-logs/` directory appears

**Symptom:** generated CSVs are written under a duplicated `ingestion/ingestion/` path.

**Likely cause:** `generate_logs.py` was run from inside `ingestion/`; its output path is relative to the current working directory.

**Resolution:** return to the repository root, move or remove the misplaced files, and rerun:

```powershell
python ingestion/generate_logs.py
```

**Verify:** CSVs appear directly under `ingestion/sample-logs/`.

### Power BI refresh fails after a result schema changes

**Symptom:** Power BI reports a schema/type error after a query result changes columns.

**Likely cause:** an existing Power Query `Changed Type` step references the prior schema.

**Resolution:** inspect the affected query in Power Query Editor and update or remove the stale type step as appropriate.

**Verify:** refresh completes using the current Q1–Q9 CSV schema.

### Git uses the wrong identity on Windows

**Symptom:** commits use an unintended author identity.

**Likely cause:** the expected global Git identity is not active in the current environment.

**Resolution:** set repository-level identity or pass it explicitly at commit time.

```powershell
git config user.email "your@email.com"
git config user.name "your-username"
```

**Verify:** run `git config user.email` and `git config user.name` before committing.

## 11. Quick reference

| Resource | Value |
| --- | --- |
| AWS Region used by the project | `us-east-1` |
| S3 bucket | `YOUR-BUCKET-NAME` |
| Lambda function | `security-log-lake-parser` |
| Lambda IAM role | `security-log-lake-lambda-role` |
| Athena database | `security_log_lake` |
| Athena workgroup | `primary` |
| Repository | `https://github.com/angel-wm/security-log-lake-aws` |
| Historical working branches | `dev-angel`, `dev-flavio` |
