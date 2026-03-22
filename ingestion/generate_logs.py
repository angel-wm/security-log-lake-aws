import csv
import random
import os
from datetime import datetime, timedelta

# ── Configuración ──────────────────────────────────────────
OUTPUT_DIR = "ingestion/sample-logs"
DAYS_OF_DATA = 7        # cuántos días de logs generar
RECORDS_PER_FILE = 500  # registros por archivo

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Datos de apoyo ─────────────────────────────────────────
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

def random_ip(private=False):
    if private:
        return f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
    return f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"

def random_ts(base_date):
    offset = timedelta(
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59)
    )
    return (base_date + offset).strftime("%Y-%m-%d %H:%M:%S")

# ── Generadores ────────────────────────────────────────────
def generate_firewall(base_date, n):
    rows = []
    for _ in range(n):
        action = random.choices(ACTIONS_FW, weights=[60, 25, 10, 5])[0]
        rows.append({
            "timestamp": random_ts(base_date),
            "device_id": f"FGT-{random.randint(1,3):02d}",
            "action": action,
            "src_ip": random_ip(private=random.random() > 0.5),
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
            "status": "FAIL" if is_fail else "SUCCESS",
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
            "protocol": random.choice(["6", "17", "1"]),  # TCP, UDP, ICMP
            "packets": random.randint(1, 10000),
            "bytes": random.randint(40, 10000000),
            "action": action,
            "log_status": "OK",
        })
    return rows

# ── Escritura de archivos ──────────────────────────────────
generators = {
    "firewall": (generate_firewall, list(generate_firewall.__code__.co_varnames)),
    "vpn": (generate_vpn, list(generate_vpn.__code__.co_varnames)),
    "vpc-flow": (generate_vpc_flow, list(generate_vpc_flow.__code__.co_varnames)),
}

base = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

for day_offset in range(DAYS_OF_DATA):
    day = base - timedelta(days=day_offset)
    date_str = day.strftime("%Y-%m-%d")

    # Firewall
    fw_rows = generate_firewall(day, RECORDS_PER_FILE)
    fw_file = f"{OUTPUT_DIR}/firewall_{date_str}.csv"
    with open(fw_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fw_rows[0].keys())
        writer.writeheader()
        writer.writerows(fw_rows)

    # VPN
    vpn_rows = generate_vpn(day, RECORDS_PER_FILE)
    vpn_file = f"{OUTPUT_DIR}/vpn_{date_str}.csv"
    with open(vpn_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=vpn_rows[0].keys())
        writer.writeheader()
        writer.writerows(vpn_rows)

    # VPC Flow
    vpc_rows = generate_vpc_flow(day, RECORDS_PER_FILE)
    vpc_file = f"{OUTPUT_DIR}/vpc-flow_{date_str}.csv"
    with open(vpc_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=vpc_rows[0].keys())
        writer.writeheader()
        writer.writerows(vpc_rows)

    print(f"✅ Generated logs for {date_str}")

print(f"\n🎉 Done! {DAYS_OF_DATA * 3} files created in {OUTPUT_DIR}/")