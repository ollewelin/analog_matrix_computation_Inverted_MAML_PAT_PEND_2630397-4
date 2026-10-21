#!/usr/bin/env python3
"""
Data Log Quota Guard & Manager for MAML Hardware Test Logs.
Enforces a hard ceiling of 100 MB total log/export data.
Protects root filesystem from filling up while permitting burst data dumps on user command.
"""

import sys
import os
import glob
from pathlib import Path
import argparse
from typing import List, Dict, Tuple

# Default Quota Ceiling: 100 MB (in megabytes = 100 * 1024 * 1024 bytes)
DEFAULT_MAX_MB = 100.0
DEFAULT_TARGET_PRUNE_MB = 80.0

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DOCS_DIR = REPO_ROOT / "FPGA_code" / "docs"

# Transient dump patterns (eligible for pruning if quota exceeded)
TRANSIENT_LOG_PATTERNS = [
    "maml_gui_full_dump_*.json",
    "maml_gui_hadamard_dump_*.csv",
    "maml_gui_cell_eval_*.json",
    "multiplier_dynamics_self_test_*.csv",
    "multiplier_dynamics_self_test_*.json",
    "*_dump_*.csv",
    "*_dump_*.json",
    "*_raw_capture_*.bin",
    "temp_*.csv",
    "temp_*.json",
    "temp_*.log",
]

# All log/export patterns tracked under the 100 MB quota
ALL_QUOTA_PATTERNS = [
    "*.csv",
    "maml_gui_*.json",
    "*_dump_*.json",
    "*_captures.json",
    "*_live_results.json",
    "*.bin",
    "*.log",
    "olle_log",
]

# Protected extensions: never prune these
PROTECTED_EXTENSIONS = {".md", ".pdf", ".sv", ".v", ".c", ".h", ".py", ".xml"}


def scan_quota_files(docs_dir: Path = DOCS_DIR) -> List[Path]:
    """Find all files in docs_dir that count towards the data log quota."""
    if not docs_dir.exists():
        return []

    found = set()
    for pattern in ALL_QUOTA_PATTERNS:
        for p in docs_dir.glob(pattern):
            if p.is_file() and p.suffix.lower() not in PROTECTED_EXTENSIONS:
                found.add(p)
    return sorted(list(found), key=lambda x: x.stat().st_mtime)


def get_transient_files(docs_dir: Path = DOCS_DIR) -> List[Path]:
    """Find transient dump files eligible for automatic pruning (oldest first)."""
    if not docs_dir.exists():
        return []

    found = set()
    for pattern in TRANSIENT_LOG_PATTERNS:
        for p in docs_dir.glob(pattern):
            if p.is_file() and p.suffix.lower() not in PROTECTED_EXTENSIONS:
                found.add(p)
    # Sort by modification time ascending (oldest first)
    return sorted(list(found), key=lambda x: x.stat().st_mtime)


def get_quota_status(max_mb: float = DEFAULT_MAX_MB, docs_dir: Path = DOCS_DIR) -> Dict:
    """Return dictionary with current byte usage, limit, and file breakdown."""
    files = scan_quota_files(docs_dir)
    total_bytes = sum(f.stat().st_size for f in files)
    max_bytes = int(max_mb * 1024 * 1024)
    usage_mb = total_bytes / (1024 * 1024)
    avail_mb = max(0.0, max_mb - usage_mb)
    usage_pct = (total_bytes / max_bytes * 100.0) if max_bytes > 0 else 0.0

    return {
        "docs_dir": str(docs_dir),
        "total_files": len(files),
        "total_bytes": total_bytes,
        "usage_mb": usage_mb,
        "max_mb": max_mb,
        "avail_mb": avail_mb,
        "usage_pct": usage_pct,
        "is_exceeded": total_bytes > max_bytes,
        "files": files,
    }


def prune_oldest_logs(
    target_mb: float = DEFAULT_TARGET_PRUNE_MB,
    max_mb: float = DEFAULT_MAX_MB,
    docs_dir: Path = DOCS_DIR,
    dry_run: bool = False,
) -> Tuple[int, int]:
    """
    Prune oldest transient dump files until total usage falls below target_mb.
    Returns (files_removed_count, bytes_freed).
    """
    target_bytes = int(target_mb * 1024 * 1024)
    status = get_quota_status(max_mb, docs_dir)
    current_bytes = status["total_bytes"]

    if current_bytes <= target_bytes:
        return 0, 0

    transient = get_transient_files(docs_dir)
    removed_count = 0
    bytes_freed = 0

    for f in transient:
        if current_bytes - bytes_freed <= target_bytes:
            break
        sz = f.stat().st_size
        if not dry_run:
            try:
                f.unlink()
            except OSError as e:
                print(f"Warning: could not delete {f}: {e}")
                continue
        bytes_freed += sz
        removed_count += 1
        tag = "[DRY-RUN] Would remove" if dry_run else "Removed"
        print(f"  - {tag}: {f.name} ({sz / 1024:.1f} KB)")

    return removed_count, bytes_freed


