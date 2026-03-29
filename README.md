English | [Español](README.es.md)

# 🔐 Security Log Lake & Traffic Insights on AWS

> **Serverless analytics platform for security and network telemetry** — ingests raw firewall, VPN, and VPC Flow logs, normalizes them through an automated pipeline, and generates actionable insights via SQL analytics and interactive Power BI dashboards.

<br>

## 📊 Dashboards

### Executive Overview
![Executive Overview](docs/screenshots/dashboard-executive.png)
*150K total events across 30 days · 69K blocked · 46.2% block rate · interactive date slicer*

### Network & Threat Analysis
![Network & Threat Analysis](docs/screenshots/dashboard-network.png)
*Severity heatmap by hour · Top 10 source IPs by bytes · Rejected ports breakdown*

### VPN Analysis
![VPN Analysis](docs/screenshots/dashboard-vpn.png)
*6 active users · 30K failed auth attempts · gateway traffic imbalance · deviation from average*

<br>

## 📌 Project Overview

This project simulates a production-grade **Security Operations Center (SOC) data pipeline** built entirely on AWS serverless services. It covers the full lifecycle of security telemetry: from raw log generation, through automated normalization, to SQL-driven analysis and executive-ready Power BI dashboards.

Designed as a **real-world portfolio project**, it demonstrates cloud engineering, data engineering, and security analytics skills in a collaborative, version-controlled environment.

<br>

## 🏗️ Architecture

```
Synthetic Logs
      │
      ▼
 S3 (raw/)           ← Partitioned by source: firewall/, vpn/, vpc-flow/
      │
      │  S3 Event Notification (ObjectCreated)
      ▼
 AWS Lambda           ← Python 3.12 | Normalizes timestamps, IPs, ports, actions
 (security-log-lake-parser)
      │
      ▼
 S3 (processed/)      ← Clean, enriched CSVs ready for querying
      │
      ▼
 Amazon Athena         ← Serverless SQL on S3 | 9 analytical queries
      │
      ▼
 Power BI Dashboards   ← Executive Overview · Network & Threat · VPN Analysis
```

<br>

## ☁️ AWS Services Used

| Service | Role |
|---|---|
| **Amazon S3** | Raw and processed log storage, partitioned by source and date |
| **AWS Lambda** | Event-driven log parser — normalizes, validates, and enriches logs |
| **Amazon Athena** | Serverless SQL analytics directly on S3 (no database server required) |
| **AWS IAM** | Least-privilege roles and policies for Lambda and Athena |
| **Amazon CloudWatch** | Lambda execution monitoring, error logging, and alerting |
| **S3 Event Notifications** | Event-driven trigger: new raw file → automatic Lambda invocation |

<br>

## 📦 Data Pipeline — What It Does

### 1. Log Generation (`ingestion/generate_logs.py`)
Generates **3 types of synthetic security logs** across **30 days** at **5,000 records/day per source** — 450,000 total records:

| Log Type | Fields | Description |
|---|---|---|
| **Firewall** | 15 fields | Action, IPs, ports, protocol, bytes, severity, country |
| **VPN** | 11 fields | Auth events, user, gateway, session duration, status |
| **VPC Flow** | 12 fields | AWS-style network flow records with packet and byte counts |

Includes **realistic threat simulation**: a set of known malicious IPs appear with weighted DENY rates to simulate real attack traffic patterns.

### 2. Lambda Parser (`lambda/parser/handler.py`)
An event-driven Python 3.12 function triggered automatically on every S3 upload. It:
- **Detects** the log type from the S3 key prefix
- **Validates** every field against a per-source schema, logging data quality issues without dropping records
- **Normalizes** timestamps to ISO 8601 format across multiple input formats
- **Standardizes** action and status vocabularies (`ACCEPT` → `ALLOW`, `AUTH_FAIL` → `FAIL`, `REJECT` → `DENY`)
- **Enriches** each record with `_source`, `_processed_at`, and `_has_issues` metadata
- **Writes** clean CSVs to `processed/` for Athena consumption

