#!/usr/bin/env python3
"""Explicit opt-in local poller for an existing folder knowledge base."""
from __future__ import annotations

import argparse
import contextlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid
import warnings
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import folderdb


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def paths(root):
    state_dir = root / ".filedb" / "watch"
    return state_dir, state_dir / "state.json", state_dir / "stop.request", state_dir / "watch.jsonl", state_dir / "start.lock"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".watch-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if Path(temp).exists():
            Path(temp).unlink()


def read_json(path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def append_log(path, event, **fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 5 * 1024 * 1024:
        old = path.with_suffix(".jsonl.1")
        if old.exists():
            old.unlink()
        os.replace(path, old)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps({"at": utc_now(), "event": event, **fields}, ensure_ascii=False) + "\n")


def watch_status(root):
    _, state_path, stop_path, _, _ = paths(root)
    state = read_json(state_path)
    if not state:
        return {"status": "stopped", "configured": False}
    age = max(0, time.time() - state.get("heartbeat_epoch", state.get("started_epoch", 0)))
    threshold = max(60, int(state.get("interval_seconds", 30)) * 3 + int(state.get("debounce_seconds", 2)) + 10)
    status = state.get("status", "unknown")
    if status in {"starting", "running", "stop_requested"} and age > threshold:
        status = "stale"
    if stop_path.exists() and status == "running":
        request = read_json(stop_path, {})
        if request.get("token") == state.get("token"):
            status = "stop_requested"
    return {**state, "status": status, "heartbeat_age_seconds": round(age, 1), "configured": True}


def update_state(root, state, **changes):
    _, state_path, _, _, _ = paths(root)
    state.update(changes)
    state["heartbeat_at"] = utc_now()
    state["heartbeat_epoch"] = time.time()
    write_json(state_path, state)


def wait_interruptible(seconds, root, token):
    until = time.monotonic() + max(0, seconds)
    while time.monotonic() < until:
        _, state_path, stop_path, _, _ = paths(root)
        state = read_json(state_path, {})
        request = read_json(stop_path, {})
        if state.get("token") != token or request.get("token") == token:
            return False
        time.sleep(min(1, max(0, until - time.monotonic())))
    return True


def run_worker(root, token, interval_seconds=30, debounce_seconds=2, full_interval_hours=24, max_cycles=None):
    if folderdb.identity(root).get("kind") != "managed":
        raise ValueError("Watcher only runs for a recognized managed library")
    state_dir, state_path, stop_path, log_path, _ = paths(root)
    state = read_json(state_path, {})
    if state.get("token") != token:
        raise ValueError("Watcher token does not match the active instance")
    state.update({"status": "running", "pid": os.getpid(), "started_at": state.get("started_at", utc_now()),
        "interval_seconds": interval_seconds, "debounce_seconds": debounce_seconds,
        "full_interval_hours": full_interval_hours, "last_full_epoch": state.get("last_full_epoch", 0)})
    update_state(root, state)
    append_log(log_path, "started", interval_seconds=interval_seconds, debounce_seconds=debounce_seconds,
        full_interval_hours=full_interval_hours, scope="refresh-only-no-model")
    cycles = 0
    try:
        while True:
            current = read_json(state_path, {})
            request = read_json(stop_path, {})
            if current.get("token") != token or request.get("token") == token:
                update_state(root, state, status="stopped", stopped_at=utc_now())
                if stop_path.exists() and request.get("token") == token:
                    stop_path.unlink()
                append_log(log_path, "stopped", cycles=cycles)
                return {"status": "stopped", "cycles": cycles}
            full_due = time.time() - state.get("last_full_epoch", 0) >= full_interval_hours * 3600
            observed = folderdb.status(root)
            if observed.get("library", {}).get("kind") != "managed":
                raise ValueError("Library catalog became unavailable or incompatible")
            dirty = observed.get("needs_scan", False) or observed.get("needs_index", False)
            if full_due or dirty:
                if not full_due and debounce_seconds:
                    if not wait_interruptible(debounce_seconds, root, token):
                        continue
                    stable = folderdb.status(root)
                    if stable.get("snapshot_fingerprint") != observed.get("snapshot_fingerprint"):
                        append_log(log_path, "change_still_settling", before=observed.get("snapshot_fingerprint"), after=stable.get("snapshot_fingerprint"))
                        update_state(root, state)
                        cycles += 1
                        if max_cycles is not None and cycles >= max_cycles:
                            break
                        if not wait_interruptible(interval_seconds, root, token):
                            continue
                        continue
                report = folderdb.refresh(root, full=full_due)
                if full_due:
                    state["last_full_epoch"] = time.time()
                    state["last_full_at"] = utc_now()
                update_state(root, state, last_refresh_at=utc_now(), last_refresh_status="refreshed")
                append_log(log_path, "refresh_completed", full=full_due, scan_counts=report["scan"].get("counts"),
                    files=report["scan"].get("files"), generated_indexes=report["index"].get("generated_indexes"))
            else:
                update_state(root, state)
            cycles += 1
            if max_cycles is not None and cycles >= max_cycles:
                break
            if not wait_interruptible(interval_seconds, root, token):
                continue
    except Exception as exc:
        update_state(root, state, status="failed", error=str(exc)[:1000], stopped_at=utc_now())
        append_log(log_path, "worker_failed", error=str(exc)[:1000])
        return {"status": "failed", "error": str(exc)}
    update_state(root, state, status="stopped", stopped_at=utc_now())
    append_log(log_path, "stopped", cycles=cycles, reason="bounded test or worker loop ended")
    return {"status": "stopped", "cycles": cycles}


def start(root, interval_seconds=30, debounce_seconds=2, full_interval_hours=24):
    if folderdb.identity(root).get("kind") != "managed":
        raise ValueError("Create and scan the library before starting its watcher")
    if not 1 <= interval_seconds <= 86400 or not 0 <= debounce_seconds <= 300 or not 1 <= full_interval_hours <= 720:
        raise ValueError("Use interval 1..86400 seconds, debounce 0..300 seconds, full interval 1..720 hours")
    state_dir, state_path, stop_path, log_path, start_lock = paths(root)
    state_dir.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    try:
        with start_lock.open("x", encoding="ascii") as stream:
            stream.write(token)
    except FileExistsError:
        raise ValueError("Another watcher start operation is in progress; inspect watch status")
    try:
        existing = watch_status(root)
        if existing.get("status") in {"starting", "running", "stop_requested"}:
            raise ValueError("Watcher is already active")
        if stop_path.exists():
            stop_path.unlink()
        state = {"token": token, "status": "starting", "root": str(root), "started_at": utc_now(),
            "started_epoch": time.time(), "heartbeat_at": utc_now(), "heartbeat_epoch": time.time(),
            "interval_seconds": interval_seconds, "debounce_seconds": debounce_seconds,
            "full_interval_hours": full_interval_hours}
        write_json(state_path, state)
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "_worker", "--root", str(root),
            "--token", token, "--interval-seconds", str(interval_seconds), "--debounce-seconds", str(debounce_seconds),
            "--full-interval-hours", str(full_interval_hours)]
        kwargs = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL,
            "close_fds": True, "cwd": str(HERE)}
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0x00000008) | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        else:
            kwargs["start_new_session"] = True
        with warnings.catch_warnings():
            # The parent intentionally detaches; the cooperative stop token is its lifecycle API.
            warnings.filterwarnings("ignore", message="subprocess .* is still running", category=ResourceWarning)
            process = subprocess.Popen(command, **kwargs)
            pid = process.pid
            del process
        state["pid"] = pid
        write_json(state_path, state)
        append_log(log_path, "start_requested", pid=pid, interval_seconds=interval_seconds,
            debounce_seconds=debounce_seconds, full_interval_hours=full_interval_hours)
        return {"status": "starting", "pid": pid, "state_file": str(state_path), "log_file": str(log_path),
            "auto_start": False, "wakes_model": False}
    finally:
        if start_lock.exists() and start_lock.read_text(encoding="ascii") == token:
            start_lock.unlink()


