const { app, BrowserWindow } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const fs = require("fs");

let serverProcess = null;
let mainWindow = null;

// Determine the best Python executable to use
function getPythonExecutable() {
  const venvPath = path.join(__dirname, ".venv");
  if (process.platform === "win32") {
    const winVenvPython = path.join(venvPath, "Scripts", "python.exe");
    if (fs.existsSync(winVenvPython)) {
      return winVenvPython;
    }
    return "python";
  } else {
    const unixVenvPython = path.join(venvPath, "bin", "python");
    if (fs.existsSync(unixVenvPython)) {
      return unixVenvPython;
    }
    return "python3";
  }
}

// Start the Python scan_server.py WebSocket server
function startBackendServer() {
  const pythonPath = getPythonExecutable();
  const serverScript = path.join(__dirname, "scan_server.py");

  console.log(`[Electron] Starting backend server using: ${pythonPath}`);
  console.log(`[Electron] Script path: ${serverScript}`);

  serverProcess = spawn(pythonPath, [serverScript, "--host", "127.0.0.1", "--port", "8765"], {
    cwd: __dirname,
    stdio: "pipe",
  });

  serverProcess.stdout.on("data", (data) => {
    console.log(`[Python Server STDOUT] ${data.toString().trim()}`);
  });

  serverProcess.stderr.on("data", (data) => {
    console.error(`[Python Server STDERR] ${data.toString().trim()}`);
  });

  serverProcess.on("close", (code) => {
    console.log(`[Python Server] Process exited with code ${code}`);
    serverProcess = null;
  });

  serverProcess.on("error", (err) => {
    console.error(`[Python Server] Failed to start server process:`, err);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1024,
    height: 768,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  mainWindow.loadFile("index.html");

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  app.setPath("userData", path.join(app.getPath("userData"), "custom-cache"));
  
  // Start python scan server in the background
  startBackendServer();
  
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("will-quit", () => {
  if (serverProcess) {
    console.log("[Electron] Killing backend server process...");
    serverProcess.kill();
    serverProcess = null;
  }
});

