#!/usr/bin/env python3
"""
Network Monitoring Tool - ICMP Host Availability Monitor
A command-line utility for monitoring host availability using ICMP ping.

Features:
- ICMP ping monitoring with configurable intervals
- CSV and JSON logging for analysis
- Concurrent monitoring of multiple hosts
- Configurable timeout and retry settings
- Summary statistics and reporting
- Color-coded console output
"""

import subprocess
import platform
import time
import csv
import json
import argparse
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from collections import defaultdict
import statistics


@dataclass
class PingResult:
    """Represents the result of a single ping attempt."""
    host: str
    timestamp: datetime
    success: bool
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    packet_loss: float = 0.0


class HostMonitor:
    """Monitors a single host via ICMP ping."""

    def __init__(self, host: str, timeout: int = 2, retries: int = 3):
        self.host = host
        self.timeout = timeout
        self.retries = retries
        self.history: List[PingResult] = []
        self.lock = Lock()

    def ping(self) -> PingResult:
        """Execute ICMP ping and return result."""
        timestamp = datetime.now()

        # Determine ping command based on OS
        system = platform.system().lower()
        if system == "windows":
            cmd = ["ping", "-n", "1", "-w", str(self.timeout * 1000), self.host]
        else:  # Linux/Mac
            cmd = ["ping", "-c", "1", "-W", str(self.timeout), self.host]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout + 2
            )

            success = result.returncode == 0
            response_time = self._parse_response_time(result.stdout, system)

            ping_result = PingResult(
                host=self.host,
                timestamp=timestamp,
                success=success,
                response_time_ms=response_time,
                error_message=None if success else "Host unreachable"
            )

        except subprocess.TimeoutExpired:
            ping_result = PingResult(
                host=self.host,
                timestamp=timestamp,
                success=False,
                response_time_ms=None,
                error_message="Request timed out"
            )
        except Exception as e:
            ping_result = PingResult(
                host=self.host,
                timestamp=timestamp,
                success=False,
                response_time_ms=None,
                error_message=str(e)
            )

        with self.lock:
            self.history.append(ping_result)

        return ping_result

    def _parse_response_time(self, output: str, system: str) -> Optional[float]:
        """Extract response time from ping output."""
        try:
            if system == "windows":
                # Windows: look for "time=XXms" or "time<1ms"
                if "time<1ms" in output.lower():
                    return 0.5
                for line in output.split('\n'):
                    if "time=" in line.lower() and "ms" in line.lower():
                        parts = line.lower().split("time=")[1].split("ms")[0]
                        return float(parts.strip())
            else:
                # Linux/Mac: look for "time=XX.X ms"
                for line in output.split('\n'):
                    if "time=" in line and "ms" in line:
                        parts = line.split("time=")[1].split()[0]
                        return float(parts)
        except (ValueError, IndexError):
            pass
        return None

    def get_statistics(self) -> Dict:
        """Calculate uptime statistics for this host."""
        with self.lock:
            if not self.history:
                return {"total_checks": 0, "uptime_percentage": 0}

            total = len(self.history)
            successful = sum(1 for r in self.history if r.success)
            response_times = [r.response_time_ms for r in self.history if r.response_time_ms is not None]

            stats = {
                "host": self.host,
                "total_checks": total,
                "successful_checks": successful,
                "failed_checks": total - successful,
                "uptime_percentage": round((successful / total) * 100, 2),
                "last_check": self.history[-1].timestamp.isoformat(),
                "last_status": "UP" if self.history[-1].success else "DOWN"
            }

            if response_times:
                stats.update({
                    "avg_response_ms": round(statistics.mean(response_times), 2),
                    "min_response_ms": round(min(response_times), 2),
                    "max_response_ms": round(max(response_times), 2)
                })

            return stats


