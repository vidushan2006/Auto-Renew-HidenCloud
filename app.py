#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, sys, time, random, requests
try:
    from patchright.sync_api import sync_playwright
    USING_PATCHRIGHT = True
except ImportError:
    from playwright.sync_api import sync_playwright
    USING_PATCHRIGHT = False

COOKIE_VALUE = os.environ.get('COOKIE_VALUE') or ""
EMAIL        = os.environ.get('EMAIL') or "sahanvijesiri@gmail.com"
PASSWORD     = os.environ.get('PASSWORD') or "zx12cv34vidushan."
TG_CHAT_ID   = os.environ.get('TG_CHAT_ID') or ""
TG_BOT_TOKEN = os.environ.get('TG_BOT_TOKEN') or ""

# 📡 VIDU WhatsApp Bot Webhook Configuration (Allocation Port 24723)
WEBHOOK_URL   = os.environ.get('WEBHOOK_URL') or "http://lou.hidencloud.com:24723/api/renew-webhook"
WEBHOOK_TOKEN = os.environ.get('WEBHOOK_TOKEN') or "ptlc_5dDf5MBF1p4axsIzRTCe1L8KVIz1b0DytXFVdlneJb5"

BASE_URL = "https://dash.hidencloud.com"
LOGIN_URL = f"{BASE_URL}/auth/login"

IS_PROXY      = os.environ.get('IS_PROXY', 'false').lower() == 'true'
PROXY_SERVER  = os.environ.get('PROXY_SERVER') or "http://127.0.0.1:1081"
REQUESTS_PROXIES = {"http": PROXY_SERVER, "https": PROXY_SERVER} if IS_PROXY else None

CF_IFRAME_SELECTOR = 'iframe[src*="challenges.cloudflare.com"]'

if sys.platform == 'win32':
    DEFAULT_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
else:
    DEFAULT_UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'

def log(message):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}", flush=True)

STEALTH_JS = """
try {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
} catch (e) {}
"""

def notify_whatsapp_bot(expiry_date: str, status: str = "synced", cooldown: str = ""):
    if not expiry_date:
        return
    try:
        payload = {
            "token": WEBHOOK_TOKEN,
            "expiry": expiry_date,
            "status": status,
            "cooldown": cooldown
        }
        log(f"📡 Sending real-time renewal status to WhatsApp Bot ({status} | {expiry_date})...")
        res = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        if res.status_code == 200:
            log("✅ WhatsApp Bot acknowledged webhook (200 OK)")
        else:
            log(f"⚠️ WhatsApp Bot Webhook returned: {res.status_code} - {res.text}")
    except Exception as e:
        log(f"⚠️ Failed to connect to WhatsApp Bot webhook: {e}")

def get_current_ip(proxy_server=None):
    proxies = {"http": proxy_server, "https": proxy_server} if (proxy_server and IS_PROXY) else None
    try:
        resp = requests.get("https://api.ip.sb/ip", proxies=proxies, timeout=15)
        if resp.status_code == 200:
            return resp.text.strip()
        return "Unknown"
    except Exception as e:
        log(f"❌ Failed to get IP: {e}")
        return "Unknown"

def send_telegram_notification(status, old_due, new_due, current_ip="Unknown"):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return False
    
    local_time = time.gmtime(time.time() + 8 * 3600)
    now = time.strftime("%Y-%m-%d %H:%M:%S", local_time)
    if '@' in EMAIL:
        name, domain = EMAIL.split('@', 1)
        masked_email = f"{name[:2]}****{name[-2:]}@{domain}" if len(name) > 4 else f"{name}@{domain}"
    else:
        masked_email = EMAIL[:2] + '****'

    text = (
        f"🎉 HidenCloud Renewal Notification\n\n"
        f"{status}\n"
        f"👤 Account: {masked_email}\n"
        f"📅 Previous Due: {old_due}\n"
        f"📅 New Due: {new_due}\n"
        f"🌐 IP: {current_ip}\n"
        f"🕒 Time: {now}"
    )
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10, proxies=REQUESTS_PROXIES)
        return True
    except Exception:
        return False

