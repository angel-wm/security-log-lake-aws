English | [Español](README.es.md)

# Security Log Lake & Traffic Insights on AWS

Security Log Lake is a serverless security-analytics pipeline for synthetic firewall, VPN, and VPC Flow telemetry. It generates raw logs, normalizes them with an event-driven AWS Lambda function, queries the processed data with Amazon Athena, and presents the resulting analysis in Power BI.

The repository is a portfolio project built by two engineers to demonstrate cloud data engineering, security analytics, SQL, Python, Power BI, and a pull-request-based collaboration workflow.

## Start here

This project is most useful if you want to inspect or reproduce:

- an event-driven S3 → Lambda → S3 processing path;
- schema-aware normalization across three security-log sources;
- serverless SQL analytics in Athena;
- a Power BI reporting layer built from Athena result CSVs;
- documented deployment, schemas, findings, and engineering tradeoffs.

### Requirements and important limitations

To reproduce the project, you need:

- an AWS account with access to S3, Lambda, Athena, IAM, and CloudWatch;
- Python 3.10+ for local log generation;
- AWS CLI v2 configured with your credentials;
- Power BI Desktop on Windows for the dashboard workflow.

Before reusing the AWS configuration, replace deployment-specific values in:

- `lambda/parser/s3-notification.json` — contains the original Lambda function ARN;
- `athena/queries/01_create_tables.sql` — contains the original project bucket in the table `LOCATION` clauses.

The deployment guide currently uses the managed `AmazonS3FullAccess` policy for a straightforward reproduction path. Treat that as a lab/portfolio setup rather than a least-privilege production IAM baseline.

The repository supports two distinct reproducibility paths:

- **Replay the published run:** use the 90 version-controlled CSVs already in `ingestion/sample-logs/`. This preserves the source dataset behind the committed portfolio evidence and is the right path when comparing your Athena results with the published findings below.
- **Generate a fresh synthetic run:** clear the committed CSVs locally, then run `python ingestion/generate_logs.py`. The generator uses the execution date and does not set a fixed random seed, so the new files, event counts, and findings will differ from the published run.

For the complete deployment path and substitutions, use the [Setup Guide](docs/setup.md).

## Quick Start

1. Clone the repository.

   ```bash
   git clone https://github.com/angel-wm/security-log-lake-aws.git
   cd security-log-lake-aws
   ```

2. Choose the source dataset for this run.

   - To reproduce the published run, keep the 90 committed CSVs in `ingestion/sample-logs/` and do not run the generator.
   - To create a fresh stochastic run, first remove the committed CSVs from your local working tree, then generate a new 30-day dataset:

     ```powershell
     Remove-Item ingestion/sample-logs/*.csv
     python ingestion/generate_logs.py
     ```

     The fresh run writes 90 CSV files: 30 days × 3 sources × 5,000 records per source/day, or 450,000 records total. Because dates and random values are generated at runtime, its findings will not match the published metrics exactly.

3. Follow the [Setup Guide](docs/setup.md) to create the S3 prefixes, upload the selected source dataset, deploy the Lambda parser, configure the S3 trigger, and substitute your AWS identifiers.

4. Run `athena/queries/01_create_tables.sql`, then execute Q1–Q9 from `athena/queries/02_analytics.sql`.

5. Use the resulting CSVs in `powerbi/data/` to refresh the Power BI reporting layer.

