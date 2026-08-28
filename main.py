import subprocess
import re
import json
import os
import socket
import time
import statistics
import shutil
from datetime import datetime


# ============================================================
# NETX - NETWORK DIAGNOSTIC TOOL
# Windows Edition
# ============================================================


# ============================================================
# COLORS
# ============================================================

class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"

    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"


def clr(text, color):
    return f"{color}{text}{C.RESET}"


# ============================================================
# HELPERS
# ============================================================

def run_cmd(command, timeout=30):

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=timeout
        )

        return result.stdout

    except subprocess.TimeoutExpired:
        return ""

    except Exception as e:
        print(clr(f"Command error: {e}", C.RED))
        return ""


def clear_screen():
    os.system("cls")


def pause():
    input("\nPress Enter...")


def banner():

    clear_screen()

    print(clr(r"""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║                       🌐 NETX                            ║
║                NETWORK DIAGNOSTIC TOOL                   ║
║                                                          ║
║                  Windows Edition                         ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
""", C.CYAN))


# ============================================================
# CURRENT WIFI
# ============================================================

def current_wifi():

    output = run_cmd([
        "netsh",
        "wlan",
        "show",
        "interfaces"
    ])

    if not output:
        return None

    ssid = re.search(
        r"^\s*SSID\s*:\s*(.+)$",
        output,
        re.MULTILINE
    )

    signal = re.search(
        r"^\s*Signal\s*:\s*(.+)$",
        output,
        re.MULTILINE
    )

    radio = re.search(
        r"^\s*Radio type\s*:\s*(.+)$",
        output,
        re.MULTILINE
    )

    state = re.search(
        r"^\s*State\s*:\s*(.+)$",
        output,
        re.MULTILINE
    )

    bssid = re.search(
        r"^\s*BSSID\s*:\s*(.+)$",
        output,
        re.MULTILINE
    )

    channel = re.search(
        r"^\s*Channel\s*:\s*(.+)$",
        output,
        re.MULTILINE
    )

    if state and state.group(1).strip().lower() != "connected":
        return None

    return {
        "ssid": ssid.group(1).strip() if ssid else "Unknown",
        "signal": signal.group(1).strip() if signal else "Unknown",
        "radio": radio.group(1).strip() if radio else "Unknown",
        "state": state.group(1).strip() if state else "Unknown",
        "bssid": bssid.group(1).strip() if bssid else "Unknown",
        "channel": channel.group(1).strip() if channel else "Unknown"
    }


# ============================================================
# NETWORK INFORMATION
# ============================================================

def network_info():

    output = run_cmd(["ipconfig", "/all"])

    info = {
        "ipv4": "Unknown",
        "gateway": "Unknown",
        "dns": [],
        "subnet": "Unknown",
        "adapter": "Unknown"
    }

    ipv4_matches = re.findall(
        r"IPv4 Address[.\s]*:\s*([0-9.]+)",
        output,
        re.IGNORECASE
    )

    gateway_matches = re.findall(
        r"Default Gateway[.\s]*:\s*([0-9.]+)",
        output,
        re.IGNORECASE
    )

    subnet_matches = re.findall(
        r"Subnet Mask[.\s]*:\s*([0-9.]+)",
        output,
        re.IGNORECASE
    )

    dns_matches = re.findall(
        r"DNS Servers[.\s]*:\s*([0-9.]+)",
        output,
        re.IGNORECASE
    )

    if ipv4_matches:
        for ip in ipv4_matches:
            if not ip.startswith("169.254."):
                info["ipv4"] = ip
                break

    if gateway_matches:
        info["gateway"] = gateway_matches[0]

    if subnet_matches:
        info["subnet"] = subnet_matches[0]

    info["dns"] = list(dict.fromkeys(dns_matches))

    return info


# ============================================================
# PING
# ============================================================

def ping(host, count=4, timeout=2000):

    command = [
        "ping",
        "-n",
        str(count),
        "-w",
        str(timeout),
        host
    ]

    output = run_cmd(command, timeout=(count * 5) + 5)

    if not output:
        return None

    sent_match = re.search(
        r"Packets: Sent = (\d+), Received = (\d+), Lost = (\d+)",
        output,
        re.IGNORECASE
    )

    if not sent_match:
        return None

    sent = int(sent_match.group(1))
    received = int(sent_match.group(2))
    lost = int(sent_match.group(3))

    loss = 0

    if sent > 0:
        loss = (lost / sent) * 100

    times = re.findall(
        r"time[=<]\s*(\d+)\s*ms",
        output,
        re.IGNORECASE
    )

    times = [int(x) for x in times]

    minimum = min(times) if times else None
    maximum = max(times) if times else None
    average = statistics.mean(times) if times else None

    jitter = None

    if len(times) > 1:

        differences = [
            abs(times[i] - times[i - 1])
            for i in range(1, len(times))
        ]

        jitter = round(
            statistics.mean(differences),
            2
        )

    return {
        "host": host,
        "sent": sent,
        "received": received,
        "lost": lost,
        "loss": round(loss, 2),
        "min": minimum,
        "max": maximum,
        "avg": round(average, 2)
        if average is not None else None,
        "jitter": jitter
    }


# ============================================================
# PING QUALITY
# ============================================================