def _get_turnstile_token(page):
    try:
        return page.evaluate(
            """
            () => {
                try {
                    if (window.turnstile && typeof window.turnstile.getResponse === 'function') {
                        let t = null;
                        try { t = window.turnstile.getResponse(); } catch (e) {}
                        if (t && t.length > 30) return t;
                        for (let i = 0; i < 5; i++) {
                            try { t = window.turnstile.getResponse(String(i)); } catch (e) { t = null; }
                            if (t && t.length > 30) return t;
                        }
                    }
                } catch (e) {}
                const inputs = document.querySelectorAll(
                    'input[name="cf-turnstile-response"], input[id$="_response"]'
                );
                for (const el of inputs) {
                    if (el.value && el.value.length > 30) return el.value;
                }
                return null;
            }
            """
        )
    except Exception:
        return None

def _find_visible_cf_frames(page):
    result = []
    try:
        for handle in page.query_selector_all(CF_IFRAME_SELECTOR):
            try:
                box = handle.bounding_box()
                if box and box['width'] > 10 and box['height'] > 10:
                    result.append(handle)
            except Exception:
                continue
    except Exception:
        pass
    return result

def _cf_checkbox_visible(page):
    for frame in page.frames:
        if 'challenges.cloudflare.com' not in (frame.url or ''):
            continue
        try:
            if frame.locator('input[type="checkbox"]:visible').count() > 0:
                return True
        except Exception:
            continue
    return False

def _click_cf_checkbox(page, frame_el=None):
    for frame in page.frames:
        if 'challenges.cloudflare.com' not in (frame.url or ''):
            continue
        try:
            frame.locator('input[type="checkbox"]').first.click(timeout=2500)
            return True
        except Exception:
            continue
    if frame_el is None:
        return False
    try:
        try:
            frame_el.scroll_into_view_if_needed(timeout=3000)
        except Exception:
            pass
        box = frame_el.bounding_box()
        if not box:
            return False
        x = box['x'] + random.uniform(18, 34)
        y = box['y'] + box['height'] / 2 + random.uniform(-4, 4)
        page.mouse.move(x - random.uniform(30, 60), y + random.uniform(-8, 8))
        time.sleep(random.uniform(0.15, 0.4))
        page.mouse.move(x, y)
        time.sleep(random.uniform(0.05, 0.2))
        page.mouse.down()
        time.sleep(random.uniform(0.04, 0.1))
        page.mouse.up()
        return True
    except Exception:
        return False

SECURITY_TITLE_HINTS = ('security verification', 'just a moment', 'attention required', 'checking your browser', 'please wait', 'one more step')

def _is_security_check_page(page):
    try:
        title = (page.title() or '').lower()
        if any(h in title for h in SECURITY_TITLE_HINTS):
            return True
    except Exception:
        return True
    try:
        return page.evaluate(
            """
            () => {
                const t = document.body ? document.body.innerText.slice(0, 5000).toLowerCase() : '';
                return t.includes('verify you are human') || t.includes('checking your browser')
                    || t.includes('security verification');
            }
            """
        )
    except Exception:
        return True

def _has_interstitial_iframe(page):
    try:
        for handle in page.query_selector_all(CF_IFRAME_SELECTOR):
            if '/turnstile/' not in (handle.get_attribute('src') or ''):
                return True
    except Exception:
        pass
    return False

def handle_cloudflare(page, timeout=240):
    def challenge_active():
        return _has_interstitial_iframe(page) or _is_security_check_page(page)

    if not challenge_active():
        for _ in range(3):
            time.sleep(1)
            if challenge_active():
                break
        else:
            return True

    log("🔒 Cloudflare Challenge detected...")
    time.sleep(5)

    effective_timeout = timeout + (180 if timeout > 60 else 0)
    start_time = time.time()
    last_click = 0
    clear_rounds = 0
    while time.time() - start_time < effective_timeout:
        if not challenge_active():
            clear_rounds += 1
            if clear_rounds >= 2: 
                return True
            time.sleep(1)
            continue
        clear_rounds = 0
        if time.time() - last_click > 6:
            frames = _find_visible_cf_frames(page)
            if frames:
                if _click_cf_checkbox(page, frames[-1]):
                    last_click = time.time()
                    time.sleep(random.uniform(3, 5))
                    continue
        time.sleep(1)
    return False

def solve_modal_turnstile(page, timeout=90):
    start = time.time()
    last_click = 0
    clicks = 0
    no_frame_seconds = 0
    while time.time() - start < timeout:
        if _get_turnstile_token(page):
            log("✅ Turnstile verified successfully")
            return True
        frames = _find_visible_cf_frames(page)
        if not frames:
            no_frame_seconds += 1
            if no_frame_seconds >= 20 and clicks == 0:
                return True
            time.sleep(1)
            continue
        no_frame_seconds = 0
        if clicks > 0 and time.time() - last_click > 4 and not _cf_checkbox_visible(page):
            time.sleep(2)
            if not _cf_checkbox_visible(page):
                return True
        if time.time() - last_click > 6 and _cf_checkbox_visible(page):
            if _click_cf_checkbox(page, frames[-1]):
                clicks += 1
                last_click = time.time()
                time.sleep(random.uniform(3, 5))
                continue
        time.sleep(1)
    return bool(_get_turnstile_token(page))

