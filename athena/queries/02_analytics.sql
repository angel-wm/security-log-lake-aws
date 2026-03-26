-- ============================================
-- Security Log Lake — Analytics Queries
-- Ejecutar cada query por separado en Athena
-- ============================================

-- Q1: Top 10 IPs con más tráfico bloqueado
SELECT src_ip, COUNT(*) AS blocked_count
FROM security_log_lake.firewall_logs
WHERE action = 'DENY'
GROUP BY src_ip
ORDER BY blocked_count DESC
LIMIT 10;

-- Q2: Tráfico permitido vs bloqueado por hora
SELECT 
  SUBSTR(timestamp, 1, 13) AS hour,
  action,
  COUNT(*) AS total
FROM security_log_lake.firewall_logs
GROUP BY SUBSTR(timestamp, 1, 13), action
ORDER BY hour, action;

-- Q3: Top talkers (más bytes transferidos)
SELECT 
  src_ip,
  SUM(bytes_sent + bytes_received) AS total_bytes
FROM security_log_lake.firewall_logs
GROUP BY src_ip
ORDER BY total_bytes DESC
LIMIT 10;

-- Q4: Fallos de autenticación VPN por usuario
SELECT 
  user,
  COUNT(*) AS failed_attempts
FROM security_log_lake.vpn_logs
WHERE status = 'FAIL'
GROUP BY user
ORDER BY failed_attempts DESC
LIMIT 10;

-- Q5: Sesiones VPN activas
SELECT 
  user,
  vpn_gateway,
  SUM(session_duration_sec) AS total_session_sec,
  SUM(bytes_transferred) AS total_bytes
FROM security_log_lake.vpn_logs
WHERE status = 'SUCCESS'
GROUP BY user, vpn_gateway
ORDER BY total_session_sec DESC;

-- Q6: Tráfico rechazado en VPC por puerto
SELECT 
  dst_port,
  COUNT(*) AS rejected_count
FROM security_log_lake.vpc_flow_logs
WHERE action = 'DENY'
GROUP BY dst_port
ORDER BY rejected_count DESC
LIMIT 10;

-- Q7: Severidad de eventos por hora (heatmap)
SELECT 
  SUBSTR(timestamp, 1, 13) AS hour,
  severity,
  COUNT(*) AS total
FROM security_log_lake.firewall_logs
GROUP BY SUBSTR(timestamp, 1, 13), severity
ORDER BY hour, severity;

-- Q8: Países con más tráfico denegado
SELECT 
  country_src,
  COUNT(*) AS denied_count
FROM security_log_lake.firewall_logs
WHERE action = 'DENY'
GROUP BY country_src
ORDER BY denied_count DESC
LIMIT 10;

-- Q9: Resumen ejecutivo diario
SELECT
  SUBSTR(timestamp, 1, 10) AS day,
  COUNT(*) AS total_events,
  SUM(CASE WHEN action = 'ALLOW' THEN 1 ELSE 0 END) AS allowed,
  SUM(CASE WHEN action = 'DENY' THEN 1 ELSE 0 END) AS blocked,
  SUM(CASE WHEN action = 'DROP' THEN 1 ELSE 0 END) AS dropped,
  SUM(CASE WHEN action = 'RESET' THEN 1 ELSE 0 END) AS reset_count,
  SUM(bytes_sent + bytes_received) AS total_bytes
FROM security_log_lake.firewall_logs
GROUP BY SUBSTR(timestamp, 1, 10)
ORDER BY day;