def ping_quality(avg):

    if avg is None:
        return clr("🔴 TIMEOUT", C.RED)

    if avg < 50:
        return clr("🟢 Excellent", C.GREEN)

    if avg < 100:
        return clr("🟡 Good", C.YELLOW)

    if avg < 200:
        return clr("🟠 High", C.YELLOW)

    return clr("🔴 Very High", C.RED)


# ============================================================
# PING RESULT
# ============================================================

def show_ping_result(result):

    if not result:

        print(
            clr(
                "\n❌ Ping failed.",
                C.RED
            )
        )

        return

    print()
    print(clr(
        "╔════════════════════════════════════════════╗",
        C.CYAN
    ))

    print(clr(
        "║              📊 PING RESULT                ║",
        C.CYAN
    ))

    print(clr(
        "╚════════════════════════════════════════════╝",
        C.CYAN
    ))

    print()

    print(f"🎯 Target       : {result['host']}")

    if result["avg"] is not None:

        print(f"📈 Average      : {result['avg']} ms")
        print(f"⚡ Minimum      : {result['min']} ms")
        print(f"🐌 Maximum      : {result['max']} ms")
        print(f"📊 Quality      : {ping_quality(result['avg'])}")

        if result["jitter"] is not None:
            print(f"〰️ Jitter       : {result['jitter']} ms")

    else:

        print("📈 Average      : Timeout")

    print(f"📦 Packets Sent : {result['sent']}")
    print(f"📥 Received     : {result['received']}")

    loss = result["loss"]

    if loss == 0:

        loss_status = clr(
            f"{loss}% 🟢",
            C.GREEN
        )

    elif loss < 20:

        loss_status = clr(
            f"{loss}% 🟡",
            C.YELLOW
        )

    else:

        loss_status = clr(
            f"{loss}% 🔴",
            C.RED
        )

    print(f"📦 Packet Loss  : {loss_status}")


# ============================================================
# 1. NETWORK INFORMATION
# ============================================================

def show_network_info():

    banner()

    wifi = current_wifi()
    network = network_info()

    print(clr(
        "📡 CONNECTION",
        C.BOLD
    ))

    print("-" * 55)

    if wifi:

        print(f"SSID       : {clr(wifi['ssid'], C.GREEN)}")
        print(f"Signal     : {wifi['signal']}")
        print(f"Radio      : {wifi['radio']}")
        print(f"Channel    : {wifi['channel']}")
        print(f"BSSID      : {wifi['bssid']}")
        print(f"State      : {wifi['state']}")

    else:

        print(
            clr(
                "Wi-Fi information unavailable.",
                C.RED
            )
        )

    print()

    print(clr(
        "🌐 NETWORK",
        C.BOLD
    ))

    print("-" * 55)

    print(f"IPv4       : {network['ipv4']}")
    print(f"Subnet     : {network['subnet']}")
    print(f"Gateway    : {network['gateway']}")

    if network["dns"]:
        print(f"DNS        : {', '.join(network['dns'])}")
    else:
        print("DNS        : Unknown")

    pause()


# ============================================================
# 2. PING TEST
# ============================================================

def ping_menu():

    banner()

    print(clr(
        "📊 PING TEST",
        C.BOLD
    ))

    print("-" * 55)

    host = input(
        "Target [google.com]: "
    ).strip()

    if not host:
        host = "google.com"

    count_input = input(
        "Packets [4]: "
    ).strip()

    try:
        count = int(count_input)

        if count <= 0:
            count = 4

        if count > 50:
            count = 50

    except ValueError:
        count = 4

    print()

    print(
        clr(
            f"Testing {host}...",
            C.CYAN
        )
    )

    result = ping(
        host,
        count
    )

    show_ping_result(result)

    pause()


# ============================================================
# 3. INTERNET TEST
# ============================================================

def internet_test():

    banner()

    print(clr(
        "🌐 INTERNET CONNECTIVITY TEST",
        C.BOLD
    ))

    print("-" * 60)

    network = network_info()

    targets = [
        ("Gateway", network["gateway"]),
        ("Cloudflare", "1.1.1.1"),
        ("Google DNS", "8.8.8.8")
    ]

    results = []

    for name, host in targets:

        if host == "Unknown":
            continue

        print(
            f"Testing {name:<15}",
            end="",
            flush=True
        )

        result = ping(
            host,
            2
        )

        if result and result["received"] > 0:

            avg = result["avg"]

            print(
                clr(
                    f" 🟢 {avg} ms",
                    C.GREEN
                )
            )

            results.append(
                (name, result)
            )

        else:

            print(
                clr(
                    " 🔴 FAILED",
                    C.RED
                )
            )

            results.append(
                (name, None)
            )

    print()

    gateway_ok = any(
        name == "Gateway" and result
        for name, result in results
    )

    internet_ok = any(
        name in ("Cloudflare", "Google DNS") and result
        for name, result in results
    )

    if gateway_ok and internet_ok:

        print(
            clr(
                "✅ Internet connection looks healthy.",
                C.GREEN
            )
        )

    elif gateway_ok and not internet_ok:

        print(
            clr(
                "⚠️ Gateway works, but Internet is unreachable.",
                C.YELLOW
            )
        )

    else:

        print(
            clr(
                "❌ Local network connectivity problem.",
                C.RED
            )
        )

    pause()


