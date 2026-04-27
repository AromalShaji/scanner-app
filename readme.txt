# WebScan — Setup & Run Guide

## Files

```
scan_server.py       WebSocket server (the backend)
scanner_backend.py   Cross-platform scanner driver (TWAIN / SANE / pyinsane2)
scan_ui.html         Browser UI — open this in any browser
setup.py             One-time setup: creates .venv + installs dependencies
run.py               Start the server using .venv (no manual activation needed)
```

---

## Step 1 — System dependencies (once only)

### Windows
Nothing extra — TWAIN drivers ship with your scanner.

### macOS
```bash
brew install sane-backends
```

### Linux (Ubuntu / Debian)
```bash
sudo apt install libsane-dev
```

---

## Step 2 — Create the virtual environment (once only)

```bash
python setup.py
```

Creates `.venv/` and installs the right packages for your OS.

---

## Step 3 — Run the server

### Easiest (no activation needed)
```bash
python run.py
```

### Manual (activate venv first)

Windows CMD:
```cmd
.venv\Scripts\activate
python scan_server.py
```

Windows PowerShell:
```powershell
.venv\Scripts\Activate.ps1
python scan_server.py
```

macOS / Linux:
```bash
source .venv/bin/activate
python scan_server.py
```

### Custom port
```bash
python run.py --port 9000
python run.py --host 0.0.0.0 --port 8765
```

---

## Step 4 — Open the UI

Open `scan_ui.html` in any browser. Connects to `ws://127.0.0.1:8765` automatically.

```bash
open scan_ui.html        # macOS
xdg-open scan_ui.html   # Linux
start scan_ui.html       # Windows
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "No scanners found" macOS | `brew install sane-backends` then restart server |
| "No scanners found" Linux | `sudo apt install libsane-dev` then restart server |
| "Cannot reach server" in browser | Make sure `python run.py` is running |
| PowerShell blocks Activate.ps1 | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |