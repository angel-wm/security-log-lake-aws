# 📖 Data Dictionary — Security Log Lake

Complete reference for all fields, tables, and calculated measures used across the pipeline: raw logs → Lambda normalization → Athena tables → Power BI.

---

## Table of Contents

1. [Raw Log Schemas](#1-raw-log-schemas)
2. [Processed Log Schemas](#2-processed-log-schemas-post-lambda)
3. [Athena Analytics Tables](#3-athena-analytics-tables)
4. [Athena Query Outputs](#4-athena-query-outputs-power-bi-sources)
5. [Power BI DAX Measures](#5-power-bi-dax-measures)
6. [Normalized Value Enumerations](#6-normalized-value-enumerations)

---

## 1. Raw Log Schemas

These are the fields as written by `generate_logs.py` and stored in `s3://YOUR-BUCKET/raw/`.

### 1.1 Firewall Logs (`raw/firewall/`)

| Field | Type | Description | Example Values |
|---|---|---|---|
| `timestamp` | STRING | Event datetime in `YYYY-MM-DD HH:MM:SS` format | `2026-03-15 14:32:07` |
| `device_id` | STRING | Firewall device identifier | `FGT-01`, `FGT-02`, `FGT-03` |
| `action` | STRING | Firewall decision (raw, pre-normalization) | `ALLOW`, `DENY`, `DROP`, `RESET` |
| `src_ip` | STRING | Source IP address | `91.108.4.12`, `10.0.1.10` |
| `dst_ip` | STRING | Destination IP address | `192.168.1.50` |
| `src_port` | INT | Source port number | `1024`–`65535` |
| `dst_port` | INT | Destination port number | `80`, `443`, `22`, `3389`, `53`, `8080`, `445` |
| `protocol` | STRING | Network protocol | `TCP`, `UDP`, `ICMP` |
| `bytes_sent` | BIGINT | Bytes sent by source | `100`–`500000` |
| `bytes_received` | BIGINT | Bytes received by source | `100`–`1000000` |
| `duration_sec` | DOUBLE | Connection duration in seconds | `1`–`3600` |
| `severity` | STRING | Event severity level | `low`, `medium`, `high`, `critical` |
| `policy_name` | STRING | Firewall policy matched | `internet-access`, `internal-only`, `dmz-policy`, `vpn-split` |
| `country_src` | STRING | ISO 3166-1 alpha-2 country code of source | `US`, `CN`, `RU`, `BR`, `DE`, `PA`, `MX`, `IN`, `GB`, `KP` |
| `country_dst` | STRING | ISO 3166-1 alpha-2 country code of destination | Same as `country_src` |

### 1.2 VPN Logs (`raw/vpn/`)

| Field | Type | Description | Example Values |
|---|---|---|---|
| `timestamp` | STRING | Event datetime in `YYYY-MM-DD HH:MM:SS` format | `2026-03-15 09:14:22` |
| `device_id` | STRING | Firewall/VPN device identifier | `FGT-01`, `FGT-02`, `FGT-03` |
| `event_type` | STRING | Type of VPN event | `AUTH_SUCCESS`, `AUTH_FAIL`, `SESSION_START`, `SESSION_END` |
| `user` | STRING | Username attempting or holding VPN session | `jsmith`, `mlopez`, `agarcia`, `fmartinez`, `admin`, `svc-account` |
| `src_ip` | STRING | Client IP address | Any public IP |
| `vpn_gateway` | STRING | VPN gateway receiving the connection | `vpn-gw-01`, `vpn-gw-02` |
| `auth_method` | STRING | Authentication method used | `certificate`, `password`, `MFA` |
| `session_duration_sec` | BIGINT | Session length in seconds (0 on failure) | `60`–`28800`; `0` on fail |
| `bytes_transferred` | BIGINT | Total bytes in session (0 on failure) | `1000`–`5000000`; `0` on fail |
| `status` | STRING | Outcome of the event (raw, pre-normalization) | `success`, `fail` |
| `failure_reason` | STRING | Reason for auth failure; empty on success | `wrong_password`, `expired_cert`, `timeout`, `blocked_ip`, `""` |

### 1.3 VPC Flow Logs (`raw/vpc-flow/`)

| Field | Type | Description | Example Values |
|---|---|---|---|
| `timestamp` | STRING | Event datetime in `YYYY-MM-DD HH:MM:SS` format | `2026-03-15 22:05:11` |
| `account_id` | STRING | AWS account ID | `123456789012` |
| `interface_id` | STRING | Elastic Network Interface ID | `eni-abc123`, `eni-def456`, `eni-ghi789` |
| `src_ip` | STRING | Source IP address | Any IP |
| `dst_ip` | STRING | Destination IP address | Any IP |
| `src_port` | INT | Source port number | `1024`–`65535` |
| `dst_port` | INT | Destination port number | `80`, `443`, `22`, `3306`, `5432`, `6379` |
| `protocol` | STRING | Protocol number (IANA) | `6` (TCP), `17` (UDP), `1` (ICMP) |
| `packets` | BIGINT | Number of packets in flow | `1`–`10000` |
| `bytes` | BIGINT | Total bytes in flow | `40`–`10000000` |
| `action` | STRING | Flow decision (raw, pre-normalization) | `ACCEPT`, `REJECT` |
| `log_status` | STRING | VPC Flow log capture status | `OK` |

---

## 2. Processed Log Schemas (post-Lambda)

After normalization by `lambda/parser/handler.py`, files are stored in `s3://YOUR-BUCKET/processed/`. Each source retains all raw fields plus the following enrichment fields.

### 2.1 Added Metadata Fields (all sources)

| Field | Type | Description | Example Values |
|---|---|---|---|
| `_source` | STRING | Log source type, detected from S3 key prefix | `firewall`, `vpn`, `vpc-flow` |
| `_processed_at` | STRING | UTC timestamp when Lambda processed the record | `2026-03-15T14:32:07` |
| `_has_issues` | STRING | Whether the record had missing or empty required fields | `True`, `False` |

### 2.2 Normalized Fields

| Source | Field | Raw Values | Normalized Values |
|---|---|---|---|
| Firewall | `timestamp` | `YYYY-MM-DD HH:MM:SS` | `YYYY-MM-DDTHH:MM:SS` (ISO 8601) |
| Firewall | `action` | `ALLOW`, `DENY`, `DROP`, `RESET` | `ALLOW`, `DENY`, `DENY`, `RESET` |
| VPN | `timestamp` | `YYYY-MM-DD HH:MM:SS` | `YYYY-MM-DDTHH:MM:SS` (ISO 8601) |
| VPN | `status` | `success`, `fail` | `SUCCESS`, `FAIL` |
| VPC Flow | `timestamp` | `YYYY-MM-DD HH:MM:SS` | `YYYY-MM-DDTHH:MM:SS` (ISO 8601) |
| VPC Flow | `action` | `ACCEPT`, `REJECT` | `ALLOW`, `DENY` |

> **Note:** `DROP` is mapped to `DENY` in the normalization layer. In the raw generator, `DROP` appears as a distinct firewall action, but in Athena analytics both are treated as blocked traffic. See `normalize_action()` in `handler.py`.

---

## 3. Athena Analytics Tables

Defined in `athena/queries/01_create_tables.sql`. All tables are external, pointing to the `processed/` prefix in S3.

### 3.1 `security_log_lake.firewall_logs`

Location: `s3://YOUR-BUCKET/processed/firewall/`

| Column | Athena Type | Notes |
|---|---|---|
| `timestamp` | STRING | ISO 8601 after normalization |
| `device_id` | STRING | |
| `action` | STRING | Normalized: `ALLOW`, `DENY`, `RESET` |
| `src_ip` | STRING | |
| `dst_ip` | STRING | |
| `src_port` | INT | |
| `dst_port` | INT | |
| `protocol` | STRING | |
| `bytes_sent` | BIGINT | |
| `bytes_received` | BIGINT | |
| `duration_sec` | DOUBLE | |
| `severity` | STRING | `low`, `medium`, `high`, `critical` |
| `policy_name` | STRING | |
| `country_src` | STRING | |
| `country_dst` | STRING | |
| `_source` | STRING | Always `firewall` |
| `_processed_at` | STRING | |
| `_has_issues` | STRING | Stored as STRING, not BOOLEAN — Athena CSV limitation |

### 3.2 `security_log_lake.vpn_logs`

Location: `s3://YOUR-BUCKET/processed/vpn/`

| Column | Athena Type | Notes |
|---|---|---|
| `timestamp` | STRING | ISO 8601 after normalization |
| `device_id` | STRING | |
| `event_type` | STRING | `AUTH_SUCCESS`, `AUTH_FAIL`, `SESSION_START`, `SESSION_END` |
| `user` | STRING | |
| `src_ip` | STRING | |
| `vpn_gateway` | STRING | `vpn-gw-01`, `vpn-gw-02` |
| `auth_method` | STRING | `certificate`, `password`, `MFA` |
| `session_duration_sec` | BIGINT | `0` when status is `FAIL` |
| `bytes_transferred` | BIGINT | `0` when status is `FAIL` |
| `status` | STRING | Normalized to uppercase: `SUCCESS`, `FAIL` |
| `failure_reason` | STRING | Empty string on success |
| `_source` | STRING | Always `vpn` |
| `_processed_at` | STRING | |
| `_has_issues` | STRING | |

### 3.3 `security_log_lake.vpc_flow_logs`

Location: `s3://YOUR-BUCKET/processed/vpc-flow/`

| Column | Athena Type | Notes |
|---|---|---|
| `timestamp` | STRING | ISO 8601 after normalization |
| `account_id` | STRING | |
| `interface_id` | STRING | |
| `src_ip` | STRING | |
| `dst_ip` | STRING | |
| `src_port` | INT | |
| `dst_port` | INT | |
| `protocol` | STRING | IANA number as string: `6`, `17`, `1` |
| `packets` | BIGINT | |
| `bytes` | BIGINT | |
| `action` | STRING | Normalized: `ALLOW` (was `ACCEPT`), `DENY` (was `REJECT`) |
| `log_status` | STRING | Always `OK` in synthetic data |
| `_source` | STRING | Always `vpc-flow` |
| `_processed_at` | STRING | |
| `_has_issues` | STRING | |

---

## 4. Athena Query Outputs (Power BI Sources)

CSV files stored in `powerbi/data/`, produced by the queries in `athena/queries/02_analytics.sql`.

| File | Source Query | Columns | Description |
|---|---|---|---|
| `q1_top_blocked_ips.csv` | Q1 | `src_ip`, `blocked_count` | Top 10 IPs by DENY count |
| `q2_traffic_by_hour.csv` | Q2 | `hour`, `action`, `total` | Hourly ALLOW/DENY/RESET totals |
| `q3_top_talkers.csv` | Q3 | `src_ip`, `total_bytes` | Top 10 IPs by bytes_sent + bytes_received |
| `q4_vpn_failed_auth.csv` | Q4 | `user`, `failed_attempts` | FAIL count per VPN user |
| `q5_vpn_sessions.csv` | Q5 | `user`, `vpn_gateway`, `total_session_sec`, `total_bytes` | Successful VPN sessions aggregated |
| `q6_vpc_rejected_ports.csv` | Q6 | `dst_port`, `rejected_count` | Top 10 VPC denied destination ports |
| `q7_severity_by_hour.csv` | Q7 | `hour`, `severity`, `total` | Firewall severity distribution per hour |
| `q8_denied_by_country.csv` | Q8 | `country_src`, `denied_count` | Top 10 source countries for DENY traffic |
| `q9_daily_summary.csv` | Q9 | `day`, `total_events`, `allowed`, `blocked`, `dropped`, `reset_count`, `total_bytes` | Per-day executive summary |

---

## 5. Power BI DAX Measures

All measures live in the Power BI model and are calculated at query time from the imported CSV tables.

### 5.1 Executive Overview Measures

| Measure | Table | Formula Summary | Description |
|---|---|---|---|
| `Block Rate Percentage` | `q9_daily_summary` | `SUM(blocked) / SUM(total_events)` | Ratio of blocked events to total events across the selected date range |

```dax
Block Rate Percentage = 
DIVIDE(
    SUM(q9_daily_summary[blocked]),
    SUM(q9_daily_summary[total_events]),
    0
)
```

### 5.2 VPN Analysis Measures

| Measure | Table | Formula Summary | Description |
|---|---|---|---|
| `Active VPN Users` | `q5_vpn_sessions` | `DISTINCTCOUNT(user)` | Count of unique users with at least one successful VPN session |
| `VPN Data GB` | `q5_vpn_sessions` | `SUM(total_bytes) / 1,000,000,000` | Total bytes transferred across all VPN sessions, expressed in gigabytes |
| `VPN Session Hours` | `q5_vpn_sessions` | `SUM(total_session_sec) / 3600` | Total session time across all users and gateways, expressed in hours |
| `Failed Auth Avg All Users` | `q4_vpn_failed_auth` | `AVERAGE(failed_attempts)` ignoring user filter | Baseline average failed attempts across all users, used as denominator for deviation |
| `Failed Auth vs Avg %` | `q4_vpn_failed_auth` | `(user_total - avg_all) / avg_all` | Each user's failed auth count as a percentage deviation from the fleet average |
| `Failed Auth Color` | `q4_vpn_failed_auth` | Conditional on `Failed Auth vs Avg %` | Returns `#FF4D4F` (red) for above-average, `#7DD3FC` (blue) for below — drives dynamic bar color in the chart |
| `Gateway Traffic Imbalance %` | `q5_vpn_sessions` | `ABS(GW01 - GW02) / AVG(GW01, GW02)` | Measures how unevenly traffic is distributed between the two VPN gateways per user |

```dax
Failed Auth Avg All Users = 
CALCULATE(
    AVERAGE(q4_vpn_failed_auth[failed_attempts]),
    ALL(q4_vpn_failed_auth[user])
)

Failed Auth vs Avg % = 
DIVIDE(
    SUM(q4_vpn_failed_auth[failed_attempts]) - [Failed Auth Avg All Users],
    [Failed Auth Avg All Users],
    0
)

Failed Auth Color = 
IF([Failed Auth vs Avg %] >= 0, "#FF4D4F", "#7DD3FC")

Gateway Traffic Imbalance % = 
VAR GW01 =
    CALCULATE(
        SUM(q5_vpn_sessions[total_bytes]),
        q5_vpn_sessions[vpn_gateway] = "vpn-gw-01"
    )
VAR GW02 =
    CALCULATE(
        SUM(q5_vpn_sessions[total_bytes]),
        q5_vpn_sessions[vpn_gateway] = "vpn-gw-02"
    )
VAR AvgVal = DIVIDE(GW01 + GW02, 2, 0)
RETURN
    DIVIDE(ABS(GW01 - GW02), AvgVal, 0)
```

---

## 6. Normalized Value Enumerations

Quick reference for all controlled vocabularies after Lambda normalization.

| Field | Source | Valid Values (post-normalization) |
|---|---|---|
| `action` | firewall | `ALLOW`, `DENY`, `RESET` |
| `action` | vpc-flow | `ALLOW`, `DENY` |
| `status` | vpn | `SUCCESS`, `FAIL` |
| `event_type` | vpn | `AUTH_SUCCESS`, `AUTH_FAIL`, `SESSION_START`, `SESSION_END` |
| `severity` | firewall | `low`, `medium`, `high`, `critical` |
| `protocol` | firewall | `TCP`, `UDP`, `ICMP` |
| `protocol` | vpc-flow | `6` (TCP), `17` (UDP), `1` (ICMP) |
| `auth_method` | vpn | `certificate`, `password`, `MFA` |
| `policy_name` | firewall | `internet-access`, `internal-only`, `dmz-policy`, `vpn-split` |
| `vpn_gateway` | vpn | `vpn-gw-01`, `vpn-gw-02` |
| `log_status` | vpc-flow | `OK` |
| `_has_issues` | all | `True`, `False` (stored as STRING) |

---

*Last updated: March 2026*