### 3. Athena Analytics (`athena/queries/`)
External tables defined directly over S3 — no ETL, no infrastructure to provision. Nine analytical queries covering:

| Query | Insight |
|---|---|
| **Q1** | Top 10 IPs with most blocked traffic |
| **Q2** | Allowed vs. blocked traffic per hour |
| **Q3** | Top talkers by total bytes transferred |
| **Q4** | VPN failed authentication attempts by user |
| **Q5** | VPN session duration and bytes by user/gateway |
| **Q6** | VPC rejected traffic by destination port |
| **Q7** | Firewall severity distribution by hour |
| **Q8** | Countries with most denied traffic |
| **Q9** | Daily executive summary — events, blocks, resets, bytes |

### 4. Power BI Dashboards
Three dashboard pages connected to the nine Athena result CSVs:

| Page | Key Visuals |
|---|---|
| **Executive Overview** | KPI cards, hourly traffic trends, top blocked IPs, denied-by-country |
| **Network & Threat Analysis** | Severity-by-hour line chart, top talkers by bytes, rejected ports |
| **VPN Analysis** | Failed auth deviation from average, gateway imbalance, session data |

<br>

## 📁 Repository Structure

```
security-log-lake-aws/
│
├── ingestion/
│   ├── generate_logs.py          # Synthetic log generator (firewall, VPN, VPC Flow)
│   └── sample-logs/              # Generated CSV files (gitignored)
│
├── lambda/
│   └── parser/
│       ├── handler.py            # Lambda function — core normalization logic
│       ├── requirements.txt      # Dependencies (boto3 pre-installed on Lambda)
│       ├── trust-policy.json     # IAM trust policy for Lambda execution role
│       └── s3-notification.json  # S3 event trigger configuration
│
├── athena/
│   └── queries/
│       ├── 01_create_tables.sql  # External table DDL for all 3 log types
│       └── 02_analytics.sql      # 9 analytical queries (Q1–Q9)
│
├── powerbi/
│   └── data/                     # Athena result CSVs for Power BI (q1–q9)
│
├── docs/
│   └── screenshots/              # Dashboard screenshots
│
├── .gitignore
├── LICENSE
└── README.md
```

<br>

## 🔧 Technical Highlights

- **Event-Driven Architecture** — Lambda triggers on `s3:ObjectCreated:*`, zero polling required
- **Schema Validation at Ingest** — every field validated per source; issues flagged and logged, never silently dropped
- **Unified Normalization Layer** — heterogeneous vocabularies across log types resolved at write time, keeping Athena queries clean
- **Serverless SQL** — Athena queries S3 directly via external tables; no database provisioning, pay-per-query pricing
- **Idempotent Pipeline** — re-uploading a raw file safely overwrites the processed output
- **Data Quality Metadata** — every processed record carries `_has_issues` and `_processed_at` for full auditability
- **Least-Privilege IAM** — Lambda execution role scoped to specific resources only

<br>

## 📈 Key Findings from 30 Days of Data

| Metric | Value |
|---|---|
| Total firewall events | 150,000 |
| Overall block rate | 46.2% |
| Top blocked IP | `91.108.4.12` — 9,586 connections blocked |
| Highest-volume denied country | MX — 7,028 events |
| Most attacked port | 6379 (Redis) — 7,648 VPC rejections |
| VPN brute-force leader | `agarcia` — 5,097 failed auth attempts (+2.36% above average) |
| Total VPN failed auth | 30K across all users |
| Highest bandwidth consumer | `91.108.4.12` — 9.6 billion bytes |

<br>

## 🚀 Getting Started

### Prerequisites
- AWS account with access to S3, Lambda, Athena, IAM, CloudWatch
- Python 3.10+
- AWS CLI configured (`aws configure`)
- Power BI Desktop