# ============================================================
# 4. DNS TEST
# ============================================================

def dns_test():

    banner()

    print(clr(
        "🔎 DNS PERFORMANCE TEST",
        C.BOLD
    ))

    print("-" * 60)

    domains = [
        ("Google", "google.com"),
        ("Cloudflare", "cloudflare.com"),
        ("Microsoft", "microsoft.com"),
        ("GitHub", "github.com"),
        ("Python", "python.org")
    ]

    results = []

    for name, host in domains:

        print(
            f"Testing {name:<15}",
            end="",
            flush=True
        )

        start = time.perf_counter()

        try:

            socket.gethostbyname(host)

            elapsed = (
                time.perf_counter() - start
            ) * 1000

            elapsed = round(elapsed, 2)

            print(
                clr(
                    f" 🟢 {elapsed} ms",
                    C.GREEN
                )
            )

            results.append(
                (name, elapsed)
            )

        except socket.gaierror:

            print(
                clr(
                    " 🔴 FAILED",
                    C.RED
                )
            )

    if results:

        fastest = min(
            results,
            key=lambda x: x[1]
        )

        print()

        print(
            clr(
                f"🏆 Fastest: {fastest[0]} "
                f"({fastest[1]} ms)",
                C.GREEN
            )
        )

    pause()


# ============================================================
# 5. DNS BENCHMARK
# ============================================================

def dns_benchmark():

    banner()

    print(clr(
        "🔎 DNS BENCHMARK",
        C.BOLD
    ))

    print("-" * 70)

    dns_servers = [
        ("Cloudflare", "1.1.1.1"),
        ("Cloudflare 2", "1.0.0.1"),
        ("Google", "8.8.8.8"),
        ("Google 2", "8.8.4.4"),
        ("Quad9", "9.9.9.9"),
        ("OpenDNS", "208.67.222.222"),
        ("AdGuard", "94.140.14.14")
    ]

    domains = [
        "google.com",
        "github.com",
        "cloudflare.com"
    ]

    results = []

    for name, server in dns_servers:

        print(
            f"Testing {name:<18} {server:<16}",
            end="",
            flush=True
        )

        times = []

        for domain in domains:

            command = [
                "nslookup",
                domain,
                server
            ]

            start = time.perf_counter()

            output = run_cmd(
                command,
                timeout=5
            )

            elapsed = (
                time.perf_counter() - start
            ) * 1000

            if output and "timed out" not in output.lower():

                times.append(elapsed)

        if times:

            avg = round(
                statistics.mean(times),
                2
            )

            results.append(
                (name, server, avg)
            )

            print(
                clr(
                    f"🟢 {avg} ms",
                    C.GREEN
                )
            )

        else:

            print(
                clr(
                    "🔴 FAILED",
                    C.RED
                )
            )

    if results:

        results.sort(
            key=lambda x: x[2]
        )

        print()

        print(
            clr(
                "🏆 DNS RANKING",
                C.CYAN
            )
        )

        print("-" * 50)

        for index, item in enumerate(
            results,
            1
        ):

            name, server, avg = item

            print(
                f"{index:02d}. "
                f"{name:<18}"
                f"{server:<16}"
                f"{avg} ms"
            )

        print()

        winner = results[0]

        print(
            clr(
                f"🥇 Fastest DNS: "
                f"{winner[0]} "
                f"({winner[1]}) "
                f"- {winner[2]} ms",
                C.GREEN
            )
        )

    pause()


# ============================================================
# 6. SAVED WIFI PROFILES
# ============================================================

def wifi_profiles():

    banner()

    output = run_cmd([
        "netsh",
        "wlan",
        "show",
        "profiles"
    ])

    profiles = re.findall(
        r"All User Profile\s*:\s*(.*)",
        output,
        re.IGNORECASE
    )

    profiles = [
        p.strip()
        for p in profiles
        if p.strip()
    ]

    print(clr(
        "📂 SAVED WI-FI PROFILES",
        C.BOLD
    ))

    print("-" * 65)

    if not profiles:

        print(
            clr(
                "No profiles found.",
                C.RED
            )
        )

    else:

        current = current_wifi()

        for index, profile in enumerate(
            profiles,
            1
        ):

            if (
                current
                and profile == current["ssid"]
            ):

                status = clr(
                    "🟢 CONNECTED",
                    C.GREEN
                )

            else:

                status = clr(
                    "⚪ SAVED",
                    C.GRAY
                )

            print(
                f"{index:02d}. "
                f"{profile:<35} "
                f"{status}"
            )

        print()

        print(
            f"📊 Total Profiles: "
            f"{len(profiles)}"
        )

    pause()


# ============================================================
# 7. WIFI SCANNER
# ============================================================

