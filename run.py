#!/usr/bin/env python3
"""
run.py — starts scan_server.py using the .venv Python automatically.
No need to activate the venv manually.

Usage:
  python run.py [--port 8765] [--host 127.0.0.1]
"""

import subprocess
import sys
import os
import platform
import argparse

OS     = platform.system()
VENV   = ".venv"

if OS == "Windows":
    VENV_PYTHON = os.path.join(VENV, "Scripts", "python.exe")
else:
    VENV_PYTHON = os.path.join(VENV, "bin", "python")

if not os.path.isfile(VENV_PYTHON):
    print("[ERROR] .venv not found. Run setup first:\n  python setup.py")
    sys.exit(1)

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--host", default="127.0.0.1")
parser.add_argument("--port", default="8765")
args, _ = parser.parse_known_args()

server = os.path.join(os.path.dirname(__file__), "scan_server.py")

print(f"Starting WebScan server → ws://{args.host}:{args.port}")
print(f"Open scan_ui.html in your browser\n")

try:
    subprocess.run([VENV_PYTHON, server, "--host", args.host, "--port", args.port])
except KeyboardInterrupt:
    print("\nServer stopped.")