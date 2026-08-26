#!/usr/bin/env python3
"""
Background Scheduler for Autonomous Target Sweeps and Continuous Commit Watching.
Maintains persistent state in cache/scanner_state.json and emits heartbeat in cache/scheduler_heartbeat.json.
"""
import os
import sys
import time
import json
import argparse
import signal
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from scripts.batch_scanner import scan_target, GitDeltaScanner

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [Scheduler] %(message)s")
logger = logging.getLogger("EthHunterScheduler")

STATE_FILE = BASE_DIR / "cache" / "scanner_state.json"
HEARTBEAT_FILE = BASE_DIR / "cache" / "scheduler_heartbeat.json"


def load_state() -> Dict[str, Any]:
    """Loads previous scanner state from disk."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            logger.debug(f"Failed to load scanner state: {e}")
    return {}


def save_state(state: Dict[str, Any]) -> None:
    """Persists scanner state to cache/scanner_state.json."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to save scanner state: {e}")


def write_heartbeat(status: str = "running", extra: Optional[Dict[str, Any]] = None) -> None:
    """Emits heartbeat status and timestamp into cache/scheduler_heartbeat.json."""
    HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": status,
        "timestamp": time.time(),
        "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if extra:
        payload.update(extra)
    try:
        HEARTBEAT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception as e:
        logger.debug(f"Failed to write heartbeat: {e}")


def run_scheduler_sweep(targets: List[str], delta_mode: bool = True) -> None:
    """Executes a single sweep over target repositories/directories with state tracking."""
    state = load_state()
    write_heartbeat("sweeping", {"target_count": len(targets)})
    logger.info(f"🤖 Starting scheduled automated batch sweep across {len(targets)} target(s)...")

    for target in targets:
        try:
            target_state = state.get(target, {})
            last_head = target_state.get("last_head", "")
            is_git = target.startswith("http") or target.endswith(".git")

            if is_git:
                repo_dir, old_head, new_head, is_updated = GitDeltaScanner.clone_or_update(target)
                if delta_mode and not is_updated and last_head == new_head and last_head != "":
                    logger.info(f"Target {target} is unchanged at commit {new_head[:8]}. Skipping.")
                    continue
                scan_target(target, delta_mode=delta_mode, base_ref=last_head or "HEAD~1", head_ref=new_head)
                state[target] = {
                    "last_head": new_head,
                    "last_scan_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "status": "success",
                }
            else:
                scan_target(target, delta_mode=delta_mode)
                state[target] = {
                    "last_head": "local",
                    "last_scan_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "status": "success",
                }
            save_state(state)
        except Exception as e:
            logger.error(f"❌ Error sweeping {target}: {e}")
            state[target] = {
                "last_scan_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "status": f"error: {e}",
            }
            save_state(state)

    write_heartbeat("idle")
    logger.info("✅ Scheduled sweep completed successfully.")


def main():
    parser = argparse.ArgumentParser(description="EthAudit-Agent Autonomous Scheduler Daemon")
    parser.add_argument("--interval", type=int, default=21600, help="Sweep interval in seconds (default: 21600 = 6h)")
    parser.add_argument("--once", action="store_true", help="Run a single sweep pass and exit")
    parser.add_argument("--delta", action="store_true", default=True, help="Enable git delta diff scanning (default: True)")
    parser.add_argument("--targets", nargs="*", default=[], help="List of target repositories or files to watch")
    parser.add_argument("--daemon", action="store_true", help="Run continuously in foreground daemon mode")

    args = parser.parse_args()

    targets = list(args.targets) if args.targets else []
    if not targets:
        # 1. Check config/targets.json
        targets_cfg = BASE_DIR / "config" / "targets.json"
        if targets_cfg.exists():
            try:
                targets_data = json.loads(targets_cfg.read_text(encoding="utf-8"))
                targets = targets_data.get("repositories", [])
            except Exception:
                pass

    if not targets:
        # 2. Check contracts directory and subdirectories
        contracts_dirs = [
            BASE_DIR / "contracts" / "examples",
            BASE_DIR / "contracts",
            BASE_DIR / "cache" / "contracts",
            BASE_DIR / "examples",
        ]
        for cdir in contracts_dirs:
            if cdir.exists():
                for sol in cdir.rglob("*.sol"):
                    if not any(skip in sol.name.lower() for skip in ["test", "mock"]):
                        targets.append(str(sol))

    logger.info(f"🚀 Eth-Hunter Background Scheduler Initialized with {len(targets)} targets.")

    if args.once:
        run_scheduler_sweep(targets, delta_mode=args.delta)
        return

    # Continuous loop
    run_scheduler_sweep(targets, delta_mode=args.delta)
    while True:
        try:
            logger.info(f"Sleeping for {args.interval}s until next sweep...")
            time.sleep(args.interval)
            run_scheduler_sweep(targets, delta_mode=args.delta)
        except KeyboardInterrupt:
            logger.info("Stopping scheduler via SIGINT...")
            write_heartbeat("stopped")
            break
        except Exception as e:
            logger.error(f"Scheduler loop error: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()
