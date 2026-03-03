# Network Monitoring Tool

A robust, cross-platform Python command-line utility for monitoring host availability using ICMP ping. Designed for automation of routine network checks with comprehensive logging and statistical analysis.

## Features

- **ICMP Ping Monitoring**: Native cross-platform ping implementation (Windows/Linux/macOS)
- **Concurrent Monitoring**: Check multiple hosts simultaneously using ThreadPoolExecutor
- **Dual Logging System**:
  - CSV logs for time-series analysis and trending
  - JSON summaries for aggregated statistics
- **Uptime Analytics**: Track uptime percentage, response times, min/max/average latency
- **Flexible Configuration**: Command-line arguments for all parameters
- **Color-Coded Output**: Visual status indicators (green=UP, red=DOWN)
- **Graceful Shutdown**: Handles interruptions with final summary report
- **Batch Processing**: Support for host lists via text files

## Installation

### Requirements
- Python 3.7+
- ICMP ping privileges (may require admin/root on some systems)

### Setup
```bash
# Clone or download the script
git clone https://github.com/dav-oss/network-monitor.git
cd network-monitor

# Or simply download network_monitor.py to your working directory
```

No external dependencies required - uses only Python standard library.

## Usage

### Basic Monitoring

```bash
# Monitor single host continuously
python network_monitor.py -H 8.8.8.8

# Monitor multiple hosts
python network_monitor.py -H 8.8.8.8 google.com 192.168.1.1

# Custom check interval (30 seconds)
python network_monitor.py -H 8.8.8.8 -i 30
```

### Time-Limited Monitoring

```bash
# Monitor for 60 minutes then auto-exit
python network_monitor.py -H 8.8.8.8 -t 60

# Quick 5-minute diagnostic
python network_monitor.py -H 192.168.1.1 gateway.local -t 5 -i 10
```

### Single Check Mode

```bash
# Run once and generate summary (useful for cron jobs)
python network_monitor.py -H 8.8.8.8 --once
```

### Batch Host Monitoring

Create a hosts file (`hosts.txt`):
```
# Infrastructure monitoring list
8.8.8.8
google.com
192.168.1.1
10.0.0.1
router.local
```

Run with file input:
```bash
python network_monitor.py -f hosts.txt -i 60 -t 1440
```

### Advanced Options

```bash
# Custom timeout and output directory
python network_monitor.py -H 8.8.8.8 --timeout 5 -o /var/log/netmon/

# Full example: 10 hosts, 30s interval, 2s timeout, 1 hour duration
python network_monitor.py -f production-hosts.txt -i 30 --timeout 2 -t 60 -o logs/
```

## Command-Line Arguments

| Argument | Short | Description | Default |
|----------|-------|-------------|---------|
| `--hosts` | `-H` | Host(s) to monitor (space-separated) | None |
| `--file` | `-f` | File containing hosts (one per line) | None |
| `--interval` | `-i` | Check interval in seconds | 60 |
| `--time` | `-t` | Total monitoring duration in minutes | Infinite |
| `--once` | | Run single check and exit | False |
| `--timeout` | | Ping timeout in seconds | 2 |
| `--output` | `-o` | Output directory for logs | logs |

## Output Files

### CSV Log Format
Located in `logs/uptime_log_YYYYMMDD_HHMMSS.csv`:
```csv
timestamp,host,status,response_time_ms,error
2024-01-15T09:30:00,8.8.8.8,UP,14.2,
2024-01-15T09:30:01,google.com,UP,23.5,
2024-01-15T09:30:02,192.168.1.1,DOWN,,Request timed out
```

### JSON Summary Format
Located in `logs/uptime_summary_YYYYMMDD_HHMMSS.json`:
```json
{
  "generated_at": "2024-01-15T10:30:00",
  "monitoring_duration_minutes": 60,
  "hosts": {
    "8.8.8.8": {
      "host": "8.8.8.8",
      "total_checks": 60,
      "successful_checks": 60,
      "failed_checks": 0,
      "uptime_percentage": 100.0,
      "last_check": "2024-01-15T10:30:00",
      "last_status": "UP",
      "avg_response_ms": 15.3,
      "min_response_ms": 12.1,
      "max_response_ms": 18.7
    }
  }
}
```

## Console Output Example