def open_browser(p):
    proxy_arg = {"server": PROXY_SERVER} if IS_PROXY else None
    if USING_PATCHRIGHT:
        browser = p.chromium.launch(
            channel="chrome",
            headless=False,
            args=['--disable-infobars'],
            proxy=proxy_arg,
        )
        ctx = browser.new_context(viewport=None, proxy=proxy_arg)
        page = ctx.new_page()
        return browser, page
    browser = p.chromium.launch(
        channel="chrome",
        headless=False,
        args=['--no-sandbox', '--disable-blink-features=AutomationControlled', '--disable-infobars']
    )
    ctx = browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent=DEFAULT_UA,
        proxy=proxy_arg,
    )
    page = ctx.new_page()
    page.add_init_script(STEALTH_JS)
    return browser, page

def _is_logged_in(page):
    try:
        url = page.url or ''
        return 'dash.hidencloud.com' in url and 'auth/login' not in url and not _is_security_check_page(page)
    except Exception:
        return False

def login(page):
    if COOKIE_VALUE:
        log("📇 Attempting Cookie login...")
        try:
            page.context.add_cookies([{
                'name': 'remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d',
                'value': COOKIE_VALUE,
                'domain': 'dash.hidencloud.com',
                'path': '/',
                'expires': int(time.time()) + 3600 * 24 * 365,
                'httpOnly': True,
                'secure': True,
                'sameSite': 'Lax'
            }])
            page.goto(f"{BASE_URL}/dashboard", wait_until="domcontentloaded", timeout=60000)
            handle_cloudflare(page, timeout=240)
            time.sleep(2)
            handle_cloudflare(page, timeout=60)
            if _is_logged_in(page):
                log("✅ Cookie login successful!")
                return True
        except Exception as e:
            log(f"⚠️ Cookie login attempt error: {e}")

    if not EMAIL or not PASSWORD:
        return False
    log("🔑 Attempting Credentials login...")
    try:
        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
        handle_cloudflare(page, timeout=240)
        time.sleep(8)
        user_input = page.locator('input[name="username"], input[name="email"], input[type="email"]').first
        pwd_input = page.locator('input[name="password"], input[type="password"]').first
        try:
            user_input.wait_for(state="visible", timeout=30000)
        except Exception:
            handle_cloudflare(page, timeout=120)
            user_input.wait_for(state="visible", timeout=30000)
        user_input.fill(EMAIL, timeout=10000)
        pwd_input.fill(PASSWORD, timeout=10000)
        time.sleep(0.5)
        handle_cloudflare(page, timeout=60)
        solve_modal_turnstile(page, timeout=90)
        time.sleep(3)
        try:
            page.click('button[type="submit"]', timeout=10000)
        except Exception:
            page.locator('button:has-text("Sign in")').first.click(timeout=10000)
        time.sleep(3)
        handle_cloudflare(page, timeout=240)
        page.goto(f"{BASE_URL}/dashboard", wait_until="domcontentloaded", timeout=60000)
        handle_cloudflare(page, timeout=120)
        if not _is_logged_in(page):
            log("❌ Login failed.")
            return False
        log("✅ Credentials login successful!")
        return True
    except Exception as e:
        log(f"❌ Login error: {e}")
        return False

def get_server_id(page):
    try:
        if 'dash.hidencloud.com' not in page.url:
            page.goto(f"{BASE_URL}/dashboard", wait_until="domcontentloaded", timeout=60000)
            handle_cloudflare(page)
            time.sleep(2)
        handle_cloudflare(page)
        time.sleep(3)
        html = page.content()

        matches = re.findall(r'/service/(\d+)/manage', html)
        if matches:
            return matches[0]

        matches = [m for m in re.findall(r'#(\d{4,})', html) if set(m) != {'0'}]
        if matches:
            return matches[0]
        return None
    except Exception as e:
        log(f"❌ Failed to locate Server ID: {e}")
        return None