def stop(root):
    _, state_path, stop_path, log_path, _ = paths(root)
    state = read_json(state_path)
    if not state:
        return {"status": "stopped", "requested": False}
    current = watch_status(root)
    if current["status"] in {"stopped", "stale", "failed"}:
        return {"status": current["status"], "requested": False}
    write_json(stop_path, {"token": state["token"], "requested_at": utc_now()})
    append_log(log_path, "stop_requested", pid=state.get("pid"))
    return {"status": "stop_requested", "requested": True, "pid": state.get("pid")}


def tail_log(root, lines=50):
    if not 1 <= lines <= 500:
        raise ValueError("lines must be 1..500")
    _, _, _, log_path, _ = paths(root)
    if not log_path.exists():
        return {"path": str(log_path), "lines": []}
    content = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    return {"path": str(log_path), "lines": content[-lines:], "total_lines_in_current_log": len(content)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("start", "stop", "status", "log", "_worker"):
        item = sub.add_parser(name)
        item.add_argument("--root", required=True)
        if name == "start":
            item.add_argument("--interval-seconds", type=int, default=30)
            item.add_argument("--debounce-seconds", type=int, default=2)
            item.add_argument("--full-interval-hours", type=int, default=24)
        if name == "log":
            item.add_argument("--tail-lines", type=int, default=50)
        if name == "_worker":
            item.add_argument("--token", required=True)
            item.add_argument("--interval-seconds", type=int, required=True)
            item.add_argument("--debounce-seconds", type=int, required=True)
            item.add_argument("--full-interval-hours", type=int, required=True)
    args = parser.parse_args()
    root = folderdb.root_path(args.root)
    if args.command == "start":
        result = start(root, args.interval_seconds, args.debounce_seconds, args.full_interval_hours)
    elif args.command == "stop":
        result = stop(root)
    elif args.command == "status":
        result = watch_status(root)
    elif args.command == "log":
        result = tail_log(root, args.tail_lines)
    else:
        result = run_worker(root, args.token, args.interval_seconds, args.debounce_seconds, args.full_interval_hours)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