If Lambda is not processing uploaded files or another deployment step fails, use the [troubleshooting section](docs/setup.md#10-troubleshooting).

## Architecture

The pipeline has one main flow:

```text
Synthetic log generator
        |
        v
S3 raw/<source>/
        |
        | s3:ObjectCreated:*
        v
AWS Lambda: security-log-lake-parser
        |
        | validate + normalize + enrich
        v
S3 processed/<source>/
        |
        v
Amazon Athena external tables
        |
        | Q1-Q9 result CSVs
        v
Power BI dashboards
```

The essential behavior is also readable directly from the source:

| Component | Source of truth | Responsibility |
| --- | --- | --- |
| Synthetic data | [`ingestion/generate_logs.py`](ingestion/generate_logs.py) | Generates firewall, VPN, and VPC Flow CSVs |
| Normalization | [`lambda/parser/handler.py`](lambda/parser/handler.py) | Detects source, validates fields, normalizes values, adds metadata, writes processed CSVs |
| Event trigger | [`lambda/parser/s3-notification.json`](lambda/parser/s3-notification.json) | Invokes Lambda for CSV objects created under `raw/` |
| Athena schema | [`athena/queries/01_create_tables.sql`](athena/queries/01_create_tables.sql) | Defines the three external tables |
| Analytics | [`athena/queries/02_analytics.sql`](athena/queries/02_analytics.sql) | Implements nine analytical queries |
| Reporting data | [`powerbi/data/`](powerbi/data/) | Stores the committed Athena result CSVs used by Power BI |

## Data pipeline

### Synthetic log generation

`ingestion/generate_logs.py` creates three sources across 30 days at 5,000 records per source/day.

| Source | Raw fields | Examples of modeled behavior |
| --- | ---: | --- |
| Firewall | 15 | actions, IPs, ports, protocol, bytes, severity, policy, countries |
| VPN | 11 | auth events, users, gateways, session duration, transfer volume, failure reason |
| VPC Flow | 12 | interfaces, IPs, ports, protocol numbers, packets, bytes, flow action |

The generator weights a fixed set of source IPs toward blocked traffic to create repeatable threat patterns at the scenario level, while individual generated rows remain stochastic.

### Lambda normalization

The Python 3.12 Lambda function:

- detects `firewall`, `vpn`, or `vpc-flow` from the S3 key prefix;
- checks each row for required fields and logs detected issues;
- normalizes timestamps to ISO 8601;
- maps heterogeneous action/status values into a smaller vocabulary;
- adds `_source`, `_processed_at`, and `_has_issues`;
- writes the processed CSV to the matching `processed/<source>/` prefix.

The current Athena DDL declares `_has_issues` as `BOOLEAN`; the CSV contains the serialized values `True` and `False`.

### Athena analytics

The repository contains nine analytical queries:

| Query | Insight |
| --- | --- |
| Q1 | Top blocked source IPs |
| Q2 | Allowed vs. blocked traffic by hour |
| Q3 | Top talkers by total bytes |
| Q4 | Failed VPN authentication by user |
| Q5 | VPN session duration and bytes by user/gateway |
| Q6 | Rejected VPC traffic by destination port |
| Q7 | Firewall severity distribution by hour |
| Q8 | Countries with the most denied traffic |
| Q9 | Daily executive summary |

Because the Lambda layer maps firewall `DROP` to `DENY`, the Q9 `dropped` column is `0` for the current processed dataset.

## Dashboard evidence

The screenshots below are portfolio evidence from the committed reporting run. The underlying result CSVs are versioned under `powerbi/data/`.

### Executive Overview

![Executive Overview](docs/screenshots/dashboard-executive.png)

The executive page summarizes 150,000 firewall events across 30 days, blocked traffic, hourly patterns, top blocked IPs, and denied traffic by country.

### Network & Threat Analysis

![Network & Threat Analysis](docs/screenshots/dashboard-network.png)

The network page combines severity-by-hour analysis, high-volume source IPs, and rejected VPC destination ports.

### VPN Analysis

![VPN Analysis](docs/screenshots/dashboard-vpn.png)

The VPN page compares failed authentication by user, session activity, gateway traffic, and deviation from the fleet average.

## Published findings

These values come from the committed Athena result CSVs in `powerbi/data/`. A newly generated dataset will differ because the generator is stochastic.

| Metric | Published result |
| --- | ---: |
| Firewall events | 150,000 |
| Blocked firewall events | 69,295 |
| Overall block rate | 46.2% |
| Top blocked source IP | `91.108.4.12` — 9,586 |
| Highest denied-source country | MX — 7,028 |
| Most rejected VPC destination port | 6379 — 7,648 |
| Failed VPN authentication events | 29,878 |
| Highest failed-auth user | `agarcia` — 5,097 |
| Highest-bandwidth source IP | `91.108.4.12` — 9,606,409,766 bytes |

## Documentation map

Choose the document based on what you need to do:

| Goal | Read |
| --- | --- |
| Deploy or reproduce the project | [Setup Guide](docs/setup.md) |
| Look up raw, processed, Athena, query-output, or DAX fields | [Data Dictionary](docs/data-dictionary.md) |
| Inspect synthetic-data behavior | [Log generator](ingestion/generate_logs.py) |
| Inspect validation and normalization logic | [Lambda parser](lambda/parser/handler.py) |
| Inspect table definitions | [Athena DDL](athena/queries/01_create_tables.sql) |
| Inspect analytical logic | [Athena analytics queries](athena/queries/02_analytics.sql) |
| Review dashboard evidence | [Dashboard screenshots](docs/screenshots/) |

## Repository structure

```text
security-log-lake-aws/
├── ingestion/
│   └── generate_logs.py
├── lambda/
│   └── parser/
│       ├── handler.py
│       ├── requirements.txt
│       ├── trust-policy.json
│       └── s3-notification.json
├── athena/
│   └── queries/
│       ├── 01_create_tables.sql
│       └── 02_analytics.sql
├── powerbi/
│   └── data/
├── docs/
│   ├── setup.md
│   ├── data-dictionary.md
│   └── screenshots/
├── README.md
└── README.es.md
```

## Engineering decisions and tradeoffs

- **Athena external tables instead of a database server:** processed CSVs remain in S3 and are queried in place.
- **Explicit table DDL instead of Glue Crawlers:** the schema is visible and version controlled.
- **CSV instead of Parquet:** the current portfolio workflow favors transparent files and direct Power BI use; Parquet remains a roadmap optimization.
- **Normalization in Lambda:** action/status vocabulary is standardized once before analytics instead of repeatedly inside every query.
- **Issue metadata in every processed row:** `_has_issues` preserves row-level visibility into missing required fields.
- **Deployment configuration is not fully portable as checked in:** the original S3 bucket and Lambda ARN must be replaced before reproducing the environment.
- **IAM in the setup guide prioritizes reproducibility:** the documented S3 full-access policy should be narrowed for production use.

## Team and workflow

Built end-to-end by two engineers. Both contributors participated across the project; the domain lead indicates deeper prior experience rather than exclusive ownership.

| Contributor | Domain lead |
| --- | --- |
| [flaviobox](https://github.com/flaviobox) | Python, SQL, and analytics |
| [angel-wm](https://github.com/angel-wm) | Cloud infrastructure and security |

The project used `dev-angel` and `dev-flavio` working branches with pull requests into `main` for traceable collaboration.

## Roadmap

Completed:

- synthetic firewall, VPN, and VPC Flow generation;
- S3 raw/processed architecture;
- Lambda normalization and event trigger;
- Athena external tables and Q1–Q9 analytics;
- three Power BI dashboard pages;
- deployment and data-dictionary documentation.

Future optimizations:

- partition Athena tables by date;
- emit Parquet through Lambda or Glue for larger-scale workloads.

## License

[MIT](LICENSE) — free to use, learn from, and build upon.