def scan_wifi_networks():

    banner()

    print(clr(
        "📶 WIFI NETWORK SCANNER",
        C.BOLD
    ))

    print("-" * 85)

    print(
        clr(
            "Scanning nearby Wi-Fi networks...",
            C.CYAN
        )
    )

    output = run_cmd([
        "netsh",
        "wlan",
        "show",
        "networks",
        "mode=bssid"
    ])

    if not output:

        print(
            clr(
                "\n❌ Could not scan Wi-Fi networks.",
                C.RED
            )
        )

        pause()
        return

    networks = []

    current = None

    for raw_line in output.splitlines():

        line = raw_line.strip()

        ssid_match = re.match(
            r"SSID\s+\d+\s*:\s*(.*)",
            line,
            re.IGNORECASE
        )

        if ssid_match:

            if current is not None:
                networks.append(current)

            current = {
                "ssid": ssid_match.group(1).strip(),
                "signal": "Unknown",
                "security": "Unknown",
                "channel": "Unknown",
                "radio": "Unknown",
                "bssid": "Unknown"
            }

            continue

        if current is None:
            continue

        signal_match = re.match(
            r"Signal\s*:\s*(\d+)%",
            line,
            re.IGNORECASE
        )

        if signal_match:
            current["signal"] = (
                signal_match.group(1) + "%"
            )

        auth_match = re.match(
            r"Authentication\s*:\s*(.*)",
            line,
            re.IGNORECASE
        )

        if auth_match:
            current["security"] = (
                auth_match.group(1).strip()
            )

        channel_match = re.match(
            r"Channel\s*:\s*(\d+)",
            line,
            re.IGNORECASE
        )

        if channel_match:
            current["channel"] = (
                channel_match.group(1)
            )

        radio_match = re.match(
            r"Radio type\s*:\s*(.*)",
            line,
            re.IGNORECASE
        )

        if radio_match:
            current["radio"] = (
                radio_match.group(1).strip()
            )

        bssid_match = re.match(
            r"BSSID\s+\d+\s*:\s*(.*)",
            line,
            re.IGNORECASE
        )

        if bssid_match:
            current["bssid"] = (
                bssid_match.group(1).strip()
            )

    if current is not None:
        networks.append(current)

    # --------------------------------------------------------
    # Remove duplicates by SSID
    # --------------------------------------------------------

    unique_networks = {}

    for network in networks:

        ssid = network["ssid"]

        if ssid not in unique_networks:

            unique_networks[ssid] = network

        else:

            try:

                old_signal = int(
                    unique_networks[ssid]["signal"]
                    .replace("%", "")
                )

                new_signal = int(
                    network["signal"]
                    .replace("%", "")
                )

                if new_signal > old_signal:
                    unique_networks[ssid] = network

            except ValueError:
                pass

    networks = list(
        unique_networks.values()
    )

    # --------------------------------------------------------
    # Sort by signal
    # --------------------------------------------------------

    def signal_value(network):

        try:

            return int(
                network["signal"]
                .replace("%", "")
            )

        except ValueError:

            return -1

    networks.sort(
        key=signal_value,
        reverse=True
    )

    # --------------------------------------------------------
    # Display
    # --------------------------------------------------------

    print()

    print(
        f"{'SSID':<25}"
        f"{'Signal':<12}"
        f"{'Security':<22}"
        f"{'Channel':<10}"
        f"{'Radio':<12}"
    )

    print("-" * 81)

    open_count = 0
    secured_count = 0

    open_networks = []

    for network in networks:

        ssid = network["ssid"]

        if not ssid:
            ssid = "<Hidden Network>"

        ssid_display = ssid[:23]

        signal = network["signal"]
        security = network["security"]
        channel = network["channel"]
        radio = network["radio"]

        security_lower = security.lower()

        # ----------------------------------------------------
        # OPEN DETECTION
        # ----------------------------------------------------

        is_open = (
            security_lower in [
                "open",
                "none",
                "unknown"
            ]
            or security == ""
        )

        if is_open:

            security_display = clr(
                "🟢 OPEN",
                C.GREEN
            )

            open_count += 1
            open_networks.append(network)

        else:

            security_display = clr(
                "🔐 " + security[:17],
                C.YELLOW
            )

            secured_count += 1

        # ----------------------------------------------------
        # SIGNAL COLOR
        # ----------------------------------------------------

        try:

            signal_number = int(
                signal.replace("%", "")
            )

        except ValueError:

            signal_number = 0

        if signal_number >= 75:

            signal_display = clr(
                signal,
                C.GREEN
            )

        elif signal_number >= 40:

            signal_display = clr(
                signal,
                C.YELLOW
            )

        else:

            signal_display = clr(
                signal,
                C.RED
            )

        print(
            f"{ssid_display:<25}"
            f"{signal_display:<21}"
            f"{security_display:<31}"
            f"{channel:<10}"
            f"{radio[:10]:<12}"
        )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print("-" * 81)

    print()

    print(
        f"📡 Total Networks : "
        f"{len(networks)}"
    )

    print(
        f"🟢 Open Networks  : "
        f"{open_count}"
    )

    print(
        f"🔐 Secured        : "
        f"{secured_count}"
    )

    # --------------------------------------------------------
    # OPEN NETWORKS
    # --------------------------------------------------------

    print()

    if open_networks:

        print(
            clr(
                "🚨 OPEN WI-FI NETWORKS DETECTED",
                C.GREEN
            )
        )

        print("-" * 70)

        for network in open_networks:

            display_name = (
                network["ssid"]
                if network["ssid"]
                else "<Hidden Network>"
            )

            print(
                f"  🟢 {display_name}"
                f"   📶 {network['signal']}"
                f"   📻 CH {network['channel']}"
            )

        print()

        print(
            clr(
                "⚠️ OPEN networks do not require "
                "Wi-Fi authentication.",
                C.YELLOW
            )
        )

    else:

        print(
            clr(
                "🔐 No OPEN Wi-Fi networks detected.",
                C.YELLOW
            )
        )

    pause()


