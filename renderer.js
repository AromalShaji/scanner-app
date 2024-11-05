const scannerSelect = document.getElementById("scanner-select");
const scanButton = document.getElementById("start-scan");
const scanStatus = document.getElementById("scan-status");
const scannedImage = document.getElementById("scanned-image");

scanButton.addEventListener("click", () => {
  const selectedScanner = scannerSelect.value;
  if (selectedScanner) {
    scanStatus.style.display = "block";
    window.electronAPI
      .startScan(selectedScanner)
      .then((result) => {
        scanStatus.style.display = "none";
        if (result.startsWith("data:image/png;base64,")) {
          scannedImage.src = result;
          scannedImage.style.display = "block";
        } else {
          alert("Error during scanning.");
        }
      })
      .catch((error) => {
        scanStatus.style.display = "none";
        console.error("Scan failed:", error);
        alert("Error occurred during scanning.");
      });
  } else {
    alert("Please select a scanner");
  }
});
