from flask import Flask, request, jsonify, render_template_string, send_from_directory
import base64
import datetime
from PIL import Image
from io import BytesIO
from pyzbar.pyzbar import decode
import qrcode
import logging
import sys
import os

app = Flask(__name__)

logging.getLogger('werkzeug').setLevel(logging.ERROR)

# Store current QR link
current_qr_link = None
last_update_time = None
style_options = {
    "dotStyle": "square",
    "dotColor": "#000000",
    "eyeStyle": "square",
    "innerEyeStyle": "square",
    "eyeColor": "#000000",
    "eyeOuterColor": "#000000",
    "eyeInnerColor": "#000000",
    "colorMode": "single",
    "gradientType": "linear",
    "dotPrimary": "#000000",
    "dotSecondary": "#1f2937",
    "backgroundStyle": "white",
    "backgroundColor": "#ffffff",
    "logoUrl": "",
    "logoSize": 0.35,
    "logoMargin": 8,
    "hideBgDots": False
}

DEMO_LINK = "https://example.com/demo"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>PRO QR Designer</title>
<script src="https://unpkg.com/qr-code-styling/lib/qr-code-styling.js"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" />
<style>
:root{
  --bg:#e8f4f8; --panel:#ffffff; --border:#b0c4de; --text:#2c3e50; --muted:#708090;
  --blue:#87ceeb; --blue-200:#b0e0e6; --gray:#708090; --black:#000000; --white:#ffffff;
}
body{ font-family:"Segoe UI", system-ui, -apple-system, Arial, sans-serif; margin:0; padding:0; background:linear-gradient(135deg,#e8f4f8,#ffffff); color:var(--text); }
.wrapper{ display:grid; grid-template-columns: 1fr 1fr; gap:24px; padding:28px; align-items:start; }
.sidebar{ background:var(--panel); border:1px solid var(--border); border-radius:18px; padding:24px; box-shadow:0 16px 48px rgba(112,128,144,0.15); overflow-y:auto; }
.sidebar h2{ margin:0 0 10px 0; font-size:22px; color:var(--gray); }
label{ font-weight:600; margin-top:12px; display:block; color:var(--gray); }
input, select{ width:100%; padding:10px; margin-top:6px; border:1px solid var(--border); border-radius:10px; background:#fff; color:var(--text); }
input:focus, select:focus{ border-color:var(--blue); box-shadow:0 0 0 3px var(--blue-200); outline:none; }
.row{ display:grid; grid-template-columns: 1fr 1fr; gap:12px; }
.button{ width:100%; padding:12px; margin-top:18px; border:none; border-radius:10px; background:var(--blue); color:white; font-size:15px; cursor:pointer; }
.button:hover{ filter:brightness(1.05); }
.note{ margin-top:10px; font-size:12px; color:var(--muted); }
.preview{ display:flex; align-items:center; justify-content:center; background:linear-gradient(135deg,#e8f4f8,#f0f8ff); border:1px solid var(--border); border-radius:18px; box-shadow:inset 0 0 22px rgba(112,128,144,0.1); }
#qrContainer{ padding:0; background:#ffffff; border:1px solid var(--border); border-radius:16px; box-shadow:0 10px 28px rgba(112,128,144,0.15); display:inline-block; }
#qrContainer canvas{ display:block; }
input[type="color"]{ width:60px; height:60px; padding:5px; border:2px solid var(--border); border-radius:8px; cursor:pointer; background:none; flex-shrink:0; }
input[type="color"]::-webkit-color-swatch-wrapper{ padding:0; }
input[type="color"]::-webkit-color-swatch{ border:2px solid var(--border); border-radius:6px; width:100%; height:100%; }
.color-row{ display:flex; align-items:center; gap:12px; margin-top:12px; }
.color-row label{ margin:0; flex:1; min-width:120px; }
.color-row input[type="color"]{ margin:0; }
.nav{ position:sticky; top:0; z-index:10; background:var(--panel); border-bottom:1px solid var(--border); box-shadow:0 8px 24px rgba(112,128,144,0.12); }
.nav-inner{ display:flex; align-items:center; justify-content:space-between; padding:14px 28px; }
.brand{ font-weight:700; font-size:18px; color:var(--gray); letter-spacing:0.3px; }
.menu{ display:flex; align-items:center; gap:10px; }
.menu a{ text-decoration:none; color:var(--text); padding:8px 12px; border-radius:10px; border:1px solid transparent; }
.menu a:hover{ background:var(--blue-200); border-color:var(--border); }
.tabs{ display:flex; gap:10px; padding:12px 28px 0; }
.tab-btn{ appearance:none; border:1px solid var(--border); background:var(--panel); color:var(--text); font-weight:600; padding:8px 14px; border-radius:10px; cursor:pointer; }
.tab-btn.active{ background:var(--blue-200); border-color:var(--blue); }
.about{ margin:0 28px 28px; background:var(--panel); border:1px solid var(--border); border-radius:18px; box-shadow:0 16px 48px rgba(112,128,144,0.12); padding:24px; }
.about h2{ margin:0 0 8px 0; font-size:22px; color:var(--gray); }
.about p{ margin:0; color:var(--text); line-height:1.6; }
.about-section{ margin:0 28px 28px; background:var(--panel); border:1px solid var(--border); border-radius:18px; box-shadow:0 16px 48px rgba(112,128,144,0.12); padding:24px; }
.about-header h2{ margin:0 0 12px 0; font-size:22px; color:var(--gray); }
.team-container{ display:grid; grid-template-columns: repeat(auto-fit,minmax(280px,1fr)); gap:16px; }
.team-member{ background:#fff; border:1px solid var(--border); border-radius:14px; padding:16px; box-shadow:0 8px 24px rgba(112,128,144,0.1); }
.team-member:hover{ box-shadow:0 12px 32px rgba(112,128,144,0.18); }
.member-name{ font-weight:700; font-size:16px; color:var(--text); }
.member-role{ font-size:13px; color:var(--muted); margin-top:4px; }
.member-bio{ font-size:14px; color:var(--text); line-height:1.6; margin-top:10px; }
.social-links{ display:flex; gap:10px; margin-top:12px; }
.social-link{ width:36px; height:36px; display:flex; align-items:center; justify-content:center; border:1px solid var(--border); border-radius:10px; color:var(--text); text-decoration:none; background:var(--panel); }
.social-link:hover{ background:var(--blue-200); border-color:var(--blue); }
@media (min-width: 901px){
  .sidebar{ position: sticky; top: 92px; height: calc(100vh - 120px); overflow-y:auto; }
  .preview{ position: sticky; top: 92px; height: calc(100vh - 120px); }
}
@media (max-width: 900px){ .wrapper{ grid-template-columns: 1fr; } .menu{ gap:6px; } }
</style>
</head>
<body>
<nav class="nav">
  <div class="nav-inner">
    <div class="brand">Alpha QR</div>
    <div class="tabs">
      <button class="tab-btn active" id="navHome">Home</button>
      <button class="tab-btn" id="navAbout">About us</button>
    </div>
  </div>
</nav>
<div class="wrapper" id="designer">
  <div class="sidebar">
    <h2>QR Designer</h2>
    
    <label>Text / URL</label>
    <input id="qrText" placeholder="Enter URL">
    
    <div class="color-row">
      <label>Dot Style</label>
      <input type="color" id="dotPrimary" value="#000000">
      <select id="dotStyle" style="flex:1; margin:0;">
      <option value="square">Square</option>
      <option value="dots">Dots</option>
      <option value="rounded">Rounded</option>
      <option value="extra-rounded">Extra Rounded</option>
      <option value="classy">Classy</option>
      <option value="classy-rounded">Classy Rounded</option>
      </select>
    </div>
    
    <div class="color-row">
      <label>Inner Eye Style</label>
      <input type="color" id="eyeInnerColor" value="#000000">
      <select id="innerEyeStyle" style="flex:1; margin:0;">
      <option value="square">Square</option>
      <option value="dot">Dot</option>
      </select>
    </div>
    
    <div class="color-row">
      <label>Outer Eye Style</label>
      <input type="color" id="eyeOuterColor" value="#000000">
      <select id="eyeStyle" style="flex:1; margin:0;">
      <option value="square">Square</option>
      <option value="circle">Circle</option>
      </select>
    </div>
    
    <label>Color Mode</label>
    <select id="colorMode">
      <option value="single">Single</option>
      <option value="linear">Linear Gradient</option>
      
    </select>
    
    <label>Gradient Type</label>
    <select id="gradientType">
      <option value="linear">Linear</option>
      <option value="radial">Radial</option>
    </select>
    
    <div class="row">
      <div>
        <label>Primary Color</label>
        <input type="color" id="dotPrimary2" value="#000000">
      </div>
      <div>
        <label>Secondary Color</label>
        <input type="color" id="dotSecondary" value="#1f2937">
      </div>
    </div>
    <div class="row">
      <div>
        <label>Background Style</label>
        <select id="backgroundStyle">
          <option value="transparent">Transparent</option>
          <option value="white">White</option>
          <option value="color">Color</option>
        </select>
      </div>
      <div>
        <label>Background Color</label>
        <input type="color" id="backgroundColor" value="#ffffff">
      </div>
    </div>
    <label>Logo URL</label>
    <input id="logoUrl" placeholder="https://image.com/logo.png">
    <div class="row">
      <div>
        <label>Logo Size</label>
        <input type="range" id="logoSize" min="0.2" max="0.6" step="0.05" value="0.35">
      </div>
      <div>
        <label>Logo Margin</label>
        <input type="range" id="logoMargin" min="0" max="20" step="1" value="8">
      </div>
    </div>
    <label><input type="checkbox" id="hideBgDots"> Hide dots under logo</label>
    <button class="button" onclick="downloadQR()">Download PNG</button>
    <div class="note">Detected QR link auto-fills when available.</div>
  </div>
  <div class="preview"><div id="qrContainer"></div></div>
</div>
<div id="aboutSection" class="about-section" style="display:none;">
  <div class="about-header">
    <h2>About us</h2>
  </div>
  <div class="team-container">
    <div class="team-member no-image">
      <div class="member-name">Varun</div>
      <div class="member-role">Ethical Hacker</div>
      <div class="member-bio">
        <p>I'm a passionate cybersecurity enthusiast with a strong interest in ethical hacking, red teaming, and web application security. I spend my time learning, building tools, and simulating real-world attacks in safe environments to sharpen my skills. I'm currently exploring opportunities to grow and contribute within the cybersecurity field.</p>
      </div>
      <div class="social-links">
        <a href="https://github.com/mr-pentest" target="_blank" class="social-link" title="GitHub"><i class="fab fa-github"></i></a>
        <a href="https://www.linkedin.com/in/mr-pentest" target="_blank" class="social-link" title="LinkedIn"><i class="fab fa-linkedin-in"></i></a>
        <a href="#" class="social-link" title="Twitter"><i class="fab fa-twitter"></i></a>
        <a href="https://www.instagram.com/mr_pentest1/" target="_blank" class="social-link" title="Instagram"><i class="fab fa-instagram"></i></a>
        <a href="#" class="social-link" title="Discord"><i class="fab fa-discord"></i></a>
      </div>
    </div>
    <div class="team-member no-image">
      <div class="member-name">Aashish Kumar</div>
      <div class="member-role">Cybersecurity Mentor</div>
      <div class="member-bio">
        <p>Cybersecurity teacher, creator, and Co-Founder of M Cyber Academy. Provided expert guidance throughout the development of Eden, sharing invaluable insights from years of industry experience.</p>
      </div>
      <div class="social-links">
        <a href="https://www.linkedin.com/in/aashish-kumar-hak0r" target="_blank" class="social-link" title="LinkedIn"><i class="fab fa-linkedin-in"></i></a>
        <a href="https://www.instagram.com/mcyberacademy/" target="_blank" class="social-link" title="Instagram"><i class="fab fa-instagram"></i></a>
        <a href="#" class="social-link" title="Twitter"><i class="fab fa-twitter"></i></a>
        <a href="#" class="social-link" title="Discord"><i class="fab fa-discord"></i></a>
      </div>
    </div>
  </div>
</div>
<script>
var DEMO='https://example.com/demo';
let qrCode = new QRCodeStyling({
  width: 300,
  height: 300,
  type: "png",
  data: "",
  image: "",
  margin: 12,
  dotsOptions: { type: "square", color: "#000000", scale: 1 },
  cornersSquareOptions: { type: "square", color: "#000000", scale: 1 },
  cornersDotOptions: { type: "square", color: "#000000", scale: 1 }
});
qrCode.append(document.getElementById("qrContainer"));
let userEditedText=false; let lastLink=null;
let lastQRConfig = null;

function getQRConfig(){
  const eyeSel = document.getElementById("eyeStyle").value;
  const innerSel = document.getElementById("innerEyeStyle").value;
  const eyeTypes = eyeSel === 'circle' ? { cs:'extra-rounded' } : { cs:'square' };
  const innerType = innerSel === 'dot' ? 'dot' : 'square';
  const colorMode = document.getElementById("colorMode").value;
  const gradientType = document.getElementById("gradientType").value;
  const primary = document.getElementById("dotPrimary").value;
  const primary2 = document.getElementById("dotPrimary2") ? document.getElementById("dotPrimary2").value : primary;
  const secondary = document.getElementById("dotSecondary").value;
  const bgStyle = document.getElementById("backgroundStyle").value;
  const bgColor = document.getElementById("backgroundColor").value;
  const eyeOuterColor = document.getElementById("eyeOuterColor").value;
  const eyeInnerColor = document.getElementById("eyeInnerColor").value;
  
  // Use primary2 if available, otherwise primary
  const dotColor = primary2 || primary;
  
  let dotsOptions = { type: document.getElementById("dotStyle").value, color: dotColor, scale: 1 };
  if(colorMode !== 'single'){
    dotsOptions = {
      type: document.getElementById("dotStyle").value,
      gradient: {
        type: gradientType,
        rotation: 0,
        colorStops: [
          { offset: 0, color: dotColor },
          { offset: 1, color: secondary }
        ]
      },
      scale: 1
    };
  }
  const backgroundOptions = { color: (bgStyle === 'transparent' ? 'transparent' : (bgStyle === 'white' ? '#ffffff' : bgColor)) };
  
  return {
    data: document.getElementById("qrText").value || " ",
    image: document.getElementById("logoUrl").value || "",
    margin: 12,
    imageOptions: { imageSize: Number(document.getElementById("logoSize").value), margin: Number(document.getElementById("logoMargin").value), hideBackgroundDots: document.getElementById("hideBgDots").checked },
    dotsOptions: dotsOptions,
    cornersSquareOptions: { type: eyeTypes.cs, color: eyeOuterColor, scale: 1 },
    cornersDotOptions: { type: innerType, color: eyeInnerColor, scale: 1 },
    backgroundOptions: backgroundOptions
  };
}

function applyUI(){
  const newConfig = getQRConfig();
  const configStr = JSON.stringify(newConfig);
  
  // Only update if configuration actually changed
  if(lastQRConfig !== configStr){
    lastQRConfig = configStr;
    qrCode.update(newConfig);
  }
}
document.getElementById("qrText").addEventListener("input", function(){ userEditedText=true; applyUI(); });
document.getElementById("logoUrl").addEventListener("input", applyUI);
document.getElementById("dotStyle").addEventListener("input", applyUI);
document.getElementById("eyeStyle").addEventListener("input", applyUI);
document.getElementById("eyeOuterColor").addEventListener("input", applyUI);
document.getElementById("eyeInnerColor").addEventListener("input", applyUI);
document.getElementById("innerEyeStyle").addEventListener("input", applyUI);
document.getElementById("colorMode").addEventListener("input", applyUI);
document.getElementById("gradientType").addEventListener("input", applyUI);
document.getElementById("dotPrimary").addEventListener("input", function(){
  applyUI();
  if(document.getElementById("dotPrimary2")) document.getElementById("dotPrimary2").value = document.getElementById("dotPrimary").value;
});
if(document.getElementById("dotPrimary2")){
  document.getElementById("dotPrimary2").addEventListener("input", function(){
    document.getElementById("dotPrimary").value = document.getElementById("dotPrimary2").value;
    applyUI();
  });
}
document.getElementById("dotSecondary").addEventListener("input", applyUI);
document.getElementById("backgroundStyle").addEventListener("input", applyUI);
document.getElementById("backgroundColor").addEventListener("input", applyUI);
document.getElementById("logoSize").addEventListener("input", applyUI);
document.getElementById("logoMargin").addEventListener("input", applyUI);
document.getElementById("hideBgDots").addEventListener("input", applyUI);
function pushStyle(){
  const payload = {
    dotStyle: document.getElementById("dotStyle").value,
    dotColor: document.getElementById("dotPrimary").value,
    eyeStyle: document.getElementById("eyeStyle").value,
    innerEyeStyle: document.getElementById("innerEyeStyle").value,
    eyeOuterColor: document.getElementById("eyeOuterColor").value,
    eyeInnerColor: document.getElementById("eyeInnerColor").value,
    colorMode: document.getElementById("colorMode").value,
    gradientType: document.getElementById("gradientType").value,
    dotPrimary: document.getElementById("dotPrimary").value,
    dotSecondary: document.getElementById("dotSecondary").value,
    backgroundStyle: document.getElementById("backgroundStyle").value,
    backgroundColor: document.getElementById("backgroundColor").value,
    logoUrl: document.getElementById("logoUrl").value,
    logoSize: Number(document.getElementById("logoSize").value),
    logoMargin: Number(document.getElementById("logoMargin").value),
    hideBgDots: document.getElementById("hideBgDots").checked
  };
  fetch('/api/style', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
}
['dotStyle','dotPrimary','dotSecondary','eyeStyle','innerEyeStyle','eyeOuterColor','eyeInnerColor','colorMode','gradientType','backgroundStyle','backgroundColor','logoUrl','logoSize','logoMargin','hideBgDots'].forEach(function(id){
  const el = document.getElementById(id);
  if(el) el.addEventListener('input', pushStyle);
});
if(document.getElementById("dotPrimary2")){
  document.getElementById("dotPrimary2").addEventListener('input', pushStyle);
}
function loadStyle(){
  fetch('/api/style').then(function(r){ return r.json(); }).then(function(s){
    if(s){
      document.getElementById('dotStyle').value = s.dotStyle || 'square';
      const dotPrimaryVal = (s.dotPrimary || s.dotColor || '#000000');
      document.getElementById('dotPrimary').value = dotPrimaryVal;
      if(document.getElementById('dotPrimary2')) document.getElementById('dotPrimary2').value = dotPrimaryVal;
      document.getElementById('dotSecondary').value = s.dotSecondary || '#1f2937';
      document.getElementById('colorMode').value = s.colorMode || 'single';
      document.getElementById('gradientType').value = s.gradientType || 'linear';
      document.getElementById('eyeStyle').value = s.eyeStyle || 'square';
      document.getElementById('innerEyeStyle').value = s.innerEyeStyle || 'square';
      document.getElementById('eyeOuterColor').value = s.eyeOuterColor || s.eyeColor || '#000000';
      document.getElementById('eyeInnerColor').value = s.eyeInnerColor || s.eyeColor || '#000000';
      document.getElementById('backgroundStyle').value = s.backgroundStyle || 'white';
      document.getElementById('backgroundColor').value = s.backgroundColor || '#ffffff';
      document.getElementById('logoUrl').value = s.logoUrl || '';
      document.getElementById('logoSize').value = s.logoSize || 0.35;
      document.getElementById('logoMargin').value = s.logoMargin || 8;
      document.getElementById('hideBgDots').checked = !!s.hideBgDots;
      applyUI();
    }
  }).catch(function(){});
}
function poll(){
  fetch('/api/current_qr').then(function(r){ return r.json(); }).then(function(j){
    if(j && j.suppress){
      document.getElementById('qrContainer').style.display='none';
      lastLink=null;
      return;
    }
    document.getElementById('qrContainer').style.display='';
    if(j && j.link){
      if(!userEditedText){
        const currentText = document.getElementById('qrText').value;
        if(currentText !== j.link){
          document.getElementById('qrText').value = j.link;
        }
      }
      if(lastLink!==j.link){
        lastLink=j.link;
        applyUI();
      }
    } else {
      if(!userEditedText){
        const currentText = document.getElementById('qrText').value;
        if(currentText !== DEMO){
          document.getElementById('qrText').value = DEMO;
          applyUI();
        }
      }
    }
  }).catch(function(){});
}
setInterval(poll,500); poll();
loadStyle();
function downloadQR(){ qrCode.download({ name: "custom_qr", extension: "png" }); }
document.getElementById('navHome').addEventListener('click', function(){
  document.getElementById('designer').style.display='';
  document.getElementById('aboutSection').style.display='none';
  document.getElementById('navHome').classList.add('active');
  document.getElementById('navAbout').classList.remove('active');
});
document.getElementById('navAbout').addEventListener('click', function(){
  document.getElementById('designer').style.display='none';
  document.getElementById('aboutSection').style.display='';
  document.getElementById('navAbout').classList.add('active');
  document.getElementById('navHome').classList.remove('active');
});
</script>
</body>
</html>
"""

@app.route("/AlphaQR")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/<path:filename>")
def serve_file(filename):
    base_dir = os.getcwd()
    return send_from_directory(base_dir, filename)

@app.route("/api/current_qr", methods=["GET"])
def get_current_qr():
    global current_qr_link, last_update_time
    if current_qr_link:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(current_qr_link)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        qr_image_data = f"data:image/png;base64,{img_str}"
        return jsonify({
            "link": current_qr_link,
            "qr_image": qr_image_data,
            "timestamp": last_update_time
        })
    return jsonify({
        "link": None,
        "qr_image": None,
        "timestamp": None
    })

@app.route("/api/style", methods=["GET", "POST"])
def style_api():
    global style_options
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        for k in [
            "dotStyle","dotColor","eyeStyle","innerEyeStyle","eyeColor",
            "eyeOuterColor","eyeInnerColor",
            "colorMode","gradientType","dotPrimary","dotSecondary",
            "backgroundStyle","backgroundColor","logoUrl","logoSize",
            "logoMargin","hideBgDots"
        ]:
            if k in data:
                style_options[k] = data[k]
        return jsonify(style_options)
    return jsonify(style_options)

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route("/receive_screenshot", methods=["POST"])
def receive_screenshot():
    global current_qr_link, last_update_time
    
    data = request.get_json()
    image_data = data.get("image")
    
    if not image_data:
        return jsonify({"error": "no image"}), 400
    
    try:
        # Decode base64 image
        img_bytes = base64.b64decode(image_data.split(",")[1])
        img = Image.open(BytesIO(img_bytes))
        
        # Convert to grayscale for better QR detection
        if img.mode != 'L':
            img = img.convert('L')
        
        # Resize if too large (for faster processing)
        width, height = img.size
        if width > 2000 or height > 2000:
            scale = min(2000 / width, 2000 / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Try to decode QR code
        result = decode(img)
        
        if result and len(result) > 0:
            decoded_link = result[0].data.decode('utf-8')
            if decoded_link == DEMO_LINK:
                return jsonify({
                    "success": True,
                    "link": decoded_link,
                    "changed": False
                })
            was_empty = current_qr_link is None
            link_changed = False
            if was_empty or decoded_link != current_qr_link:
                current_qr_link = decoded_link
                last_update_time = datetime.datetime.now().isoformat()
                link_changed = True
                if was_empty:
                    print("\033[92mQR found\033[0m")
                else:
                    print("\033[96mQR updated\033[0m")
            return jsonify({
                "success": True,
                "link": decoded_link,
                "changed": link_changed
            })
        else:
            # No QR code found in this screenshot
            return jsonify({
                "success": False,
                "message": "No QR code found in screenshot"
            })
            
    except Exception as e:
        print(f"❌ Error processing screenshot: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == "__main__":
    print("\n\033[95m" + "="*50 + "\033[0m")
    print("\033[94m🚀 QR Code Listener Started!\033[0m")
    print("\033[93m📱 Open http://localhost:5000/AlphaQR in your browser\033[0m")
    print("\033[95m" + "="*50 + "\033[0m\n")
    try:
        app.run(port=5000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\033[91mexiting...\033[0m")
        sys.exit(0)
