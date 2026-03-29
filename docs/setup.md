# 🛠️ Setup Guide — Security Log Lake on AWS

Step-by-step deployment guide for replicating this project from scratch. All commands are written for **PowerShell on Windows**. The AWS CLI must be installed and configured before starting Part 3.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [GitHub — Repo & Branch Structure](#2-github--repo--branch-structure)
3. [AWS CLI — Configuration](#3-aws-cli--configuration)
4. [S3 — Bucket Structure](#4-s3--bucket-structure)
5. [Log Generation & Upload](#5-log-generation--upload)
6. [Lambda — Parser Deployment](#6-lambda--parser-deployment)
7. [Athena — Tables & Analytics](#7-athena--tables--analytics)
8. [Power BI — Download Results](#8-power-bi--download-results)
9. [Git Workflow](#9-git-workflow)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.10+ | Must be on PATH |
| AWS CLI | v2 | [Install guide](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) |
| Git | Any | |
| Power BI Desktop | Latest | Windows only |
| AWS Account | — | IAM user with programmatic access |

Verify AWS CLI is installed:
```powershell
aws --version
```

---

## 2. GitHub — Repo & Branch Structure

### Person 1 (Angel) — Initial setup
```powershell
# Clone the repo
git clone https://github.com/angel-wm/security-log-lake-aws.git
cd security-log-lake-aws

# Create folder structure
mkdir -p ingestion/sample-logs
mkdir -p lambda/parser
mkdir -p athena/queries
mkdir -p docs
mkdir -p powerbi/data

# Create .gitkeep placeholders so empty folders are tracked
New-Item ingestion/sample-logs/.gitkeep -Force
New-Item lambda/parser/.gitkeep -Force
New-Item athena/queries/.gitkeep -Force
New-Item docs/.gitkeep -Force
New-Item powerbi/.gitkeep -Force

# First commit
git add .
git commit -m "feat: initial project structure and README"
git push origin main
```

### Both contributors — Create working branches
```powershell
# Person 1 (Angel)
git checkout -b dev-angel
git push origin dev-angel

# Person 2 (Flavio) — after cloning
git clone https://github.com/angel-wm/security-log-lake-aws.git
cd security-log-lake-aws
git checkout -b dev-flavio
git push origin dev-flavio
```

---

## 3. AWS CLI — Configuration

Each contributor configures their own machine with their IAM user credentials.

```powershell
aws configure
# AWS Access Key ID:     [your key]
# AWS Secret Access Key: [your secret]
# Default region name:   us-east-1
# Default output format: json

# Verify identity
aws sts get-caller-identity
```

---

## 4. S3 — Bucket Structure

> **Note:** S3 has no real directories — folders are simulated via key prefixes. After any recursive deletion, folder placeholders must be explicitly recreated with `put-object`.

Set the bucket variable once and reuse it across the session:
```powershell
$BUCKET = "YOUR-BUCKET-NAME"
```

Create all folder prefixes:
```powershell
aws s3api put-object --bucket $BUCKET --key "raw/firewall/"
aws s3api put-object --bucket $BUCKET --key "raw/vpn/"
aws s3api put-object --bucket $BUCKET --key "raw/vpc-flow/"
aws s3api put-object --bucket $BUCKET --key "processed/firewall/"
aws s3api put-object --bucket $BUCKET --key "processed/vpn/"
aws s3api put-object --bucket $BUCKET --key "processed/vpc-flow/"
aws s3api put-object --bucket $BUCKET --key "curated/"
aws s3api put-object --bucket $BUCKET --key "athena-results/"

# Verify
aws s3 ls s3://$BUCKET --recursive
```

Configure Athena workgroup output location:
```powershell
aws athena update-work-group `
  --work-group primary `
  --configuration-updates "ResultConfigurationUpdates={OutputLocation=s3://$BUCKET/athena-results/}"

# Verify
aws athena get-work-group --work-group primary
```

---

## 5. Log Generation & Upload

### Generate synthetic logs

Always run from the **repo root** — not from inside `ingestion/`:
```powershell
# From repo root:
python ingestion/generate_logs.py
```

This produces 90 CSV files in `ingestion/sample-logs/` (30 days × 3 log types).

### Upload to S3

Route each log type to its correct S3 prefix. Lambda triggers automatically on upload.

```powershell
aws s3 cp ingestion/sample-logs/ s3://$BUCKET/raw/firewall/ `
  --recursive --exclude "*" --include "firewall_*.csv"

aws s3 cp ingestion/sample-logs/ s3://$BUCKET/raw/vpn/ `
  --recursive --exclude "*" --include "vpn_*.csv"

aws s3 cp ingestion/sample-logs/ s3://$BUCKET/raw/vpc-flow/ `
  --recursive --exclude "*" --include "vpc-flow_*.csv"

# Verify Lambda processed the files
aws s3 ls s3://$BUCKET/processed/firewall/
aws s3 ls s3://$BUCKET/processed/vpn/
aws s3 ls s3://$BUCKET/processed/vpc-flow/
```

### Re-running the pipeline (if regenerating data)

> ⚠️ **Important:** Delete subfolder by subfolder — never use `aws s3 rm s3://$BUCKET/raw/ --recursive`. That deletes the folder placeholders too, breaking the structure.

```powershell
# 1. Delete local CSVs
Remove-Item ingestion/sample-logs/*.csv

# 2. Regenerate
python ingestion/generate_logs.py

# 3. Clear S3 contents — subfolder by subfolder
aws s3 rm s3://$BUCKET/raw/firewall/ --recursive
aws s3 rm s3://$BUCKET/raw/vpn/ --recursive
aws s3 rm s3://$BUCKET/raw/vpc-flow/ --recursive
aws s3 rm s3://$BUCKET/processed/firewall/ --recursive
aws s3 rm s3://$BUCKET/processed/vpn/ --recursive
aws s3 rm s3://$BUCKET/processed/vpc-flow/ --recursive

# 4. Recreate folder placeholders
aws s3api put-object --bucket $BUCKET --key "raw/firewall/"
aws s3api put-object --bucket $BUCKET --key "raw/vpn/"
aws s3api put-object --bucket $BUCKET --key "raw/vpc-flow/"
aws s3api put-object --bucket $BUCKET --key "processed/firewall/"
aws s3api put-object --bucket $BUCKET --key "processed/vpn/"
aws s3api put-object --bucket $BUCKET --key "processed/vpc-flow/"

# 5. Re-upload
aws s3 cp ingestion/sample-logs/ s3://$BUCKET/raw/firewall/ `
  --recursive --exclude "*" --include "firewall_*.csv"
aws s3 cp ingestion/sample-logs/ s3://$BUCKET/raw/vpn/ `
  --recursive --exclude "*" --include "vpn_*.csv"
aws s3 cp ingestion/sample-logs/ s3://$BUCKET/raw/vpc-flow/ `
  --recursive --exclude "*" --include "vpc-flow_*.csv"

# 6. Verify
aws s3 ls s3://$BUCKET/processed/firewall/
```

---

## 6. Lambda — Parser Deployment

### Create IAM role
```powershell
aws iam create-role `
  --role-name security-log-lake-lambda-role `
  --assume-role-policy-document file://lambda/parser/trust-policy.json

# Attach required policies
aws iam attach-role-policy `
  --role-name security-log-lake-lambda-role `
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy `
  --role-name security-log-lake-lambda-role `
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# Verify
aws iam get-role --role-name security-log-lake-lambda-role
```

### Package and deploy the function
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

# Verify
aws lambda get-function --function-name security-log-lake-parser
```

### Configure S3 event trigger
```powershell
# Grant S3 permission to invoke Lambda
aws lambda add-permission `
  --function-name security-log-lake-parser `
  --statement-id s3-trigger `
  --action lambda:InvokeFunction `
  --principal s3.amazonaws.com `
  --source-arn arn:aws:s3:::$BUCKET

# Apply the notification configuration
aws s3api put-bucket-notification-configuration `
  --bucket $BUCKET `
  --notification-configuration file://lambda/parser/s3-notification.json
```

### Update function code (after changes to handler.py)
```powershell
cd lambda/parser
Compress-Archive -Path handler.py -DestinationPath function.zip -Force

aws lambda update-function-code `
  --function-name security-log-lake-parser `
  --zip-file fileb://function.zip

cd ../..
```

### Monitor execution
```powershell
# Tail CloudWatch logs in real time
aws logs tail /aws/lambda/security-log-lake-parser --follow
```

---

## 7. Athena — Tables & Analytics

Athena queries are executed in the **AWS Console** (Athena Query Editor), not via CLI.

### Step 1 — Create the database and external tables

Run the full contents of `athena/queries/01_create_tables.sql` in the Athena console. This creates:
- Database: `security_log_lake`
- Tables: `firewall_logs`, `vpn_logs`, `vpc_flow_logs`

All tables are external and point to the `processed/` prefix in S3. No data is moved.

### Step 2 — Run analytical queries

Run each query block in `athena/queries/02_analytics.sql` individually (Q1 through Q9). Results are saved automatically to `s3://YOUR-BUCKET/athena-results/`.

> Each query execution generates a UUID-named CSV file in `athena-results/`. Download and rename these as described in Part 8.

### Useful CLI checks
```powershell
# Verify Athena workgroup output is configured
aws athena get-work-group --work-group primary

# List result files in S3
aws s3 ls s3://$BUCKET/athena-results/ --recursive
```

---

## 8. Power BI — Download Results

After running all 9 queries in Athena, download the result CSVs and rename them.

### Identify which UUID corresponds to which query

```powershell
cd powerbi/data

# Print the header row of each CSV to identify it
Get-ChildItem -Filter "*.csv" | ForEach-Object {
    $header = Get-Content $_.FullName -First 1
    Write-Host "$($_.Name) -> $header"
}
```

Match headers to queries:

| Header columns | Rename to |
|---|---|
| `src_ip, blocked_count` | `q1_top_blocked_ips.csv` |
| `hour, action, total` | `q2_traffic_by_hour.csv` |
| `src_ip, total_bytes` | `q3_top_talkers.csv` |
| `user, failed_attempts` | `q4_vpn_failed_auth.csv` |
| `user, vpn_gateway, total_session_sec, total_bytes` | `q5_vpn_sessions.csv` |
| `dst_port, rejected_count` | `q6_vpc_rejected_ports.csv` |
| `hour, severity, total` | `q7_severity_by_hour.csv` |
| `country_src, denied_count` | `q8_denied_by_country.csv` |
| `day, total_events, allowed, blocked, dropped, reset_count, total_bytes` | `q9_daily_summary.csv` |

### Rename files
```powershell
# Run from powerbi/data/ — replace <UUID> with the actual filename
Rename-Item "<UUID>.csv" "q1_top_blocked_ips.csv"
Rename-Item "<UUID>.csv" "q2_traffic_by_hour.csv"
Rename-Item "<UUID>.csv" "q3_top_talkers.csv"
Rename-Item "<UUID>.csv" "q4_vpn_failed_auth.csv"
Rename-Item "<UUID>.csv" "q5_vpn_sessions.csv"
Rename-Item "<UUID>.csv" "q6_vpc_rejected_ports.csv"
Rename-Item "<UUID>.csv" "q7_severity_by_hour.csv"
Rename-Item "<UUID>.csv" "q8_denied_by_country.csv"
Rename-Item "<UUID>.csv" "q9_daily_summary.csv"

# Remove Athena metadata files
Remove-Item "*.metadata"
Remove-Item "*.txt"

# Remove any leftover UUID CSVs (keep only q1-q9)
Get-ChildItem -Filter "*.csv" | Where-Object { $_.Name -notmatch "^q[1-9]_" } | Remove-Item
```

### Refresh in Power BI Desktop
Open the `.pbix` file → Home → Refresh. All 9 tables update from the renamed CSVs.

---

## 9. Git Workflow

### Daily commit flow — Angel (dev-angel)
```powershell
git checkout dev-angel
git add .
git commit -m "feat: describe what changed"
git push origin dev-angel
```

### Daily commit flow — Flavio (dev-flavio)
```powershell
git checkout dev-flavio
git -c user.email="Flavio.Castro.B@protonmail.com" -c user.name="flaviobox" commit -m "feat: describe what changed"
git push origin dev-flavio
```

### Sync a working branch with main (after a PR is merged)
```powershell
git checkout main
git pull origin main
git checkout dev-angel      # or dev-flavio
git merge main
git push origin dev-angel   # or dev-flavio
```

### Pull Requests
Both working branches merge to `main` via PR on GitHub UI, not via direct push. This ensures a traceable, auditable contribution history for both contributors.

---

## 10. Troubleshooting

### Git identity not being picked up on Windows

`git config --global` may not be honored in some Windows environments. Reliable workarounds:

```powershell
# Option A — set at repo level (no --global)
git config user.email "your@email.com"
git config user.name "your-username"

# Option B — pass identity directly at commit time
git -c user.email="your@email.com" -c user.name="your-username" commit -m "message"
```

### S3 folder placeholders disappear after deletion

S3 has no real directories. Running `aws s3 rm s3://BUCKET/raw/ --recursive` removes the folder placeholders along with the files. Always delete **subfolder by subfolder** and then recreate the placeholders:

```powershell
# Correct approach — delete contents only
aws s3 rm s3://$BUCKET/raw/firewall/ --recursive
# Then recreate the placeholder
aws s3api put-object --bucket $BUCKET --key "raw/firewall/"
```

### Nested ingestion folder created by mistake

Happens when `generate_logs.py` is run from inside the `ingestion/` directory. The script uses `OUTPUT_DIR = "ingestion/sample-logs"` as a relative path, creating `ingestion/ingestion/sample-logs/`.

**Fix:** Always run from the repo root:
```powershell
# Correct
python ingestion/generate_logs.py

# Move any misplaced files and remove the duplicate folder
Move-Item ingestion/ingestion/sample-logs/*.csv ingestion/sample-logs/
Remove-Item ingestion/ingestion -Recurse
```

### Power BI schema refresh error after adding columns

If a query result has new or different columns, Power BI throws a refresh error due to a hardcoded "Changed Type" step in Power Query. Fix: open Power Query Editor → find the "Changed Type" step → delete it → close and apply.

### Lambda not processing uploaded files

1. Verify the S3 event notification is correctly applied:
```powershell
aws s3api get-bucket-notification-configuration --bucket $BUCKET
```
2. Verify Lambda has permission to be invoked by S3:
```powershell
aws lambda get-policy --function-name security-log-lake-parser
```
3. Check CloudWatch logs for execution errors:
```powershell
aws logs tail /aws/lambda/security-log-lake-parser --follow
```

---

## Quick Reference

| Resource | Value |
|---|---|
| AWS Region | `us-east-1` |
| S3 Bucket | `YOUR-BUCKET-NAME` |
| Lambda function | `security-log-lake-parser` |
| Lambda IAM role | `security-log-lake-lambda-role` |
| Athena database | `security_log_lake` |
| Athena workgroup | `primary` |
| GitHub repo | `https://github.com/angel-wm/security-log-lake-aws` |
| Working branches | `dev-angel`, `dev-flavio` |
| IAM users | `angel-admin`, `flavio-admin` |