### 1. Clone the repository
```bash
git clone https://github.com/angel-wm/security-log-lake-aws.git
cd security-log-lake-aws
```

### 2. Generate synthetic logs
```bash
python ingestion/generate_logs.py
# Produces 90 CSV files (30 days × 3 sources) in ingestion/sample-logs/
```

### 3. Upload raw logs to S3
```bash
aws s3 sync ingestion/sample-logs/ s3://YOUR-BUCKET/raw/ --include "*.csv"
```

### 4. Deploy the Lambda parser
```bash
cd lambda/parser
zip function.zip handler.py
aws lambda update-function-code \
  --function-name security-log-lake-parser \
  --zip-file fileb://function.zip
```

### 5. Configure S3 event trigger
```bash
aws s3api put-bucket-notification-configuration \
  --bucket YOUR-BUCKET \
  --notification-configuration file://lambda/parser/s3-notification.json
```

### 6. Run Athena analytics
Execute `athena/queries/01_create_tables.sql` then `02_analytics.sql` in the Athena console.

### 7. Open Power BI
Connect Power BI Desktop to the CSV files in `powerbi/data/`.

> Full deployment guide available in `docs/setup.md`

<br>

## 👥 Team

Built end-to-end by two engineers in a collaborative, PR-based workflow — both contributors accumulated visible commits across all phases.

| | [flaviobox](https://github.com/flaviobox) | [angel-wm](https://github.com/angel-wm) |
|---|---|---|
| Cloud Infrastructure & IAM | ✅ | ✅ |
| S3 Architecture & Data Modeling | ✅ | ✅ |
| Python Lambda Parser | ✅ | ✅ |
| Athena SQL Analytics | ✅ | ✅ |
| Power BI Dashboards | ✅ | ✅ |
| **Domain Lead** | Python, SQL & Analytics | Cloud Infrastructure & Security |

> Both contributors participated in all phases. "Domain Lead" reflects where each brought deeper prior expertise — not exclusive ownership of any deliverable.

**Branching strategy**: `main` ← PR from `dev-angel` / `dev-flavio` — all merges go through pull requests for traceable, auditable contribution history.

<br>

## 🧠 Key Engineering Decisions

- **External Athena tables over Glue Crawlers** — faster iteration, explicit schema control, zero crawler scheduling complexity
- **CSV over Parquet for processed files** — direct Power BI connectivity without additional transformation; Parquet is the natural next optimization at scale
- **Normalization at Lambda, not in Athena VIEWs** — clean schemas at write time reduce repeated transformation cost and eliminate per-query bugs
- **`_has_issues` as STRING, not BOOLEAN** — Athena's CSV reader does not reliably parse boolean values from text files; STRING avoids silent NULLs
- **VPN status normalized to uppercase at ingest** — Athena string matching is case-sensitive; normalizing at Lambda prevents query-time mismatches

<br>

## 🛣️ Roadmap

- [x] Synthetic log generator (firewall, VPN, VPC Flow)
- [x] S3 bucket with `raw/`, `processed/`, `curated/`, `athena-results/` structure
- [x] Lambda parser with schema validation and normalization
- [x] S3 event-driven trigger
- [x] Athena external tables and 9 analytics queries
- [x] Power BI — Executive Overview dashboard
- [x] Power BI — Network & Threat Analysis dashboard
- [x] Power BI — VPN Analysis dashboard
- [x] `docs/setup.md` — full deployment walkthrough
- [x] `docs/data-dictionary.md` — field definitions and value enumerations
- [ ] Partitioned Athena tables by date for query cost optimization
- [ ] Parquet output via Lambda or Glue for production-scale performance

<br>

## 📄 License

[MIT](LICENSE) — free to use, learn from, and build upon.

<br>

---

> *Built to demonstrate real-world cloud data engineering and security analytics skills — not just theory, but a working pipeline from raw bytes to business insight.*
