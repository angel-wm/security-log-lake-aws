# 🔐 Security Log Lake & Traffic Insights on AWS

Serverless analytics platform for security and network telemetry.  
Receives raw firewall/VPN/VPC logs, normalizes them, and generates actionable insights on traffic patterns, blocks, failed authentications, and operational behavior.

---

## 🏗️ Architecture

Raw logs → **S3 (raw/)** → **Lambda (parser)** → **S3 (processed/)** → **Athena (SQL)** → **Power BI (dashboards)**

## ☁️ AWS Services
- **S3** — Raw and processed log storage, partitioned by date/source
- **Lambda** — Serverless parser: normalizes timestamps, IPs, ports, actions, severity
- **Athena** — Serverless SQL analytics directly on S3
- **IAM** — Least-privilege roles and policies
- **CloudWatch** — Lambda monitoring and alerting
- **EventBridge** — S3 event-driven trigger orchestration

## 📁 Repository Structure
```
security-log-lake-aws/
├── ingestion/          # Sample logs and ingestion scripts
│   └── sample-logs/    # Synthetic firewall/VPN/VPC log files
├── lambda/             # Lambda function code
│   └── parser/         # Log normalization logic
├── athena/             # SQL queries and table definitions
│   └── queries/        # Analytical queries (top talkers, denied traffic, etc.)
├── powerbi/            # Power BI report files and connection docs
└── docs/               # Architecture decisions, data dictionary, data quality notes
```

## 👥 Team

Built collaboratively end-to-end by two engineers with complementary backgrounds.

| | flaviobox(https://github.com/flaviobox) | angel-wm(https://github.com/angel-wm) |
|---|---|---|
| Cloud Infrastructure & IAM | ✅ | ✅ |
| S3 Architecture & Data Modeling | ✅ | ✅ |
| Python Parser (Lambda) | ✅ | ✅ |
| Athena SQL Analytics | ✅ | ✅ |
| Power BI Dashboards | ✅ | ✅ |
| **Domain Lead** | Network & Security | Data & Analytics |

> Both contributors participated in all phases of the project.  
> "Domain Lead" reflects where each brought deeper prior expertise, not ownership of the deliverable.

## 🚀 Getting Started
> Setup guide coming in `docs/setup.md`

## 📄 License
MIT
