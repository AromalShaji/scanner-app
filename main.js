const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");
const { exec } = require("child_process");

function createWindow() {
  const win = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      nodeIntegration: true,
    },
  });

  win.loadFile("index.html");

  // Automatically list scanners when the window is ready
  win.webContents.on("did-finish-load", () => {
    exec(
      "python C:/Users/ACER/scanner-app/scan.py --list-scanners",
      (error, stdout, stderr) => {
        console.log(`stdout: ${stdout}`);
        console.log(`stderr: ${stderr}`);
        if (error) {
          console.error(`Error: ${error.message}`);
          win.webContents.send("scanners-list", []);
          return;
        }
        if (stderr) {
          console.error(`Stderr: ${stderr}`);
          win.webContents.send("scanners-list", []);
          return;
        }
        const scanners = stdout.trim().split("\n");
        win.webContents.send("scanners-list", scanners);
      }
    );
  });

  ipcMain.on("start-scan", (event, scannerName) => {
    exec(
      `python C:/Users/ACER/scanner-app/scan.py --scan "${scannerName}"`,
      (error, stdout, stderr) => {
        if (error) {
          console.error(`Error: ${error.message}`);
          event.reply("scan-result", "Error during scanning1.");
          return;
        }
        if (stderr) {
          console.error(`Stderr: ${stderr}`);
          event.reply("scan-result", "Error during scanning2.");
          return;
        }

        console.log(`stdout: ${stdout}`); // Log stdout for debugging

        const base64Image = stdout.trim();
        if (base64Image.startsWith("data:image/png;base64,")) {
          event.reply("scan-result", base64Image);
        } else {
          console.error("Unexpected image data format.");
          event.reply("scan-result", "Error during scanning3.");
        }
      }
    );
  });

}

app.whenReady().then(() => {
  app.setPath("userData", path.join(app.getPath("userData"), "custom-cache"));
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