# ============================================================
# 8. LIVE PING MONITOR
# ============================================================

def live_monitor():

    banner()

    print(clr(
        "📈 LIVE PING MONITOR",
        C.BOLD
    ))

    print("-" * 60)

    host = input(
        "Target [1.1.1.1]: "
    ).strip()

    if not host:
        host = "1.1.1.1"

    print()

    print(
        clr(
            "Press CTRL+C to stop.",
            C.YELLOW
        )
    )

    print()

    values = []

    try:

        while True:

            result = ping(
                host,
                1
            )

            now = datetime.now().strftime(
                "%H:%M:%S"
            )

            if (
                result
                and result["avg"] is not None
            ):

                value = result["avg"]

                values.append(value)

                if value < 50:
                    status = clr(
                        "🟢",
                        C.GREEN
                    )

                elif value < 100:
                    status = clr(
                        "🟡",
                        C.YELLOW
                    )

                else:
                    status = clr(
                        "🔴",
                        C.RED
                    )

                print(
                    f"{now}   "
                    f"{status} "
                    f"{value:>4} ms"
                )

            else:

                print(
                    f"{now}   "
                    f"{clr('🔴 TIMEOUT', C.RED)}"
                )

            time.sleep(1)

    except KeyboardInterrupt:

        print()

        if values:

            print(
                clr(
                    "📊 SESSION SUMMARY",
                    C.CYAN
                )
            )

            print(
                f"Samples : {len(values)}"
            )

            print(
                f"Min     : {min(values)} ms"
            )

            print(
                f"Avg     : "
                f"{round(statistics.mean(values), 2)} ms"
            )

            print(
                f"Max     : {max(values)} ms"
            )

            if len(values) > 1:

                differences = [
                    abs(
                        values[i] - values[i - 1]
                    )
                    for i in range(1, len(values))
                ]

                jitter = round(
                    statistics.mean(differences),
                    2
                )

                print(
                    f"Jitter  : {jitter} ms"
                )

        pause()


# ============================================================
# 9. REAL-TIME NETWORK MONITOR
# ============================================================

def get_network_bytes():

    output = run_cmd([
        "powershell",
        "-NoProfile",
        "-Command",
        """
        $stats = Get-NetAdapterStatistics |
        Where-Object {$_.ReceivedBytes -gt 0 -or $_.SentBytes -gt 0} |
        Select-Object -First 1

        if ($stats) {
            Write-Output "$($stats.ReceivedBytes)|$($stats.SentBytes)"
        }
        """
    ])

    if not output:
        return None

    line = output.strip().splitlines()

    if not line:
        return None

    try:

        rx, tx = line[-1].split("|")

        return {
            "rx": int(rx),
            "tx": int(tx)
        }

    except Exception:
        return None


def real_time_monitor():

    banner()

    print(clr(
        "📊 REAL-TIME NETWORK MONITOR",
        C.BOLD
    ))

    print("-" * 65)

    print(
        clr(
            "Monitoring network traffic...",
            C.CYAN
        )
    )

    print(
        clr(
            "Press CTRL+C to stop.",
            C.YELLOW
        )
    )

    print()

    previous = get_network_bytes()

    if not previous:

        print(
            clr(
                "❌ Could not read network statistics.",
                C.RED
            )
        )

        pause()
        return

    try:

        while True:

            time.sleep(1)

            current = get_network_bytes()

            if not current:
                continue

            download = (
                current["rx"] - previous["rx"]
            )

            upload = (
                current["tx"] - previous["tx"]
            )

            download_kb = max(
                download / 1024,
                0
            )

            upload_kb = max(
                upload / 1024,
                0
            )

            download_mb = (
                download_kb / 1024
            )

            upload_mb = (
                upload_kb / 1024
            )

            now = datetime.now().strftime(
                "%H:%M:%S"
            )

            print(
                f"{now}  "
                f"⬇️ {download_mb:>7.2f} MB/s   "
                f"⬆️ {upload_mb:>7.2f} MB/s"
            )

            previous = current

    except KeyboardInterrupt:

        print()

        print(
            clr(
                "✅ Monitoring stopped.",
                C.GREEN
            )
        )

        pause()


# ============================================================
# 10. CONNECTION DROP DETECTOR
# ============================================================

