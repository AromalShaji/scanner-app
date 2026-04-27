#!/usr/bin/env python3
"""
setup.py — creates .venv and installs the right dependencies for your OS.
Run once:  python setup.py
Then run:  python run.py   (or see README for manual commands)
"""

import subprocess
import sys
import os
import platform

OS = platform.system()   # Windows | Darwin | Linux

CORE = ["websockets==12.0", "Pillow==10.4.0", "fpdf2==2.8.1"]

PLATFORM_PKGS = {
    "Windows": ["twain==2.0.1"],
    "Darwin":  ["pyinsane2"],
    "Linux":   ["python-sane"],
}

VENV_DIR = ".venv"

def run(cmd, **kw):
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, **kw)
    if result.returncode != 0:
        print(f"\n[ERROR] Command failed: {' '.join(cmd)}")
        sys.exit(result.returncode)
    return result

def pip(*packages):
    run([pip_exe, "install", "--upgrade", *packages])

# ── resolve executables inside venv ──────────────────────────────────────────
if OS == "Windows":
    python_exe = os.path.join(VENV_DIR, "Scripts", "python.exe")
    pip_exe    = os.path.join(VENV_DIR, "Scripts", "pip.exe")
else:
    python_exe = os.path.join(VENV_DIR, "bin", "python")
    pip_exe    = os.path.join(VENV_DIR, "bin", "pip")

# ── pre-flight system checks ──────────────────────────────────────────────────
if OS == "Darwin":
    sane = subprocess.run(["brew", "list", "sane-backends"],
                          capture_output=True, text=True)
    if sane.returncode != 0:
        print("\n[macOS] sane-backends not found.")
        print("  Install it first:  brew install sane-backends\n")
        sys.exit(1)

elif OS == "Linux":
    sane = subprocess.run(["dpkg", "-s", "libsane-dev"],
                          capture_output=True, text=True)
    if sane.returncode != 0:
        print("\n[Linux] libsane-dev not found.")
        print("  Install it first:  sudo apt install libsane-dev\n")
        sys.exit(1)

# ── create venv ───────────────────────────────────────────────────────────────
if not os.path.isdir(VENV_DIR):
    print(f"\n[1/3] Creating virtual environment in {VENV_DIR}/")
    run([sys.executable, "-m", "venv", VENV_DIR])
else:
    print(f"\n[1/3] Virtual environment already exists at {VENV_DIR}/")

# ── upgrade pip ───────────────────────────────────────────────────────────────
print("\n[2/3] Upgrading pip…")
pip("pip")

# ── install packages ──────────────────────────────────────────────────────────
extra = PLATFORM_PKGS.get(OS, [])
print(f"\n[3/3] Installing packages for {OS}…")
pip(*CORE, *extra)

# ── done ─────────────────────────────────────────────────────────────────────
activate = (
    rf"  {VENV_DIR}\Scripts\activate"  if OS == "Windows"
    else f"  source {VENV_DIR}/bin/activate"
)
print(f"""
Done!

To activate the virtual environment:
{activate}

Then start the scan server:
  python scan_server.py

Or just run without activating:
  python run.py
""")