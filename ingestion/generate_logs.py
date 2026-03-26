import csv
import random
import os
from datetime import datetime, timedelta

OUTPUT_DIR = "ingestion/sample-logs"
DAYS_OF_DATA = 30       # era 7
RECORDS_PER_FILE = 5000 # era 500

os.makedirs(OUTPUT_DIR, exist_ok=True)

COUNTRIES = ["US", "CN", "RU", "BR", "DE", "PA", "MX", "IN", "GB", "KP"]
PROTOCOLS = ["TCP", "UDP", "ICMP"]
AUTH_METHODS = ["certificate", "password", "MFA"]
FAILURE_REASONS = ["wrong_password", "expired_cert", "timeout", "blocked_ip", ""]
POLICIES = ["internet-access", "internal-only", "dmz-policy", "vpn-split"]
SEVERITIES = ["low", "medium", "high", "critical"]
ACTIONS_FW = ["ALLOW", "DENY", "DROP", "RESET"]
ACTIONS_VPC = ["ACCEPT", "REJECT"]
VPN_EVENTS = ["AUTH_SUCCESS", "AUTH_FAIL", "SESSION_START", "SESSION_END"]
USERS = ["jsmith", "mlopez", "agarcia", "fmartinez", "admin", "svc-account"]
GATEWAYS = ["vpn-gw-01", "vpn-gw-02"]
INTERFACES = ["eni-abc123", "eni-def456", "eni-ghi789"]

SRC_IPS_EXTERNAL = [
    "185.220.101.45", "91.108.4.12", "45.33.32.156", "198.51.100.23",
    "203.0.113.88", "112.107.21.216", "81.24.72.156", "146.124.107.225",
    "21.64.144.5", "77.88.55.60", "194.165.16.11", "31.184.238.128",
    "109.201.133.195", "185.156.73.54", "62.210.180.229", "89.248.167.131"
]
SRC_IPS_INTERNAL = [
    "10.0.1.10", "10.0.1.20", "10.0.2.15", "10.0.2.30",
    "10.10.5.100", "10.10.5.200", "192.168.1.50", "192.168.1.75"
]
MALICIOUS_IPS = ["185.220.101.45", "91.108.4.12", "45.33.32.156", "198.51.100.23", "203.0.113.88"]

def random_ip(private=False):
    if private:
        return f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
    return f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"

def random_ts(base_date):
    offset = timedelta(hours=random.randint(0,23), minutes=random.randint(0,59), seconds=random.randint(0,59))
    return (base_date + offset).strftime("%Y-%m-%d %H:%M:%S")

def generate_firewall(base_date, n):
    rows = []
    for _ in range(n):
        src = random.choices(
            SRC_IPS_EXTERNAL + SRC_IPS_INTERNAL,
            weights=[8,8,8,8,8,4,4,4,4,4,3,3,3,3,3,3,2,2,2,2,2,2,2,2]
        )[0]
        is_malicious = src in MALICIOUS_IPS
        action = random.choices(ACTIONS_FW, weights=[20,60,15,5])[0] if is_malicious else random.choices(ACTIONS_FW, weights=[70,15,10,5])[0]
        rows.append({
            "timestamp": random_ts(base_date),
            "device_id": f"FGT-{random.randint(1,3):02d}",
            "action": action,
            "src_ip": src,
            "dst_ip": random_ip(private=random.random() > 0.3),
            "src_port": random.randint(1024, 65535),
            "dst_port": random.choice([80, 443, 22, 3389, 53, 8080, 445]),
            "protocol": random.choice(PROTOCOLS),
            "bytes_sent": random.randint(100, 500000),
            "bytes_received": random.randint(100, 1000000),
            "duration_sec": random.randint(1, 3600),
            "severity": random.choices(SEVERITIES, weights=[50, 30, 15, 5])[0],
            "policy_name": random.choice(POLICIES),
            "country_src": random.choice(COUNTRIES),
            "country_dst": random.choice(COUNTRIES),
        })
    return rows

def generate_vpn(base_date, n):
    rows = []
    for _ in range(n):
        event = random.choices(VPN_EVENTS, weights=[40, 20, 25, 15])[0]
        is_fail = event == "AUTH_FAIL"
        rows.append({
            "timestamp": random_ts(base_date),
            "device_id": f"FGT-{random.randint(1,3):02d}",
            "event_type": event,
            "user": random.choice(USERS),
            "src_ip": random_ip(),
            "vpn_gateway": random.choice(GATEWAYS),
            "auth_method": random.choice(AUTH_METHODS),
            "session_duration_sec": 0 if is_fail else random.randint(60, 28800),
            "bytes_transferred": 0 if is_fail else random.randint(1000, 5000000),
            "status": "fail" if is_fail else "success",
            "failure_reason": random.choice(FAILURE_REASONS[:-1]) if is_fail else "",
        })
    return rows

def generate_vpc_flow(base_date, n):
    rows = []
    for _ in range(n):
        action = random.choices(ACTIONS_VPC, weights=[70, 30])[0]
        rows.append({
            "timestamp": random_ts(base_date),
            "account_id": "123456789012",
            "interface_id": random.choice(INTERFACES),
            "src_ip": random_ip(private=random.random() > 0.4),
            "dst_ip": random_ip(private=random.random() > 0.4),
            "src_port": random.randint(1024, 65535),
            "dst_port": random.choice([80, 443, 22, 3306, 5432, 6379]),
            "protocol": random.choice(["6", "17", "1"]),
            "packets": random.randint(1, 10000),
            "bytes": random.randint(40, 10000000),
            "action": action,
            "log_status": "OK",
        })
    return rows

base = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
for day_offset in range(DAYS_OF_DATA):
    day = base - timedelta(days=day_offset)
    date_str = day.strftime("%Y-%m-%d")
    for name, rows in [("firewall", generate_firewall(day, RECORDS_PER_FILE)),
                       ("vpn", generate_vpn(day, RECORDS_PER_FILE)),
                       ("vpc-flow", generate_vpc_flow(day, RECORDS_PER_FILE))]:
        with open(f"{OUTPUT_DIR}/{name}_{date_str}.csv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    print(f"{date_str}")
print(f"\n{DAYS_OF_DATA * 3} files in {OUTPUT_DIR}/")