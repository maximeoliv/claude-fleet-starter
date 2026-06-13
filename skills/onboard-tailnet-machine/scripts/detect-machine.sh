#!/bin/bash
# Detects machine identity, network, and key services. Outputs JSON to stdout.
set -e

HOSTNAME=$(hostname)
TS_HOSTNAME=$(tailscale status --self --json 2>/dev/null | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['Self'].get('HostName',''))" 2>/dev/null || echo "$HOSTNAME")
TS_IP=$(tailscale ip -4 2>/dev/null | head -1)
TS_DNS_NAME=$(tailscale status --self --json 2>/dev/null | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['Self'].get('DNSName','').rstrip('.'))" 2>/dev/null || echo "")

# OS
OS_PRETTY=$(grep PRETTY_NAME /etc/os-release 2>/dev/null | cut -d'"' -f2 || uname -sr)
KERNEL=$(uname -r)
CPU_CORES=$(nproc 2>/dev/null || echo "?")
RAM_GIB=$(free -g 2>/dev/null | awk '/^Mem:/{print $2}' || echo "?")
DISK_ROOT=$(df -h / 2>/dev/null | awk 'NR==2{print $2" ("$5" used)"}' || echo "?")
UPTIME=$(uptime -p 2>/dev/null || uptime)
TZ=$(timedatectl show --property=Timezone --value 2>/dev/null || cat /etc/timezone 2>/dev/null || echo "?")

# Listening ports (excluding ephemeral high ports)
PORTS_LIST=$(ss -tlnH 2>/dev/null | awk '{split($4,a,":");port=a[length(a)];if(port+0<10000)print port}' | sort -u | tr '\n' ',' | sed 's/,$//')

# Public IP (best-effort, may be empty if no internet)
PUB_IP=$(timeout 4 curl -fsS https://api.ipify.org 2>/dev/null || echo "")

cat <<EOF
{
  "hostname": "$HOSTNAME",
  "ts_hostname": "$TS_HOSTNAME",
  "ts_ip": "$TS_IP",
  "ts_dns": "$TS_DNS_NAME",
  "pub_ip": "$PUB_IP",
  "os": "$OS_PRETTY",
  "kernel": "$KERNEL",
  "cpu_cores": "$CPU_CORES",
  "ram_gib": "$RAM_GIB",
  "disk_root": "$DISK_ROOT",
  "uptime": "$UPTIME",
  "timezone": "$TZ",
  "ports": "$PORTS_LIST"
}
EOF
