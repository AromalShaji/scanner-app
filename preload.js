const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  listScanners: () => ipcRenderer.send("list-scanners"),
  onScannersList: (callback) =>
    ipcRenderer.on("scanners-list", (event, scanners) => callback(scanners)),
  startScan: (scannerName) => ipcRenderer.send("start-scan", scannerName),
  onScanResult: (callback) =>
    ipcRenderer.on("scan-result", (event, result) => callback(result)),
});
