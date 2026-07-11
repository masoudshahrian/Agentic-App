# -*- coding: utf-8 -*-
"""
Starts/stops the vision counter script (main.py) as a subprocess, controlled
from the dashboard's Start/Stop button.

IMPORTANT: the vision app has its own dependencies (opencv, torch, ultralytics...),
which usually live in a DIFFERENT virtual environment than this agent's venv.
So we must launch it using ITS OWN python.exe, not the one running this server.
Configure the correct paths in config/settings.json -> "vision_app".
"""
import subprocess
import time
import os

from .accounting import load_settings

_process = None
_started_at = None


def _cfg():
    return load_settings().get("vision_app", {})


def start_vision():
    global _process, _started_at

    if is_running():
        return {"ok": False, "message": "Vision app is already running.", "pid": _process.pid}

    cfg = _cfg()
    python_exe = cfg.get("python_executable")
    script_path = cfg.get("script_path")
    workdir = cfg.get("working_directory") or (os.path.dirname(script_path) if script_path else None)

    if not python_exe or not script_path:
        return {"ok": False, "message": "vision_app.python_executable / script_path not set in config/settings.json"}
    if not os.path.isfile(python_exe):
        return {"ok": False, "message": f"python_executable not found: {python_exe}"}
    if not os.path.isfile(script_path):
        return {"ok": False, "message": f"script_path not found: {script_path}"}

    try:
        creationflags = 0
        if os.name == "nt":
            # Opens the vision app in its own console window (so its cv2 window/logs show up)
            creationflags = subprocess.CREATE_NEW_CONSOLE
        _process = subprocess.Popen(
            [python_exe, script_path],
            cwd=workdir,
            creationflags=creationflags,
        )
        _started_at = time.time()
        return {"ok": True, "message": "Vision app started.", "pid": _process.pid}
    except Exception as e:
        return {"ok": False, "message": f"Failed to start vision app: {e}"}


def stop_vision():
    global _process, _started_at
    if not is_running():
        return {"ok": False, "message": "Vision app is not running."}
    try:
        _process.terminate()
        _process = None
        _started_at = None
        return {"ok": True, "message": "Vision app stopped."}
    except Exception as e:
        return {"ok": False, "message": f"Failed to stop vision app: {e}"}


def is_running() -> bool:
    return _process is not None and _process.poll() is None


def status():
    running = is_running()
    uptime = int(time.time() - _started_at) if (running and _started_at) else 0
    return {
        "running": running,
        "pid": _process.pid if running else None,
        "uptime_seconds": uptime,
    }
