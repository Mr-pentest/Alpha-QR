let targetTabId = null;
let scanning = false;
let alarmName = "AlphaCapture";

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {

  // --- START SCAN ---
  if (msg.action === "startScan") {
    targetTabId = msg.tabId;
    scanning = true;

    chrome.alarms.clear(alarmName);
    chrome.alarms.create(alarmName, { periodInMinutes: 0.083 }); // ~5 sec

    sendResponse({ ok: true });
  }

  // --- STOP SCAN ---
  if (msg.action === "stopScan") {
    scanning = false;
    targetTabId = null;
    chrome.alarms.clear(alarmName);
    sendResponse({ ok: true });
  }

  // --- POPUP STATUS ---
  if (msg.action === "getStatus") {
    sendResponse({
      state: scanning ? "running" : "stopped",
      tabId: targetTabId
    });
  }

  return true;
});

// --- ALARM (REPEATED SCREENSHOT SENDER) ---
chrome.alarms.onAlarm.addListener(async () => {
  if (!scanning || !targetTabId) return;

  chrome.tabs.get(targetTabId).then(tab => {

    if (!tab) {
      scanning = false;
      targetTabId = null;
      chrome.alarms.clear(alarmName);
      return;
    }

    chrome.tabs.captureVisibleTab(tab.windowId, { format: "png" }, (img) => {
      if (!img) return;

      fetch("http://127.0.0.1:5000/receive_screenshot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tab_id: targetTabId,
          image: img
        })
      }).catch(() => {});
    });

  }).catch(() => {
    scanning = false;
    targetTabId = null;
    chrome.alarms.clear(alarmName);
  });
});