def connection_drop_detector():

    banner()

    print(clr(
        "🚨 CONNECTION DROP DETECTOR",
        C.BOLD
    ))

    print("-" * 65)

    host = input(
        "Target [1.1.1.1]: "
    ).strip()

    if not host:
        host = "1.1.1.1"

    print()

    print(
        clr(
            "Press CTRL+C to stop.",
            C.YELLOW
        )
    )

    print()

    online = True
    drop_count = 0
    downtime_start = None
    total_downtime = 0

    try:

        while True:

            result = ping(
                host,
                1
            )

            now = datetime.now()

            timestamp = now.strftime(
                "%H:%M:%S"
            )

            is_online = (
                result
                and result["received"] > 0
            )

            if is_online:

                if not online:

                    if downtime_start:

                        downtime = (
                            now - downtime_start
                        ).total_seconds()

                        total_downtime += downtime

                        print(
                            clr(
                                f"{timestamp}  "
                                f"🟢 RECOVERED "
                                f"({downtime:.1f}s)",
                                C.GREEN
                            )
                        )

                    else:

                        print(
                            clr(
                                f"{timestamp}  "
                                f"🟢 RECOVERED",
                                C.GREEN
                            )
                        )

                else:

                    avg = result["avg"]

                    print(
                        f"{timestamp}  "
                        f"🟢 ONLINE  "
                        f"{avg} ms"
                    )

                online = True
                downtime_start = None

            else:

                if online:

                    drop_count += 1
                    downtime_start = now

                    print(
                        clr(
                            f"{timestamp}  "
                            f"🔴 CONNECTION DROP #{drop_count}",
                            C.RED
                        )
                    )

                else:

                    print(
                        clr(
                            f"{timestamp}  "
                            f"🔴 OFFLINE",
                            C.RED
                        )
                    )

                online = False

            time.sleep(1)

    except KeyboardInterrupt:

        print()

        print(
            clr(
                "📊 DROP DETECTOR SUMMARY",
                C.CYAN
            )
        )

        print(
            f"Connection Drops : {drop_count}"
        )

        print(
            f"Total Downtime   : "
            f"{round(total_downtime, 2)} seconds"
        )

        pause()


# ============================================================
# 11. TRACEROUTE
# ============================================================

def traceroute():

    banner()

    print(clr(
        "🧭 TRACEROUTE",
        C.BOLD
    ))

    print("-" * 65)

    host = input(
        "Target [google.com]: "
    ).strip()

    if not host:
        host = "google.com"

    print()

    print(
        clr(
            f"Tracing route to {host}...",
            C.CYAN
        )
    )

    print()

    output = run_cmd(
        [
            "tracert",
            "-d",
            "-h",
            "20",
            host
        ],
        timeout=60
    )

    if output:

        print(output)

    else:

        print(
            clr(
                "❌ Traceroute failed.",
                C.RED
            )
        )

    pause()


# ============================================================
# 12. NETWORK HEALTH
# ============================================================

def health_check():

    banner()

    print(clr(
        "❤️ NETWORK HEALTH CHECK",
        C.BOLD
    ))

    print("-" * 65)

    score = 0

    # --------------------------------------------------------
    # WIFI
    # --------------------------------------------------------

    wifi = current_wifi()

    if wifi:

        print(
            clr(
                "📡 Wi-Fi             🟢 OK",
                C.GREEN
            )
        )

        score += 20

    else:

        print(
            clr(
                "📡 Wi-Fi             🔴 FAIL",
                C.RED
            )
        )

    # --------------------------------------------------------
    # GATEWAY
    # --------------------------------------------------------

    network = network_info()

    gateway = network["gateway"]

    if gateway != "Unknown":

        result = ping(
            gateway,
            2
        )

        if result and result["received"] > 0:

            print(
                clr(
                    "🚪 Gateway           🟢 OK",
                    C.GREEN
                )
            )

            score += 20

        else:

            print(
                clr(
                    "🚪 Gateway           🔴 FAIL",
                    C.RED
                )
            )

    else:

        print(
            clr(
                "🚪 Gateway           🔴 UNKNOWN",
                C.RED
            )
        )

    # --------------------------------------------------------
    # INTERNET
    # --------------------------------------------------------

    result = ping(
        "1.1.1.1",
        3
    )

    if result and result["received"] > 0:

        print(
            clr(
                "🌐 Internet          🟢 ONLINE",
                C.GREEN
            )
        )

        score += 30

        if result["loss"] == 0:
            score += 10

        if (
            result["avg"] is not None
            and result["avg"] < 80
        ):
            score += 10

    else:

        print(
            clr(
                "🌐 Internet          🔴 OFFLINE",
                C.RED
            )
        )

    # --------------------------------------------------------
    # DNS
    # --------------------------------------------------------

    try:

        socket.gethostbyname(
            "google.com"
        )

        print(
            clr(
                "🔎 DNS               🟢 OK",
                C.GREEN
            )
        )

        score += 10

    except socket.gaierror:

        print(
            clr(
                "🔎 DNS               🔴 FAIL",
                C.RED
            )
        )

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    print()

    print("=" * 65)

    if score >= 90:

        status = clr(
            "EXCELLENT 🟢",
            C.GREEN
        )

    elif score >= 70:

        status = clr(
            "GOOD 🟡",
            C.YELLOW
        )

    elif score >= 50:

        status = clr(
            "FAIR 🟠",
            C.YELLOW
        )

    else:

        status = clr(
            "POOR 🔴",
            C.RED
        )

    print(
        "\n              NETWORK SCORE"
    )

    print(
        clr(
            f"                  {score}/100",
            C.BOLD
        )
    )

    print(
        f"\n              {status}"
    )

    pause()