class NetworkMonitor:
    """Main monitoring orchestrator for multiple hosts."""

    def __init__(self, hosts: List[str], interval: int = 60, 
                 log_dir: str = "logs", timeout: int = 2):
        self.hosts = {host: HostMonitor(host, timeout) for host in hosts}
        self.interval = interval
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.running = False
        self.csv_file = self.log_dir / f"uptime_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self.json_file = self.log_dir / f"uptime_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self._init_csv()

    def _init_csv(self):
        """Initialize CSV log file with headers."""
        with open(self.csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'host', 'status', 'response_time_ms', 'error'])

    def _log_to_csv(self, result: PingResult):
        """Append single result to CSV log."""
        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                result.timestamp.isoformat(),
                result.host,
                'UP' if result.success else 'DOWN',
                result.response_time_ms if result.response_time_ms else '',
                result.error_message if result.error_message else ''
            ])

    def _color_status(self, success: bool) -> str:
        """Return color-coded status string."""
        if platform.system().lower() == "windows":
            return "[UP]" if success else "[DOWN]"  # Windows cmd colors are tricky
        return f"\033[92m[UP]\033[0m" if success else f"\033[91m[DOWN]\033[0m"

    def check_all_hosts(self) -> List[PingResult]:
        """Check all hosts concurrently."""
        results = []
        with ThreadPoolExecutor(max_workers=len(self.hosts)) as executor:
            future_to_host = {
                executor.submit(monitor.ping): host 
                for host, monitor in self.hosts.items()
            }

            for future in as_completed(future_to_host):
                result = future.result()
                results.append(result)
                self._log_to_csv(result)

                # Console output
                status = self._color_status(result.success)
                time_str = result.timestamp.strftime("%H:%M:%S")
                if result.success and result.response_time_ms:
                    print(f"[{time_str}] {result.host:20} {status} {result.response_time_ms:.1f}ms")
                else:
                    print(f"[{time_str}] {result.host:20} {status} {result.error_message or 'No response'}")

        return results

    def generate_summary(self) -> Dict:
        """Generate summary statistics for all hosts."""
        summary = {
            "generated_at": datetime.now().isoformat(),
            "monitoring_duration_minutes": len(next(iter(self.hosts.values())).history) * self.interval / 60,
            "hosts": {}
        }

        for host, monitor in self.hosts.items():
            summary["hosts"][host] = monitor.get_statistics()

        # Save to JSON
        with open(self.json_file, 'w') as f:
            json.dump(summary, f, indent=2)

        return summary

    def print_summary(self):
        """Print formatted summary to console."""
        summary = self.generate_summary()

        print("\n" + "="*70)
        print("NETWORK MONITORING SUMMARY")
        print("="*70)
        print(f"Generated: {summary['generated_at']}")
        print(f"Log files: CSV={self.csv_file}, JSON={self.json_file}")
        print("-"*70)

        for host, stats in summary["hosts"].items():
            print(f"\nHost: {host}")
            print(f"  Status: {stats['last_status']} (as of {stats['last_check']})")
            print(f"  Uptime: {stats['uptime_percentage']}% ({stats['successful_checks']}/{stats['total_checks']} checks)")
            if 'avg_response_ms' in stats:
                print(f"  Avg Response: {stats['avg_response_ms']}ms (min: {stats['min_response_ms']}ms, max: {stats['max_response_ms']}ms)")

        print("="*70)

    def run_continuous(self, duration_minutes: Optional[int] = None):
        """Run monitoring loop continuously."""
        self.running = True
        start_time = time.time()
        iteration = 0

        print(f"\nStarting network monitoring...")
        print(f"Hosts: {', '.join(self.hosts.keys())}")
        print(f"Interval: {self.interval}s | Logs: {self.log_dir}/")
        print(f"Press Ctrl+C to stop\n")

        try:
            while self.running:
                iteration += 1
                print(f"--- Check #{iteration} @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
                self.check_all_hosts()

                # Check if duration exceeded
                if duration_minutes and (time.time() - start_time) >= duration_minutes * 60:
                    print(f"\nCompleted {duration_minutes} minutes of monitoring.")
                    break

                # Wait for next interval
                time.sleep(self.interval)

        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user.")
        finally:
            self.running = False
            self.print_summary()

    def run_once(self):
        """Run single check cycle."""
        print(f"\nSingle check @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.check_all_hosts()
        self.print_summary()


def main():
    parser = argparse.ArgumentParser(
        description="Network Monitoring Tool - Monitor host availability via ICMP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -H 8.8.8.8 google.com                    # Monitor 2 hosts
  %(prog)s -H 192.168.1.1 -i 30 -t 5                # 30s interval, 5min duration
  %(prog)s -H 10.0.0.1 -f hosts.txt --once          # From file, single check
        """
    )

    parser.add_argument(
        '-H', '--hosts', 
        nargs='+', 
        help='Host(s) to monitor (IP or hostname)'
    )
    parser.add_argument(
        '-f', '--file',
        help='File containing hosts (one per line)'
    )
    parser.add_argument(
        '-i', '--interval', 
        type=int, 
        default=60,
        help='Check interval in seconds (default: 60)'
    )
    parser.add_argument(
        '-t', '--time', 
        type=int,
        help='Total monitoring duration in minutes (default: infinite)'
    )
    parser.add_argument(
        '--once', 
        action='store_true',
        help='Run single check and exit'
    )
    parser.add_argument(
        '--timeout', 
        type=int, 
        default=2,
        help='Ping timeout in seconds (default: 2)'
    )
    parser.add_argument(
        '-o', '--output', 
        default='logs',
        help='Output directory for logs (default: logs)'
    )

    args = parser.parse_args()

    # Collect hosts
    hosts = []
    if args.hosts:
        hosts.extend(args.hosts)
    if args.file:
        try:
            with open(args.file) as f:
                hosts.extend(line.strip() for line in f if line.strip() and not line.startswith('#'))
        except FileNotFoundError:
            print(f"Error: Hosts file '{args.file}' not found")
            return

    if not hosts:
        print("Error: No hosts specified. Use -H or -f")
        parser.print_help()
        return

    # Remove duplicates while preserving order
    hosts = list(dict.fromkeys(hosts))

    # Initialize and run monitor
    monitor = NetworkMonitor(
        hosts=hosts,
        interval=args.interval,
        log_dir=args.output,
        timeout=args.timeout
    )

    if args.once:
        monitor.run_once()
    else:
        monitor.run_continuous(duration_minutes=args.time)


if __name__ == "__main__":
    main()
