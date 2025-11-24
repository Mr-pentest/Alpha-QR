# Alpha QR
A security-focused utility for QR code styling, real-time preview, and browser-based QR scanning.

Repository: `https://github.com/Mr-pentest/Alpha-QR.git`

---

## Overview
Alpha QR provides a lightweight local environment for generating and styling QR codes, previewing them in real time, and integrating them into webpages.  
A companion Chrome extension enables live QR detection directly from the active browser tab.

---

## Components

- **Start.py** — Flask server hosting the QR Designer interface  
- **Alpha.js** — Script for embedding the live QR output into any webpage  
- **AlphaQR/** — Chrome extension for starting/stopping real-time QR scanning  
- **test.html** — Basic example showing embedded QR rendering  

---

## Requirements

- Python **3.9+**  
- Git  
- Google Chrome or Chromium  

---

## Installation

```bash
git clone https://github.com/Mr-pentest/Alpha-QR.git
cd Alpha-QR
pip install flask pillow pyzbar qrcode
```

---

## Running the Server

```bash
python Start.py
```

Access the QR Designer interface at:

```
http://localhost:5000/AlphaQR
```

---

## Chrome Extension Setup

1. Open Chrome and navigate to:  
   `chrome://extensions`
2. Enable **Developer mode**
3. Select **Load unpacked**
4. Choose the `AlphaQR` directory

---

## Usage

### Extension
- Open any target webpage  
- Click the extension icon  
- Select **Start Scan** to begin QR detection  
- Return to the Designer page at `http://localhost:5000/AlphaQR` to view or style the captured data  
- Click **Stop Scan** to end the session  

### Embedding with `Alpha.js`

Add the following to any webpage:

```html
<div id="AlphaQR" style="width:300px;height:300px"></div>
<script src="http://127.0.0.1:5000/Alpha.js"></script>
```

The QR code will display automatically and update in real time if the extension is active.

---

## Example (`test.html`)

1. Run `python Start.py`  
2. Open `test.html` in a browser  
3. The live QR preview will appear inside the container  

If needed, update the script source:

```
http://127.0.0.1:5000/Alpha.js
```

---

## Legal & Responsible Use
Alpha QR is designed for authorized security analysis, research, and educational applications.  
Use only in environments where you have explicit permission.

---

## Stop / Uninstall

**Stop:**  
Close the terminal running `Start.py`.

**Uninstall:**  
Delete the cloned directory and remove the Chrome extension.

---

## License
This project is distributed under a **custom license authored by Varun**.  
Refer to the `LICENSE` file for full terms and usage rights.

---
