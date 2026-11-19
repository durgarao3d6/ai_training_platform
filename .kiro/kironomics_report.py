#!/usr/bin/env python3
"""Kironomics tracker (Windows-friendly).

Usage:
  kironomics_report.py prompt   - count a prompt, record session start
  kironomics_report.py tool     - count a tool call
  kironomics_report.py report   - send the session report and reset counters
"""
import os, sys, ssl, json, sqlite3, tempfile, time, urllib.request
from pathlib import Path

API_KEY = "8f1f91b2141929a3ca026c63fa2b9a137ee28efa1433384087e0b5f53e68c468"
API_BASE = "https://2q4zt5zl9e.execute-api.us-east-1.amazonaws.com/dev"

TMP = Path(tempfile.gettempdir())
F_TOOLS = TMP / "kironomics_tools"
F_PROMPTS = TMP / "kironomics_prompts"
F_START = TMP / "kironomics_start"


def read_int(path, default=0):
    try:
        return int(Path(path).read_text().strip())
    except Exception:
        return default


def bump(path):
    Path(path).write_text(str(read_int(path) + 1))


def report():
    tools = read_int(F_TOOLS)
    prompts = read_int(F_PROMPTS)
    start = read_int(F_START, int(time.time()))
    elapsed = max(0, int(time.time()) - start)

    plan_data = {}
    try:
        home = Path.home()
        if sys.platform == "darwin":
            db = home / "Library/Application Support/Kiro/User/globalStorage/state.vscdb"
        elif sys.platform.startswith("win"):
            db = Path(os.environ.get("APPDATA", str(home / "AppData/Roaming"))) / "Kiro/User/globalStorage/state.vscdb"
        else:
            db = home / ".config/Kiro/User/globalStorage/state.vscdb"
        if db.exists():
            conn = sqlite3.connect(f"file:{db.as_posix()}?mode=ro&immutable=1", uri=True)
            row = conn.execute("SELECT value FROM ItemTable WHERE key=?", ("kiro.kiroAgent",)).fetchone()
            conn.close()
            if row:
                state = json.loads(row[0])
                usage = state.get("kiro.resourceNotifications.usageState", {})
                breakdowns = usage.get("usageBreakdowns", [])
                if breakdowns:
                    bd = breakdowns[0]
                    plan_data = {
                        "currentUsage": bd.get("currentUsage"),
                        "usageLimit": bd.get("usageLimit"),
                        "percentageUsed": bd.get("percentageUsed"),
                        "resetDate": bd.get("resetDate"),
                    }
    except Exception:
        pass

    payload = {
        "token": API_KEY,
        "tool_calls": tools,
        "prompts": prompts,
        "elapsed_seconds": elapsed,
        **plan_data,
    }

    # Verified TLS only (no unverified fallback).
    try:
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            ctx = ssl.create_default_context()
        req = urllib.request.Request(
            f"{API_BASE}/kironomics/session",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5, context=ctx).read()
    except Exception:
        pass

    for f in (F_TOOLS, F_PROMPTS, F_START):
        try:
            os.remove(f)
        except Exception:
            pass


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    if mode == "prompt":
        if not F_START.exists():
            F_START.write_text(str(int(time.time())))
        bump(F_PROMPTS)
    elif mode == "tool":
        bump(F_TOOLS)
    else:
        report()
    print("ok")


if __name__ == "__main__":
    main()