# ============================================================
# 13. NETWORK DIAGNOSIS
# ============================================================

def network_diagnosis():

    banner()

    print(clr(
        "🧠 NETWORK DIAGNOSIS",
        C.BOLD
    ))

    print("-" * 70)

    network = network_info()
    wifi = current_wifi()

    score = 0
    problems = []
    recommendations = []

    # --------------------------------------------------------
    # WIFI
    # --------------------------------------------------------

    print("1️⃣ Checking Wi-Fi...")

    if wifi:

        print(
            clr(
                "   🟢 Wi-Fi connected",
                C.GREEN
            )
        )

        score += 20

        try:

            signal = int(
                wifi["signal"].replace("%", "")
            )

            if signal < 30:

                problems.append(
                    "Wi-Fi signal is very weak."
                )

                recommendations.append(
                    "Move closer to the router."
                )

            elif signal < 60:

                problems.append(
                    "Wi-Fi signal is moderate."
                )

                recommendations.append(
                    "Try reducing distance from the router."
                )

        except ValueError:
            pass

    else:

        print(
            clr(
                "   🔴 Wi-Fi not connected",
                C.RED
            )
        )

        problems.append(
            "No active Wi-Fi connection."
        )

        recommendations.append(
            "Connect to a Wi-Fi network."
        )

    # --------------------------------------------------------
    # GATEWAY
    # --------------------------------------------------------

    print()
    print("2️⃣ Checking Gateway...")

    gateway = network["gateway"]

    gateway_result = None

    if gateway != "Unknown":

        gateway_result = ping(
            gateway,
            3
        )

    if (
        gateway_result
        and gateway_result["received"] > 0
    ):

        print(
            clr(
                f"   🟢 Gateway reachable "
                f"({gateway_result['avg']} ms)",
                C.GREEN
            )
        )

        score += 25

    else:

        print(
            clr(
                "   🔴 Gateway unreachable",
                C.RED
            )
        )

        problems.append(
            "Gateway is unreachable."
        )

        recommendations.append(
            "Check router/Wi-Fi connection."
        )

    # --------------------------------------------------------
    # INTERNET
    # --------------------------------------------------------

    print()
    print("3️⃣ Checking Internet...")

    internet_result = ping(
        "1.1.1.1",
        3
    )

    if (
        internet_result
        and internet_result["received"] > 0
    ):

        print(
            clr(
                f"   🟢 Internet reachable "
                f"({internet_result['avg']} ms)",
                C.GREEN
            )
        )

        score += 30

        if internet_result["loss"] > 0:

            problems.append(
                f"Packet loss detected: "
                f"{internet_result['loss']}%"
            )

            recommendations.append(
                "Check Wi-Fi interference or ISP stability."
            )

    else:

        print(
            clr(
                "   🔴 Internet unreachable",
                C.RED
            )
        )

        problems.append(
            "Internet destination is unreachable."
        )

        recommendations.append(
            "Check ISP connection and router status."
        )

    # --------------------------------------------------------
    # DNS
    # --------------------------------------------------------

    print()
    print("4️⃣ Checking DNS...")

    dns_ok = False

    try:

        start = time.perf_counter()

        socket.gethostbyname(
            "google.com"
        )

        dns_time = (
            time.perf_counter() - start
        ) * 1000

        dns_ok = True

        print(
            clr(
                f"   🟢 DNS working "
                f"({dns_time:.2f} ms)",
                C.GREEN
            )
        )

        score += 25

    except socket.gaierror:

        print(
            clr(
                "   🔴 DNS resolution failed",
                C.RED
            )
        )

        problems.append(
            "DNS resolution is not working."
        )

        recommendations.append(
            "Try another DNS such as 1.1.1.1 or 8.8.8.8."
        )

    # --------------------------------------------------------
    # FINAL DIAGNOSIS
    # --------------------------------------------------------

    print()

    print(
        clr(
            "╔════════════════════════════════════════════╗",
            C.CYAN
        )
    )

    print(
        clr(
            "║              🧠 DIAGNOSIS                 ║",
            C.CYAN
        )
    )

    print(
        clr(
            "╚════════════════════════════════════════════╝",
            C.CYAN
        )
    )

    print()

    print(
        f"Health Score: "
        f"{score}/100"
    )

    if not problems:

        print()

        print(
            clr(
                "✅ No major network problems detected.",
                C.GREEN
            )
        )

    else:

        print()

        print(
            clr(
                "⚠️ Problems detected:",
                C.YELLOW
            )
        )

        for problem in problems:

            print(
                f"  ❌ {problem}"
            )

        print()

        print(
            clr(
                "💡 Recommendations:",
                C.CYAN
            )
        )

        for recommendation in recommendations:

            print(
                f"  → {recommendation}"
            )

    pause()


# ============================================================
# 14. EXPORT REPORT
# ============================================================

