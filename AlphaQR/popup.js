document.getElementById("startBtn").addEventListener("click", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  chrome.runtime.sendMessage({
    action: "startScan",
    tabId: tab.id
  });

  updateUI("running", tab.id);
});

document.getElementById("stopBtn").addEventListener("click", () => {
  chrome.runtime.sendMessage({ action: "stopScan" });
  updateUI("stopped", "-");
});

function updateUI(state, tabId) {
  const icon = document.getElementById("statusIcon");
  const text = document.getElementById("statusText");

  icon.src = "Icons/AlphaQR.png";
  text.innerText = state === "running" ? "Running" : "Stopped";

  document.getElementById("tabId").innerText = tabId;
}

// When popup opens, sync UI
chrome.runtime.sendMessage({ action: "getStatus" }, (res) => {
  if (!res) return;

  updateUI(res.state, res.tabId || "-");
});
