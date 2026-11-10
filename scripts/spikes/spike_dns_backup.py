"""Back up and safely restore DNS settings for active Windows adapters.

Reading and writing a JSON backup is the default dry-run behavior.  Restoring
system settings requires ``--restore``, ``--execute`` and the exact confirmation
token ``RESTORE-DNS``.  Restore verifies the adapter GUID before changing it and
flushes the Windows DNS cache only after all requested changes succeed.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import ipaddress
import json
import platform
from pathlib import Path
import socket
import subprocess
import sys
from typing import Any
from uuid import UUID


BACKUP_SCHEMA = "ogk.dns-backup.v1"

READ_DNS_POWERSHELL = r"""
$ErrorActionPreference = 'Stop'
$result = @()
$adapters = Get-NetAdapter | Where-Object {
    $_.Status -eq 'Up' -and $_.InterfaceDescription -notmatch 'Loopback'
}
foreach ($adapter in $adapters) {
    $index = [int]$adapter.InterfaceIndex
    $guid = ([Guid]$adapter.InterfaceGuid).ToString('B')
    $v4 = Get-DnsClientServerAddress -InterfaceIndex $index -AddressFamily IPv4
    $v6 = Get-DnsClientServerAddress -InterfaceIndex $index -AddressFamily IPv6
    $ip4 = Get-NetIPInterface -InterfaceIndex $index -AddressFamily IPv4 -ErrorAction SilentlyContinue
    $ip6 = Get-NetIPInterface -InterfaceIndex $index -AddressFamily IPv6 -ErrorAction SilentlyContinue

    # A non-empty NameServer value is the static override. DhcpNameServer is the
    # value supplied automatically. Inspect both TCP/IP registry branches so
    # IPv4 and IPv6 can be reported independently.
    $reg4Path = "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\$guid"
    $reg6Path = "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip6\Parameters\Interfaces\$guid"
    $reg4 = Get-ItemProperty -LiteralPath $reg4Path -ErrorAction SilentlyContinue
    $reg6 = Get-ItemProperty -LiteralPath $reg6Path -ErrorAction SilentlyContinue
    $staticRaw = @($reg4.NameServer, $reg6.NameServer) | Where-Object { $_ }
    $staticAddresses = @()
    foreach ($raw in $staticRaw) {
        $staticAddresses += ($raw -split '[,; ]+' | Where-Object { $_ })
    }
    $staticV4 = @($staticAddresses | Where-Object { $_ -match '^\d{1,3}(\.\d{1,3}){3}$' })
    $staticV6 = @($staticAddresses | Where-Object { $_ -match ':' })

    $result += [pscustomobject]@{
        interface_index = $index
        interface_alias = [string]$adapter.Name
        interface_description = [string]$adapter.InterfaceDescription
        interface_guid = $guid
        mac_address = [string]$adapter.MacAddress
        status = [string]$adapter.Status
        ipv4 = [pscustomobject]@{
            dns_source = $(if ($staticV4.Count -gt 0) { 'STATIC' } else { 'DHCP' })
            dhcp_enabled = [bool]($ip4.Dhcp -contains 'Enabled')
            server_addresses = @($v4.ServerAddresses | Where-Object { $_ })
        }
        ipv6 = [pscustomobject]@{
            dns_source = $(if ($staticV6.Count -gt 0) { 'STATIC' } else { 'DHCP' })
            dhcp_enabled = [bool]($ip6.Dhcp -contains 'Enabled')
            server_addresses = @($v6.ServerAddresses | Where-Object { $_ })
        }
    }
}
@($result) | ConvertTo-Json -Depth 6 -Compress
"""


def require_windows() -> None:
    if platform.system() != "Windows":
        raise RuntimeError("This spike must be run on a Windows VM")


def run_powershell(script: str) -> str:
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"PowerShell failed ({result.returncode}): {detail}")
    return result.stdout.strip()


def read_active_adapters() -> list[dict[str, Any]]:
    require_windows()
    output = run_powershell(READ_DNS_POWERSHELL)
    if not output:
        return []
    parsed = json.loads(output)
    return parsed if isinstance(parsed, list) else [parsed]


def backup_document(adapters: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": BACKUP_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "adapters": adapters,
    }


def default_backup_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path("runtime") / "dns-backups" / f"dns-backup-{stamp}.json"


def write_backup(document: dict[str, Any], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_backup(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != BACKUP_SCHEMA:
        raise ValueError(f"unsupported backup schema: {document.get('schema')!r}")
    if not isinstance(document.get("adapters"), list):
        raise ValueError("backup must contain an adapters list")
    return document


def ps_single_quoted(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def validated_servers(values: object, family: int) -> list[str]:
    if not isinstance(values, list):
        raise ValueError("server_addresses must be a list")
    result: list[str] = []
    for value in values:
        parsed = ipaddress.ip_address(str(value))
        if parsed.version != family:
            raise ValueError(f"{value} is not IPv{family}")
        result.append(str(parsed))
    return result


def family_restore_command(index: int, family: str, config: dict[str, Any]) -> str:
    source = str(config.get("dns_source", "")).upper()
    version = 4 if family == "IPv4" else 6
    servers = validated_servers(config.get("server_addresses", []), version)
    selector = (
        f"Get-DnsClientServerAddress -InterfaceIndex {index} "
        f"-AddressFamily {family} -ErrorAction Stop"
    )
    if source == "DHCP":
        return f"{selector} | Set-DnsClientServerAddress -ResetServerAddresses -ErrorAction Stop"
    if source != "STATIC" or not servers:
        raise ValueError(f"{family} has invalid source/addresses: {source}, {servers}")
    address_list = ",".join(ps_single_quoted(value) for value in servers)
    return (
        f"{selector} | Set-DnsClientServerAddress "
        f"-ServerAddresses @({address_list}) -ErrorAction Stop"
    )


def restore_script(adapter: dict[str, Any]) -> str:
    index = int(adapter["interface_index"])
    guid = str(UUID(str(adapter["interface_guid"]).strip("{}"))).upper()
    v4 = family_restore_command(index, "IPv4", adapter["ipv4"])
    v6 = family_restore_command(index, "IPv6", adapter["ipv6"])
    return "\n".join(
        [
            "$ErrorActionPreference = 'Stop'",
            f"$adapter = Get-NetAdapter -InterfaceIndex {index} -ErrorAction Stop",
            f"if ($adapter.InterfaceGuid.ToString().ToUpperInvariant() -ne '{guid}') {{",
            "  throw 'Adapter GUID no longer matches backup; refusing restore'",
            "}",
            v4,
            v6,
        ]
    )


def selected_adapters(
    document: dict[str, Any], interface_index: int | None
) -> list[dict[str, Any]]:
    adapters = document["adapters"]
    if interface_index is None:
        return adapters
    selected = [
        item for item in adapters if int(item["interface_index"]) == interface_index
    ]
    if not selected:
        raise ValueError(f"interface index {interface_index} is not in the backup")
    return selected


def perform_restore(
    document: dict[str, Any],
    interface_index: int | None,
    execute: bool,
    confirmation: str | None,
) -> None:
    scripts = [restore_script(item) for item in selected_adapters(document, interface_index)]
    print("DNS restore plan:")
    for script in scripts:
        print("\n" + script)
    print("\nFinal step after successful restore: ipconfig /flushdns")
    if not execute:
        print("Dry-run only; no adapter setting was changed.")
        return
    if confirmation != "RESTORE-DNS":
        raise RuntimeError(
            "Refusing restore: pass --confirm-restore RESTORE-DNS after reviewing the plan"
        )
    require_windows()
    for script in scripts:
        run_powershell(script)
    result = subprocess.run(
        ["ipconfig.exe", "/flushdns"], check=False, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"DNS restored but flushdns failed: {result.stderr.strip()}")
    print("DNS settings restored and resolver cache flushed.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Backup JSON destination")
    parser.add_argument("--restore", type=Path, help="Existing backup to restore")
    parser.add_argument("--interface-index", type=int, help="Limit restore to one adapter")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Back up or print a restore plan only (the default)",
    )
    mode.add_argument("--execute", action="store_true", help="Permit DNS restore")
    parser.add_argument("--confirm-restore", help="Required token: RESTORE-DNS")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.restore:
            document = load_backup(args.restore)
            perform_restore(
                document, args.interface_index, args.execute, args.confirm_restore
            )
            return 0
        adapters = read_active_adapters()
        if not adapters:
            raise RuntimeError("No active non-loopback network adapter was found")
        destination = args.output or default_backup_path()
        document = backup_document(adapters)
        write_backup(document, destination)
        # Keep console output portable across legacy Windows code pages; the
        # repository's absolute path may contain characters they cannot encode.
        print(f"Backed up {len(adapters)} active adapter(s) to {destination}")
        print("No DNS setting was changed.")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
