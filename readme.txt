# WebScan — Setup & Run Guide

## Files

```
scan_server.py       WebSocket server (the backend)
scanner_backend.py   Cross-platform scanner driver (TWAIN / SANE / pyinsane2)
index.html           App UI — open this in any browser or run as Electron app
setup.py             One-time setup: creates .venv + installs dependencies
run.py               Start the server using .venv (no manual activation needed)
main.js              Electron main entry point (launches backend automatically)
package.json         Node dependencies & scripts for the Electron client
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

## Step 3 — Run the App

### Option A: Electron Desktop App (Recommended)
This starts the backend WebSocket server and opens the beautiful desktop application automatically in a single command:

```bash
npm install
npm start
```

### Option B: Web Browser mode (Manual Server start)
If you prefer running it in a standard web browser:

#### 1. Start the server (no venv activation needed)
```bash
python run.py
```

#### 2. Open index.html in your browser
Open `index.html` in any browser. It will connect to `ws://127.0.0.1:8765` automatically.

```bash
open index.html        # macOS
xdg-open index.html   # Linux
start index.html       # Windows
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "No scanners found" macOS | `brew install sane-backends` then restart server |
| "No scanners found" Linux | `sudo apt install libsane-dev` then restart server |
| "Cannot reach server" in browser | Make sure the WebSocket server is running |
| PowerShell blocks Activate.ps1 | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |