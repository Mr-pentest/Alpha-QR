(function () {
  const endpoint = "http://127.0.0.1:5000/api/current_qr";
  const styleEp = "http://127.0.0.1:5000/api/style";

  // Spinner CSS
  const style = document.createElement("style");
  style.textContent = `
    @keyframes spin { to { transform:rotate(360deg); } }
    .Alpha-loading {
      position:absolute;
      top:0; left:0; right:0; bottom:0;
      display:flex;
      align-items:center;
      justify-content:center;
      pointer-events:none;
    }
    .Alpha-spinner {
      width:40px;
      height:40px;
      border:4px solid #bbb;
      border-top-color:#4a63e7;
      border-radius:50%;
      animation:spin .8s linear infinite;
    }
    #AlphaQR { position:relative; width:100%; height:100%; display:flex; align-items:center; justify-content:center; }
    #AlphaQR canvas { max-width:100%; max-height:100%; width:auto; height:auto; }
  `;
  document.head.appendChild(style);

  let target = null;
  let loading = null;
  let qr = null;
  let currentStyle = {};
  let lastData = "";

  function ensureLib(cb) {
    if (window.QRCodeStyling) return cb();
    const s = document.createElement("script");
    s.src = "https://unpkg.com/qr-code-styling/lib/qr-code-styling.js";
    s.onload = cb;
    document.head.appendChild(s);
  }

  function showSpinner() {
    if (!target) return;
    if (getComputedStyle(target).position === 'static') {
      target.style.position = 'relative';
    }
    if ((target.clientHeight || 0) < 120) {
      target.style.minHeight = '220px';
    }
    if (!loading) {
      loading = document.createElement("div");
      loading.className = "Alpha-loading";
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

  function renderQR(link) {
    if (!target) return;
    
    // Use full available size of the container
    const containerWidth = target.clientWidth || 300;
    const containerHeight = target.clientHeight || 300;
    const baseSize = Math.min(containerWidth, containerHeight, 1000); // Max 1000px but use full container

    const colorMode = currentStyle.colorMode || "single";
    const gradientType = currentStyle.gradientType || "linear";
    
    // Get primary color - support dotPrimary2 (from color box) or dotPrimary
    const primary = currentStyle.dotPrimary2 || currentStyle.dotPrimary || currentStyle.dotColor || "#000000";
    const secondary = currentStyle.dotSecondary || "#1f2937";
    
    // Get eye colors separately (matching listen.py)
    // Eyes always use solid colors, never gradients
    let eyeOuterColor = currentStyle.eyeOuterColor || currentStyle.eyeColor || "#000000";
    let eyeInnerColor = currentStyle.eyeInnerColor || currentStyle.eyeColor || "#000000";
    
    // Ensure eye colors are strings (solid colors), not gradient objects
    if(typeof eyeOuterColor === 'object' && eyeOuterColor.colorStops) {
      eyeOuterColor = eyeOuterColor.colorStops[0]?.color || "#000000";
    }
    if(typeof eyeInnerColor === 'object' && eyeInnerColor.colorStops) {
      eyeInnerColor = eyeInnerColor.colorStops[0]?.color || "#000000";
    }
    
    // Get eye styles
    const eyeStyle = currentStyle.eyeStyle || "square";
    const innerEyeStyle = currentStyle.innerEyeStyle || "square";
    
    // Map eye styles to library types (matching listen.py logic)
    let eyeOuterType = "square";
    if(eyeStyle === "extra-rounded" || eyeStyle === "soft-corner") eyeOuterType = "extra-rounded";
    else if(eyeStyle === "circle") eyeOuterType = "extra-rounded";
    else if(eyeStyle === "diamond" || eyeStyle === "hexagon") eyeOuterType = "square";
    else if(eyeStyle === "hollow" || eyeStyle === "double") eyeOuterType = "extra-rounded";
    else eyeOuterType = "square";
    
    let eyeInnerType = "square";
    if(innerEyeStyle === "dot" || innerEyeStyle === "circle" || innerEyeStyle === "minimal") eyeInnerType = "dot";
    else if(innerEyeStyle === "rounded") eyeInnerType = "dot";
    else if(innerEyeStyle === "diamond") eyeInnerType = "square";
    else eyeInnerType = "square";

    // Map pixel shapes (matching listen.py)
    const pixelShape = currentStyle.pixelShape || currentStyle.dotStyle || "square";
    let dotType = "square";
    if(pixelShape === "dots") dotType = "dots";
    else if(pixelShape === "rounded") dotType = "rounded";
    else if(pixelShape === "diamond" || pixelShape === "triangle" || pixelShape === "hexagon") dotType = "square";
    else if(pixelShape === "grainy" || pixelShape === "clusters") dotType = "dots";
    else if(pixelShape === "organic" || pixelShape === "crystal" || pixelShape === "polygon" || pixelShape === "ink" || pixelShape === "flame") dotType = "classy-rounded";
    else dotType = pixelShape === "extra-rounded" ? "extra-rounded" : (pixelShape === "classy" ? "classy" : (pixelShape === "classy-rounded" ? "classy-rounded" : "square"));

    let dotsOptions;
    if (colorMode !== "single") {
      // Handle gradient - matching listen.py logic exactly
      // In listen.py: if(colorMode !== 'single') uses gradientType directly
      dotsOptions = {
        type: dotType,
        gradient: {
          type: gradientType, // Use gradientType directly (linear or radial)
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
    if(backgroundStyle === "transparent") {
      bgColor = "transparent";
    } else if(backgroundStyle === "solid" || backgroundStyle === "color") {
      bgColor = backgroundColor;
    } else if(backgroundStyle === "gradient") {
      // For gradient, we'll use solid color as fallback (library limitation)
      bgColor = backgroundColor;
    } else if(backgroundStyle === "dark") {
      bgColor = "#000000";
    } else if(backgroundStyle === "light") {
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
    try {
      const [styleRes, qrRes] = await Promise.all([
        fetch(styleEp),
        fetch(endpoint),
      ]);

      const styleData = await styleRes.json();
      const qrData = await qrRes.json();

      currentStyle = styleData;
      const link = qrData?.link;

      if (!link) {
        showSpinner();
        return;
      }

      hideSpinner();

      // If style OR link changed → update instantly (live update)
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

    showSpinner();

    // live update but no flicker
    setInterval(poll, 800); // fast & stable
    poll();
  }

  init();
})();