```
Starting network monitoring...
Hosts: 8.8.8.8, google.com, 192.168.1.1
Interval: 60s | Logs: logs/
Press Ctrl+C to stop

--- Check #1 @ 2024-01-15 09:30:00 ---
[09:30:00] 8.8.8.8              [UP] 14.2ms
[09:30:01] google.com           [UP] 23.5ms
[09:30:02] 192.168.1.1          [DOWN] Request timed out

--- Check #2 @ 2024-01-15 09:31:00 ---
[09:31:00] 8.8.8.8              [UP] 15.1ms
[09:31:01] google.com           [UP] 24.2ms
[09:31:02] 192.168.1.1          [DOWN] Request timed out

Monitoring stopped by user.

======================================================================
NETWORK MONITORING SUMMARY
======================================================================
Generated: 2024-01-15T09:35:00
Log files: CSV=logs/uptime_log_20240115_093000.csv, JSON=logs/uptime_summary_20240115_093000.json
----------------------------------------------------------------------

Host: 8.8.8.8
  Status: UP (as of 2024-01-15T09:35:00)
  Uptime: 100.0% (5/5 checks)
  Avg Response: 14.8ms (min: 12.1ms, max: 18.7ms)

Host: google.com
  Status: UP (as of 2024-01-15T09:35:01)
  Uptime: 100.0% (5/5 checks)
  Avg Response: 23.8ms (min: 21.2ms, max: 26.4ms)

Host: 192.168.1.1
  Status: DOWN (as of 2024-01-15T09:35:02)
  Uptime: 0.0% (0/5 checks)
  Avg Response: N/A

======================================================================
```

## Automation Examples

### Cron Job (Linux/macOS)
```bash
# Check critical hosts every 5 minutes, log to /var/log/
*/5 * * * * /usr/bin/python3 /opt/netmon/network_monitor.py -H 8.8.8.8 192.168.1.1 --once -o /var/log/netmon/
```

### Windows Task Scheduler
```powershell
# Run every hour, monitoring gateway and DNS
python network_monitor.py -H 192.168.1.1 8.8.8.8 --once -o C:\Logs\Network\
```

### Systemd Timer (Linux)
Create `/etc/systemd/system/netmon.service`:
```ini
[Unit]
Description=Network Monitoring Check

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /opt/netmon/network_monitor.py -f /etc/netmon/hosts.txt --once -o /var/log/netmon/
```

Create `/etc/systemd/system/netmon.timer`:
```ini
[Unit]
Description=Run network monitor every minute

[Timer]
OnCalendar=*:*:0/30
Persistent=true

[Install]
WantedBy=timers.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable netmon.timer
sudo systemctl start netmon.timer
```

## Data Analysis

### Python Pandas Example
```python
import pandas as pd

# Load CSV log
df = pd.read_csv('logs/uptime_log_20240115_093000.csv')

# Calculate hourly uptime
hourly = df.groupby(['host', pd.to_datetime(df['timestamp']).dt.hour])['status'].apply(
    lambda x: (x == 'UP').sum() / len(x) * 100
)

# Response time trends
df[df['response_time_ms'].notna()].groupby('host')['response_time_ms'].plot()
```

### SQL Import
```sql
-- Import CSV to database for long-term trending
LOAD DATA INFILE 'uptime_log_20240115_093000.csv'
INTO TABLE network_uptime
FIELDS TERMINATED BY ','
IGNORE 1 ROWS
(@timestamp, host, status, @response_time, @error)
SET 
  timestamp = @timestamp,
  response_time_ms = NULLIF(@response_time, ''),
  error = NULLIF(@error, '');
```

## Architecture

```
network_monitor.py
├── HostMonitor (per-host monitoring)
│   ├── ping() -> PingResult
│   ├── _parse_response_time()
│   └── get_statistics() -> Dict
├── PingResult (dataclass)
│   ├── host, timestamp, success
│   ├── response_time_ms
│   └── error_message
└── NetworkMonitor (orchestrator)
    ├── check_all_hosts() (concurrent)
    ├── _log_to_csv()
    ├── generate_summary() -> JSON
    └── run_continuous() / run_once()
```

## Troubleshooting

### Permission Denied (ICMP)
**Linux**: Run with sudo or set capabilities:
```bash
sudo setcap cap_net_raw+ep $(which python3)
```

**macOS**: Grant Terminal "Full Disk Access" in System Preferences > Security & Privacy

**Windows**: Run Command Prompt/PowerShell as Administrator

### No Response Time Data
Some systems block ICMP timestamps. The tool will still detect UP/DOWN status but may not show response times.

### Host Not Found
Verify DNS resolution or use IP addresses directly:
```bash
nslookup google.com
python network_monitor.py -H 142.250.80.46
```

## License

MIT License - Free for personal and commercial use.

## Contributing

Pull requests welcome. Areas for enhancement:
- TCP/HTTP health checks (beyond ICMP)
- Alerting webhooks (Slack/Email)
- Database backend support
- Web dashboard for visualization
