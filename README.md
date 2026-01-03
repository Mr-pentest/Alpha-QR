# Alpha QR
A security-focused utility for QR code styling, real-time preview, and browser-based QR scanning.

Repository: `https://github.com/Mr-pentest/Alpha-QR.git`

---

## Overview
Alpha QR provides a lightweight local environment for generating and styling QR codes, previewing them in real time, and integrating them into webpages.  
A companion Chrome extension enables live QR detection directly from the active browser tab.

This project is primarily intended for **authorized security research,
controlled simulations, and educational demonstrations**.

---

## Terminal-banner

![Terminal-banner](Assets/Terminal-banner.png)

Alpha QR startup banner showing the local server status,
designer URL, and Alpha.js embed information.

---

## Chrome Extension (Live on WhatsApp Login Page)

![Extention](Assets/Extention.png)

The Alpha QR browser extension actively scanning a WhatsApp login page.
This demonstrates real-time QR detection directly from the active browser tab.

---

## QR Designer Interface

![Designer](Assets/Designer.png)

The QR Designer interface is used to generate and style QR codes,
manage detection logic, and configure fallback behavior.

---

## Select (Keyword + HTML Configuration)

![Select](Assets/Select.png)

In this step:
- A chat-loading animation HTML file is uploaded
- The detection keyword **`have`** is saved
- The uploaded HTML file is selected as the fallback payload

This configuration is prepared for controlled QR-based simulation.

---

## QR-displayed (Split Tab View)

![QR-displayed](Assets/QR-displayed.png)

Split-tab view showing:
- One page where the QR is detected by the extension
- One page where the QR output is displayed in real time

This confirms end-to-end QR detection and rendering.

---

## Demo

The video below demonstrates the complete controlled simulation flow.
![QR-displayed](Assets/AlphaQR.gif)



### Demonstrated Flow
1. Victim-side QR is scanned  
2. Attacker-side browser session becomes active  
3. Detection keyword disappears from the attacker interface  
4. Selected chat-loading animation HTML is displayed on the victim browser  
5. Victim is redirected to the original `web.whatsapp.com` page  

⚠️ This demonstration is performed **only in a controlled lab environment**
for security research and awareness purposes.

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
