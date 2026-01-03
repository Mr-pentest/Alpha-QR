let targetTabId = null;
let scanning = false;
let isProcessing = false;

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {

  // --- START SCAN ---
  if (msg.action === "startScan") {
    targetTabId = msg.tabId;
    scanning = true;
    isProcessing = false;

    // Start the capture loop
    captureLoop();

    sendResponse({ ok: true });
  }

  // --- STOP SCAN ---
  if (msg.action === "stopScan") {
    scanning = false;
    targetTabId = null;
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

// --- CAPTURE LOOP (Request-Response chain) ---
function captureLoop() {
  if (!scanning || !targetTabId) return;

  // Don't capture if we are already waiting for a response (though the loop structure handles this naturally)
  if (isProcessing) return; 

  chrome.tabs.get(targetTabId).then(tab => {
    if (!tab) {
      scanning = false;
      targetTabId = null;
      return;
    }

    // Capture screenshot
    isProcessing = true;
    chrome.tabs.captureVisibleTab(tab.windowId, { format: "jpeg", quality: 40 }, (img) => {
      if (chrome.runtime.lastError || !img) {
        // Tab might be hidden or protected, retry after delay
        isProcessing = false;
        setTimeout(captureLoop, 500);
        return;
      }

      // Send to server
      fetch("http://127.0.0.1:5000/receive_screenshot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tab_id: targetTabId,
          image: img
        })
      })
      .then(response => {
        // We don't really care about the response content, just that it finished
        // But if we get 429 (Too Many Requests), we might want to back off slightly?
        // Our server returns 429 if locked.
        return response.json();
      })
      .then(data => {
        // Success or error, we continue
      })
      .catch(err => {
        console.error("Send error:", err);
      })
      .finally(() => {
        isProcessing = false;
        // Schedule next capture immediately (or with tiny delay to yield)
        // Using 50ms delay to prevent browser freeze if server is super fast
        if (scanning) {
            setTimeout(captureLoop, 50); 
        }
      });
    });

  }).catch(err => {
    console.error("Tab error:", err);
    scanning = false;
    targetTabId = null;
    isProcessing = false;
  });
}