def enforce_quota_before_write(
    incoming_bytes: int = 0,
    max_mb: float = DEFAULT_MAX_MB,
    auto_prune: bool = True,
    docs_dir: Path = DOCS_DIR,
) -> bool:
    """
    Check if writing incoming_bytes would breach the 100 MB quota.
    If so and auto_prune is True, prune transient logs to make room.
    Returns True if safe to write, False if quota exceeded and cannot free enough room.
    """
    status = get_quota_status(max_mb, docs_dir)
    projected_bytes = status["total_bytes"] + incoming_bytes
    max_bytes = int(max_mb * 1024 * 1024)

    if projected_bytes <= max_bytes:
        return True

    if auto_prune:
        target_mb = max_mb * 0.8
        prune_oldest_logs(target_mb=target_mb, max_mb=max_mb, docs_dir=docs_dir, dry_run=False)
        updated = get_quota_status(max_mb, docs_dir)
        return (updated["total_bytes"] + incoming_bytes) <= max_bytes

    return False


def print_status_table(status: Dict):
    print("=" * 70)
    print(" MAML HARDWARE DATA LOG QUOTA STATUS (MAX 100 MB CEILING)")
    print("=" * 70)
    print(f" Log Directory:   {status['docs_dir']}")
    print(f" Total Log Files: {status['total_files']}")
    print(f" Current Usage:   {status['usage_mb']:.2f} MB / {status['max_mb']:.1f} MB ({status['usage_pct']:.1f}%)")
    print(f" Remaining Quota: {status['avail_mb']:.2f} MB")
    print("-" * 70)

    if status["is_exceeded"]:
        print(" [!] ALERT: 100 MB DATA LOG QUOTA HAS BEEN EXCEEDED!")
    elif status["usage_pct"] >= 80.0:
        print(" [!] WARNING: Data log usage is above 80% of quota.")
    else:
        print(" [OK] Data log usage is well within safe 100 MB quota bounds.")

    print("-" * 70)
    print(f"{'Filename':<42} {'Size (KB)':>12} {'Modified':>14}")
    print("-" * 70)

    from datetime import datetime
    for f in status["files"]:
        sz_kb = f.stat().st_size / 1024.0
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        name = f.name
        if len(name) > 40:
            name = name[:37] + "..."
        print(f"{name:<42} {sz_kb:>12.1f} {mtime:>14}")
    print("=" * 70)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check and manage MAML Hardware Data Log Quota (max 100 MB)")
    parser.add_argument("--check", action="store_true", help="Exit 0 if within quota, exit 1 if exceeded")
    parser.add_argument("--status", action="store_true", help="Display detailed table of all log files and quota")
    parser.add_argument("--prune", action="store_true", help="Prune oldest transient dump files to target MB")
    parser.add_argument("--max-mb", type=float, default=DEFAULT_MAX_MB, help=f"Max quota in MB (default: {DEFAULT_MAX_MB})")
    parser.add_argument("--target-mb", type=float, default=DEFAULT_TARGET_PRUNE_MB, help=f"Prune target in MB (default: {DEFAULT_TARGET_PRUNE_MB})")
    parser.add_argument("--dry-run", action="store_true", help="Simulate pruning without deleting files")

    args = parser.parse_args()

    # Default action if no flag specified is status
    if not (args.check or args.status or args.prune):
        args.status = True

    if args.prune:
        print(f"Pruning transient dump files in {DOCS_DIR} to target <= {args.target_mb} MB...")
        count, freed = prune_oldest_logs(
            target_mb=args.target_mb,
            max_mb=args.max_mb,
            docs_dir=DOCS_DIR,
            dry_run=args.dry_run,
        )
        print(f"Pruning complete: {count} files removed, {freed / (1024*1024):.2f} MB freed.")
        return 0

    status = get_quota_status(max_mb=args.max_mb, docs_dir=DOCS_DIR)

    if args.status:
        print_status_table(status)

    if args.check:
        if status["is_exceeded"]:
            print(f"[FAIL] Data log size {status['usage_mb']:.2f} MB exceeds {args.max_mb} MB!", file=sys.stderr)
            return 1
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
