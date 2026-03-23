-- Base de datos
CREATE DATABASE IF NOT EXISTS security_log_lake;

-- Tabla: firewall_logs
CREATE EXTERNAL TABLE IF NOT EXISTS security_log_lake.firewall_logs (
  timestamp         STRING,
  device_id         STRING,
  action            STRING,
  src_ip            STRING,
  dst_ip            STRING,
  src_port          INT,
  dst_port          INT,
  protocol          STRING,
  bytes_sent        BIGINT,
  bytes_received    BIGINT,
  duration_sec      DOUBLE,
  severity          STRING,
  policy_name       STRING,
  country_src       STRING,
  country_dst       STRING,
  _source           STRING,
  _processed_at     STRING,
  _has_issues       BOOLEAN
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
LINES TERMINATED BY '\n'
STORED AS TEXTFILE
LOCATION 's3://security-log-lake-465768368095-us-east-1-an/processed/firewall/'
TBLPROPERTIES ('skip.header.line.count'='1');

-- Tabla: vpn_logs
CREATE EXTERNAL TABLE IF NOT EXISTS security_log_lake.vpn_logs (
  timestamp             STRING,
  device_id             STRING,
  event_type            STRING,
  user                  STRING,
  src_ip                STRING,
  vpn_gateway           STRING,
  auth_method           STRING,
  session_duration_sec  BIGINT,
  bytes_transferred     BIGINT,
  status                STRING,
  failure_reason        STRING,
  _source               STRING,
  _processed_at         STRING,
  _has_issues           BOOLEAN
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
LINES TERMINATED BY '\n'
STORED AS TEXTFILE
LOCATION 's3://security-log-lake-465768368095-us-east-1-an/processed/vpn/'
TBLPROPERTIES ('skip.header.line.count'='1');

-- Tabla: vpc_flow_logs
CREATE EXTERNAL TABLE IF NOT EXISTS security_log_lake.vpc_flow_logs (
  timestamp       STRING,
  account_id      STRING,
  interface_id    STRING,
  src_ip          STRING,
  dst_ip          STRING,
  src_port        INT,
  dst_port        INT,
  protocol        STRING,
  packets         BIGINT,
  bytes           BIGINT,
  action          STRING,
  log_status      STRING,
  _source         STRING,
  _processed_at   STRING,
  _has_issues     BOOLEAN
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
LINES TERMINATED BY '\n'
STORED AS TEXTFILE
LOCATION 's3://security-log-lake-465768368095-us-east-1-an/processed/vpc-flow/'
TBLPROPERTIES ('skip.header.line.count'='1');