def get_due_date(page):
    try:
        if SERVICE_URL not in page.url:
            page.goto(SERVICE_URL, wait_until="domcontentloaded", timeout=60000)
        handle_cloudflare(page)
        body_text = page.locator("body").inner_text()
        patterns = [
            r"Due date\s+(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})",
            r"Due date\s*\n\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})",
            r"Due date.*?(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})",
        ]
        for pattern in patterns:
            match = re.search(pattern, body_text, re.IGNORECASE | re.DOTALL)
            if match:
                due = match.group(1).strip()
                log(f"📅 Due Date detected: {due}")
                return due
    except Exception:
        pass
    return "Unknown"

def renew_service(page):
    try:
        log("➡ Initiating renewal flow...")
        if page.url != SERVICE_URL:
            page.goto(SERVICE_URL, wait_until="domcontentloaded", timeout=60000)
        handle_cloudflare(page)
        time.sleep(12)
        renew_btn = page.locator('button:has-text("Renew")')
        create_btn = page.locator('button:has-text("Create Invoice")')
        modal_opened = False
        for i in range(6):
            try:
                renew_btn.wait_for(state="visible", timeout=10000)
                renew_btn.scroll_into_view_if_needed()
                renew_btn.click()
                time.sleep(3)
                page_text = page.locator("body").inner_text()
                if "Renewal Restricted" in page_text or "can only renew" in page_text.lower():
                    log("⏳ Cooldown active: Server renewal not yet unlocked.")
                    return "NOT_TIME" 

                try:
                    create_btn.wait_for(state="visible", timeout=8000)
                    modal_opened = True
                    log("✅ Renewal invoice dialog visible")
                    break
                except:
                    time.sleep(2)
            except Exception as e:
                log(f"❌ Click error: {e}")

        if not modal_opened:
            return False

        handle_cloudflare(page, timeout=60)
        solve_modal_turnstile(page, timeout=90)

        new_invoice_url = None
        time.sleep(2)
        for attempt in range(6):
            try:
                create_btn.wait_for(state="visible", timeout=30000)
                create_btn.click(timeout=20000)
            except Exception:
                solve_modal_turnstile(page, timeout=45)
                time.sleep(2)
                continue

            start_wait = time.time()
            while time.time() - start_wait < 30:
                if "/payment/invoice/" in page.url:
                    new_invoice_url = page.url
                    break
                if _has_interstitial_iframe(page) or _is_security_check_page(page):
                    handle_cloudflare(page, timeout=60)
                time.sleep(1)
            if new_invoice_url:
                break
            solve_modal_turnstile(page, timeout=45)

        if not new_invoice_url:
            return False

        if page.url != new_invoice_url:
            page.goto(new_invoice_url)
        handle_cloudflare(page)

        pay_btn = page.locator('a:has-text("Pay"):visible, button:has-text("Pay"):visible').first
        pay_btn.wait_for(state="visible", timeout=30000)
        pay_btn.click()
        log("✅ Invoice successfully paid!")
        time.sleep(6)
        page.goto(SERVICE_URL, wait_until="domcontentloaded", timeout=60000)
        handle_cloudflare(page)
        return True
    except Exception as e:
        log(f"❌ Renewal error: {e}")
        return False

def main():
    global SERVICE_URL
    with sync_playwright() as p:
        browser = None
        try:
            current_ip = get_current_ip(PROXY_SERVER)
            log(f"🎯 IP: {current_ip}")
            browser, page = open_browser(p)

            if not login(page):
                notify_whatsapp_bot("", status="failed")
                sys.exit(1)

            server_id = get_server_id(page)
            if not server_id:
                notify_whatsapp_bot("", status="failed")
                sys.exit(1)
            SERVICE_URL = f"{BASE_URL}/service/{server_id}/manage"

            old_due = get_due_date(page)
            renew_result = renew_service(page)

            new_due = old_due
            if renew_result == "NOT_TIME":
                status = "⏳ On Cooldown"
                notify_whatsapp_bot(old_due, status="cooldown")
            elif renew_result is False:
                status = "❌ Renewal Failed"
                notify_whatsapp_bot(old_due, status="failed")
            else:
                new_due = get_due_date(page)
                status = "✅ Successfully Renewed (+7 Days)"
                notify_whatsapp_bot(new_due, status="renewed")

            send_telegram_notification(status, old_due, new_due, current_ip)
            sys.exit(0 if renew_result != False else 1)
        finally:
            if browser:
                try:
                    browser.close()
                except Exception:
                    pass

if __name__ == "__main__":
    main()
