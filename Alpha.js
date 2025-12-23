(function () {
  // Auto-detect API_BASE
  let API_BASE = "http://127.0.0.1:5000";
  
  try {
      if (document.currentScript && document.currentScript.src && document.currentScript.src.startsWith('http')) {
          API_BASE = new URL(document.currentScript.src).origin;
      } else if (window.location.protocol.startsWith('http')) {
          API_BASE = window.location.origin;
      }
  } catch(e) {
      console.log("[AlphaQR] Could not auto-detect API_BASE, using default.");
  }

  const endpoint = API_BASE + "/api/current_qr";
  const styleEp = API_BASE + "/api/style";
  const fallbackStatusEp = API_BASE + "/api/fallback_status";
  const fallbackContentEp = API_BASE + "/api/fallback_content";

  let target = null;
  let qr = null;
  let loading = null;
  let currentStyle = {};
  let lastData = "";
  let fallbackActive = false;
  let originalContent = null;

  // Create and inject styles
  const style = document.createElement("style");
  style.textContent = `
    @keyframes spin { to { transform: rotate(360deg); } }
    .Alpha-loading {
      position: absolute;
      top: 0; left: 0; right: 0; bottom: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      pointer-events: none;
      z-index: 10;
    }
    .Alpha-spinner {
      width: 40px;
      height: 40px;
      border: 4px solid #bbb;
      border-top-color: #4a63e7;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    #AlphaQR {
      position: relative;
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    #AlphaQR canvas {
      max-width: 100%;
      max-height: 100%;
      width: auto;
      height: auto;
    }
    .Alpha-fallback-container {
      width: 100%;
      height: 100%;
    }
    .Alpha-fallback-container iframe {
      width: 100%;
      height: 100%;
      border: none;
    }
  `;
  document.head.appendChild(style);

  // Initialize WebSocket connection for real-time fallback events
  let socket = null;
  function initSocket() {
    try {
      // Check if socket.io is available
      if (typeof io !== 'undefined') {
        socket = io(API_BASE, {
          transports: ['websocket', 'polling'],
          reconnection: true,
          reconnectionAttempts: 5,
          reconnectionDelay: 1000
        });

        socket.on('connect', function() {
          console.log('[AlphaQR] WebSocket connected');
        });

        socket.on('fallback_on', function(data) {
          console.log('[AlphaQR] Fallback ON:', data);
          activateFallback(data);
        });

        socket.on('fallback_off', function(data) {
          console.log('[AlphaQR] Fallback OFF:', data);
          deactivateFallback();
        });

        socket.on('disconnect', function() {
          console.log('[AlphaQR] WebSocket disconnected');
        });
      }
    } catch (e) {
      console.log('[AlphaQR] WebSocket not available, using polling');
    }
  }

  // Load Socket.IO library if not present
  function loadSocketIO(callback) {
    if (typeof io !== 'undefined') {
      callback();
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js';
    script.onload = callback;
    script.onerror = function() {
      console.log('[AlphaQR] Socket.IO failed to load, using polling only');
    };
    document.head.appendChild(script);
  }

  function ensureLib(cb) {
    if (window.QRCodeStyling) return cb();
    const s = document.createElement("script");
    s.src = "https://unpkg.com/qr-code-styling/lib/qr-code-styling.js";
    s.onload = cb;
    s.onerror = function() {
      console.error('[AlphaQR] Failed to load QRCodeStyling library');
    };
    document.head.appendChild(s);
  }

  function showSpinner() {
    if (!target) return;
    if (getComputedStyle(target).position === 'static') {
      target.style.position = 'relative';
    }
    if (!loading) {
      loading = document.createElement('div');
      loading.className = 'Alpha-loading';
      loading.innerHTML = '<div class="Alpha-spinner"></div>';
    }
    if (!target.contains(loading)) {
      target.appendChild(loading);
    }
  }

  function hideSpinner() {
    if (!target) return;
    if (loading && target.contains(loading)) {
      loading.remove();
    }
  }

  // ========================================
  // FALLBACK DISPLAY LOGIC
  // ========================================

  function saveFallbackState(active, data) {
    try {
      localStorage.setItem('AlphaQR_fallback_active', active ? 'true' : 'false');
      if(data && data.file) localStorage.setItem('AlphaQR_fallback_file', data.file);
      if(data && data.url) localStorage.setItem('AlphaQR_fallback_url', data.url);
      if(data && data.type) localStorage.setItem('AlphaQR_fallback_type', data.type);
    } catch (e) {
      // localStorage not available
    }
  }

  function loadFallbackState() {
    try {
      return {
        active: localStorage.getItem('AlphaQR_fallback_active') === 'true',
        file: localStorage.getItem('AlphaQR_fallback_file') || '',
        url: localStorage.getItem('AlphaQR_fallback_url') || '',
        type: localStorage.getItem('AlphaQR_fallback_type') || 'file'
      };
    } catch (e) {
      return { active: false, file: '', url: '', type: 'file' };
    }
  }

  function clearFallbackState() {
    try {
      localStorage.removeItem('AlphaQR_fallback_active');
      localStorage.removeItem('AlphaQR_fallback_file');
      localStorage.removeItem('AlphaQR_fallback_url');
      localStorage.removeItem('AlphaQR_fallback_type');
    } catch (e) {
      // localStorage not available
    }
  }

  function activateFallback(data) {
    if (!data) return;
    
    // URL Redirect Mode
    if (data.type === 'url' || (!data.file && data.url)) {
        console.log('[AlphaQR] Redirecting to:', data.url);
        window.top.location.href = data.url;
        return;
    }

    // HTML File Mode (Iframe)
    const filename = data.file || data; // handle legacy string arg
    if (!filename) return;

    // Check if already active to avoid re-rendering
    if (fallbackActive && document.getElementById('Alpha-fallback-overlay')) return;

    fallbackActive = true;
    saveFallbackState(true, {file: filename, type: 'file'});

    // Create a full-screen overlay to cover the entire page
    let overlay = document.getElementById('Alpha-fallback-overlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'Alpha-fallback-overlay';
      overlay.style.position = 'fixed';
      overlay.style.top = '0';
      overlay.style.left = '0';
      overlay.style.width = '100vw';
      overlay.style.height = '100vh';
      overlay.style.zIndex = '2147483647'; // Max z-index
      overlay.style.background = '#ffffff';
      overlay.style.border = 'none';
      overlay.style.margin = '0';
      overlay.style.padding = '0';
      
      const iframe = document.createElement('iframe');
      iframe.style.width = '100%';
      iframe.style.height = '100%';
      iframe.style.border = 'none';
      iframe.src = API_BASE + "/uploads/" + filename;
      
      overlay.appendChild(iframe);
      document.body.appendChild(overlay);
      
      // Prevent scrolling on the underlying page
      document.body.style.overflow = 'hidden';
      
      console.log('[AlphaQR] Full-page fallback activated:', filename);
    }
  }

  function deactivateFallback() {
    fallbackActive = false;
    clearFallbackState();

    const overlay = document.getElementById('Alpha-fallback-overlay');
    if (overlay) {
      overlay.remove();
      // Restore scrolling
      document.body.style.overflow = '';
      console.log('[AlphaQR] Full-page fallback cleared');
    }

    // Force immediate poll to restore QR if needed
    poll();
  }

  // Check fallback status via API (fallback for when WebSocket is not available)
  function checkFallbackStatus() {
    fetch(fallbackStatusEp)
      .then(r => r.json())
      .then(data => {
        if (data.active && !fallbackActive) {
          activateFallback(data.file);
        } else if (!data.active && fallbackActive) {
          deactivateFallback();
        }
      })
      .catch(() => {
        // Silently fail - server might be down
      });
  }

  // ========================================
  // QR CODE RENDERING
  // ========================================

  function renderQR(link) {
    if (!target || fallbackActive) return;

    // Use full available size of the container
    const containerWidth = target.clientWidth || 300;
    const containerHeight = target.clientHeight || 300;
    const baseSize = Math.min(containerWidth, containerHeight, 1000);

    const colorMode = currentStyle.colorMode || "single";
    const gradientType = currentStyle.gradientType || "linear";
    const primary = currentStyle.dotPrimary || currentStyle.dotColor || "#000000";
    const secondary = currentStyle.dotSecondary || "#1f2937";
    const eyeOuterColor = currentStyle.eyeOuterColor || currentStyle.eyeColor || "#000000";
    const eyeInnerColor = currentStyle.eyeInnerColor || currentStyle.eyeColor || "#000000";

    // Map eye styles
    const eyeStyle = currentStyle.eyeStyle || "square";
    let eyeOuterType = "square";
    if (eyeStyle === "circle" || eyeStyle === "rounded") eyeOuterType = "extra-rounded";
    else if (eyeStyle === "double") eyeOuterType = "extra-rounded";
    else eyeOuterType = "square";

    const innerEyeStyle = currentStyle.innerEyeStyle || "square";
    let eyeInnerType = "square";
    if (innerEyeStyle === "dot" || innerEyeStyle === "circle" || innerEyeStyle === "minimal") eyeInnerType = "dot";
    else if (innerEyeStyle === "rounded") eyeInnerType = "dot";
    else if (innerEyeStyle === "diamond") eyeInnerType = "square";
    else eyeInnerType = "square";

    // Map pixel shapes
    const pixelShape = currentStyle.pixelShape || currentStyle.dotStyle || "square";
    let dotType = "square";
    if (pixelShape === "dots") dotType = "dots";
    else if (pixelShape === "rounded") dotType = "rounded";
    else if (pixelShape === "diamond" || pixelShape === "triangle" || pixelShape === "hexagon") dotType = "square";
    else if (pixelShape === "grainy" || pixelShape === "clusters") dotType = "dots";
    else if (pixelShape === "organic" || pixelShape === "crystal" || pixelShape === "polygon" || pixelShape === "ink" || pixelShape === "flame") dotType = "classy-rounded";
    else if (pixelShape === "extra-rounded") dotType = "extra-rounded";
    else if (pixelShape === "classy") dotType = "classy";
    else if (pixelShape === "classy-rounded") dotType = "classy-rounded";
    else dotType = "square";

    let dotsOptions;
    if (colorMode !== "single") {
      dotsOptions = {
        type: dotType,
        gradient: {
          type: gradientType,
          rotation: 0,
          colorStops: [
            { offset: 0, color: primary },
            { offset: 1, color: secondary }
          ]
        },
        scale: 1
      };
    } else {
      dotsOptions = {
        type: dotType,
        color: primary,
        scale: 1
      };
    }

    const backgroundStyle = currentStyle.backgroundStyle || "white";
    const backgroundColor = currentStyle.backgroundColor || "#ffffff";
    let bgColor = "#ffffff";
    if (backgroundStyle === "transparent") {
      bgColor = "transparent";
    } else if (backgroundStyle === "solid" || backgroundStyle === "color") {
      bgColor = backgroundColor;
    } else if (backgroundStyle === "gradient") {
      bgColor = backgroundColor;
    } else if (backgroundStyle === "dark") {
      bgColor = "#000000";
    } else if (backgroundStyle === "light") {
      bgColor = "#ffffff";
    }

    const opts = {
      width: baseSize,
      height: baseSize,
      type: "png",
      data: link,
      image: currentStyle.logoUrl || "",
      margin: 12,
      dotsOptions: dotsOptions,
      cornersSquareOptions: {
        type: eyeOuterType,
        color: eyeOuterColor,
        scale: 1
      },
      cornersDotOptions: {
        type: eyeInnerType,
        color: eyeInnerColor,
        scale: 1
      },
      backgroundOptions: { color: bgColor },
      imageOptions: {
        imageSize: Number(currentStyle.logoSize || 0.35),
        margin: Number(currentStyle.logoMargin || 8),
        hideBackgroundDots: !!currentStyle.hideBgDots
      }
    };

    if (!qr) {
      qr = new QRCodeStyling(opts);
      target.innerHTML = "";
      target.style.width = "100%";
      target.style.height = "100%";
      target.style.display = "flex";
      target.style.alignItems = "center";
      target.style.justifyContent = "center";
      qr.append(target);
    } else {
      qr.update(opts);
    }
  }

  async function poll() {
    // Skip polling if fallback is active (unless checking for deactivation)
    if (fallbackActive) {
      checkFallbackStatus();
      return;
    }

    try {
      const [styleRes, qrRes] = await Promise.all([
        fetch(styleEp),
        fetch(endpoint)
      ]);

      const styleData = await styleRes.json();
      const qrData = await qrRes.json();

      currentStyle = styleData;

      // Check if fallback was activated server-side
      if (qrData.fallback_active) {
          if (qrData.fallback_file) {
             activateFallback({file: qrData.fallback_file, type: 'file'});
          } else if (qrData.fallback_url) {
             activateFallback({url: qrData.fallback_url, type: 'url'});
          }
          return;
      }

      const link = qrData?.link;

      if (!link) {
        showSpinner();
        return;
      }

      hideSpinner();

      // If style OR link changed → update instantly
      const newCombined = JSON.stringify(styleData) + "|" + link;
      if (newCombined !== lastData) {
        lastData = newCombined;
        ensureLib(() => renderQR(link));
      }

    } catch (err) {
      showSpinner();
    }
  }

  function init() {
    target = document.getElementById("AlphaQR");
    if (!target) return setTimeout(init, 300);

    // Check for persisted fallback state
    const savedState = loadFallbackState();
    if (savedState.active && savedState.file) {
      // Verify with server before restoring
      fetch(fallbackStatusEp)
        .then(r => r.json())
        .then(data => {
          if (data.active && data.file) {
            activateFallback(data.file);
          } else {
            clearFallbackState();
            showSpinner();
            poll();
          }
        })
        .catch(() => {
          showSpinner();
          poll();
        });
    } else {
      showSpinner();
      poll();
    }

    // Initialize WebSocket for real-time updates
    loadSocketIO(initSocket);

    // Poll for updates
    setInterval(poll, 800);
  }

  init();
})();