def export_report():

    banner()

    print(clr(
        "💾 EXPORT NETWORK REPORT",
        C.BOLD
    ))

    print("-" * 65)

    print(
        clr(
            "Collecting network information...",
            C.CYAN
        )
    )

    wifi = current_wifi()
    network = network_info()

    gateway_result = None

    if network["gateway"] != "Unknown":

        gateway_result = ping(
            network["gateway"],
            3
        )

    internet_result = ping(
        "1.1.1.1",
        3
    )

    dns_results = []

    for host in [
        "google.com",
        "cloudflare.com",
        "github.com"
    ]:

        start = time.perf_counter()

        try:

            socket.gethostbyname(host)

            elapsed = (
                time.perf_counter() - start
            ) * 1000

            dns_results.append({
                "host": host,
                "status": "OK",
                "time_ms": round(
                    elapsed,
                    2
                )
            })

        except socket.gaierror:

            dns_results.append({
                "host": host,
                "status": "FAILED",
                "time_ms": None
            })

    report = {

        "tool":
            "NetX",

        "version":
            "2.0",

        "timestamp":
            datetime.now().isoformat(),

        "system":
            {
                "platform": os.name,
                "python":
                    f"{__import__('sys').version_info.major}."
                    f"{__import__('sys').version_info.minor}."
                    f"{__import__('sys').version_info.micro}"
            },

        "wifi":
            wifi,

        "network":
            network,

        "gateway_ping":
            gateway_result,

        "internet_ping":
            internet_result,

        "dns_tests":
            dns_results
    }

    filename = (
        "netx_report_"
        + datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )
        + ".json"
    )

    try:

        with open(
            filename,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                report,
                file,
                indent=4,
                ensure_ascii=False
            )

        print()

        print(
            clr(
                "✅ Report exported successfully!",
                C.GREEN
            )
        )

        print(
            f"📄 File: {filename}"
        )

        print(
            f"📁 Location: "
            f"{os.path.abspath(filename)}"
        )

    except Exception as e:

        print(
            clr(
                f"\n❌ Export error: {e}",
                C.RED
            )
        )

    pause()


# ============================================================
# SYSTEM INFORMATION
# ============================================================

def system_info():

    banner()

    print(clr(
        "💻 SYSTEM INFORMATION",
        C.BOLD
    ))

    print("-" * 65)

    import platform

    print(
        f"OS          : {platform.system()}"
    )

    print(
        f"Version     : {platform.version()}"
    )

    print(
        f"Machine     : {platform.machine()}"
    )

    print(
        f"Processor   : {platform.processor()}"
    )

    print(
        f"Hostname    : {socket.gethostname()}"
    )

    print(
        f"Python      : {platform.python_version()}"
    )

    pause()


# ============================================================
# MAIN MENU
# ============================================================

def main():

    while True:

        banner()

        wifi = current_wifi()
        network = network_info()

        # ----------------------------------------------------
        # HEADER
        # ----------------------------------------------------

        if wifi:

            print(
                f"📡 Wi-Fi: "
                f"{clr(wifi['ssid'], C.GREEN)}"
                f"    📶 {wifi['signal']}"
            )

        else:

            print(
                clr(
                    "📡 Wi-Fi: Not connected",
                    C.RED
                )
            )

        print(
            f"🌐 IP: {network['ipv4']}"
            f"    🚪 Gateway: "
            f"{network['gateway']}"
        )

        print()

        # ----------------------------------------------------
        # MENU
        # ----------------------------------------------------

        print(clr("""
╔══════════════════════════════════════════════════════════╗
║                         MENU                             ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  1. 📡 Network Information                              ║
║  2. 📊 Ping Test                                        ║
║  3. 🌐 Internet Test                                    ║
║  4. 🔎 DNS Test                                         ║
║  5. 🔎 DNS Benchmark                                    ║
║  6. 📂 Wi-Fi Profiles                                   ║
║  7. 📶 Wi-Fi Scanner                                    ║
║  8. 📈 Live Ping Monitor                                ║
║  9. 📊 Real-Time Network Monitor                        ║
║ 10. 🚨 Connection Drop Detector                         ║
║ 11. 🧭 Traceroute                                       ║
║ 12. ❤️ Network Health                                   ║
║ 13. 🧠 Network Diagnosis                                ║
║ 14. 💾 Export Report                                    ║
║ 15. 💻 System Information                               ║
║                                                          ║
║  0. ❌ Exit                                             ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
""", C.CYAN))

        choice = input(
            clr(
                "Select option: ",
                C.YELLOW
            )
        ).strip()

        # ----------------------------------------------------
        # OPTIONS
        # ----------------------------------------------------

        if choice == "1":

            show_network_info()

        elif choice == "2":

            ping_menu()

        elif choice == "3":

            internet_test()

        elif choice == "4":

            dns_test()

        elif choice == "5":

            dns_benchmark()

        elif choice == "6":

            wifi_profiles()

        elif choice == "7":

            scan_wifi_networks()

        elif choice == "8":

            live_monitor()

        elif choice == "9":

            real_time_monitor()

        elif choice == "10":

            connection_drop_detector()

        elif choice == "11":

            traceroute()

        elif choice == "12":

            health_check()

        elif choice == "13":

            network_diagnosis()

        elif choice == "14":

            export_report()

        elif choice == "15":

            system_info()

        elif choice == "0":

            print(
                clr(
                    "\n👋 Goodbye!",
                    C.GREEN
                )
            )

            break

        else:

            print(
                clr(
                    "\n❌ Invalid option.",
                    C.RED
                )
            )

            time.sleep(1)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()