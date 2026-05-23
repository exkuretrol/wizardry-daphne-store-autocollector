"""
Wizardry Variants Daphne — JP webstore (webstore.wizardry.info) free-item autocollector.

Unlike the international store (store.wizardry.info), the JP webstore geo-restricts the
redeem action: clicking 受け取る from a non-Japan IP returns error code 70003
("お住まいの地域では、本サービスをご利用いただけません"). The login step is NOT
geo-restricted, but the redeem is — so this script must run from a Japan IP
(e.g. an Oracle Cloud Tokyo/Osaka VM).

Auth: logs in fresh each run with email + password. LINE/OAuth login is not automatable.

It logs in once, then walks FREE_PRODUCT_IDS, claiming any item with stock remaining and
skipping those already claimed (残り：0). The weekly reward recurs; the first-time bonus
self-skips after its single claim, so it's harmless to leave in the list.

Credentials come from environment variables:
    WIZARDRY_JP_EMAIL
    WIZARDRY_JP_PASSWORD

Optional, for research/testing from a non-JP host via a Japan proxy (NOT set on the VM,
which already has a native Japan IP):
    WIZARDRY_JP_PROXY   e.g. socks5://127.0.0.1:1080  (an SSH `-D` tunnel through the VM)

Exit codes:
    0  all available items claimed (or already claimed) — nothing left to do
    1  at least one item was region-blocked (error 70003) — not running from a Japan IP
    2  login failed / missing credentials
    3  unexpected error (element not found, timeout, etc.)

Every run writes a Playwright trace (artifacts/trace_jp.zip) and step screenshots to
./artifacts/ for debugging. View the trace with:  playwright show-trace artifacts/trace_jp.zip

Memory note: tuned for a 1 GB VM. Launches the headless-shell Chromium with lean flags.
Add swap on the VM (a 2 GB swapfile) before relying on this — Chromium can spike past 1 GB.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import Page, sync_playwright, TimeoutError as PWTimeout

BASE_URL = "https://webstore.wizardry.info"

# Free items to claim each run. The script claims any with stock and skips the rest,
# so order doesn't matter and already-claimed items are harmless.
FREE_PRODUCT_IDS = [
    "VvQwG2KoMz82",  # weekly recurring free reward — the primary cron target
    "D6Vj2rYxMjne",  # first-time-only bonus (オルグの貴石800個) — self-skips after one claim
]

ARTIFACT_DIR = Path(__file__).parent / "artifacts"

# Lean flags for a memory-constrained server with no display.
CHROMIUM_ARGS = ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]

# Region-block markers seen in the page when running from a non-JP IP.
BLOCK_MARKERS = ("70003", "ご利用いただけません", "ご利用が制限")

# Labels a post-受け取る confirmation dialog might use (if any).
CONFIRM_LABELS = ("受け取る", "確定", "確認", "はい", "OK")


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    print(f"[{ts}] {msg}", flush=True)


def shot(page: Page, name: str) -> None:
    """Best-effort screenshot; never let screenshotting break the flow."""
    try:
        page.screenshot(path=str(ARTIFACT_DIR / name))
    except Exception as e:  # noqa: BLE001
        log(f"(could not screenshot {name}: {e})")


def is_blocked(text: str) -> bool:
    return any(marker in text for marker in BLOCK_MARKERS)


def login(page: Page, email: str, password: str) -> bool:
    """Log in via the email+password form. Returns True on apparent success."""
    log("Opening login page...")
    page.goto(f"{BASE_URL}/login", wait_until="domcontentloaded")

    log("Choosing email login...")
    page.get_by_role("button", name="メールアドレスでログイン").click()

    log("Filling credentials...")
    page.get_by_role("textbox", name="メールアドレス").fill(email)
    page.get_by_role("textbox", name="パスワード").fill(password)

    log("Submitting login...")
    # Both the header and the modal expose a "ログイン" button; scope to the dialog.
    page.get_by_role("dialog", name="ログイン").get_by_role("button", name="ログイン").click()
    page.wait_for_timeout(3000)  # let the auth modal close + user state load
    shot(page, "01_after_login.png")

    # If the email-login button is still around, the modal didn't close -> login failed.
    if page.get_by_role("button", name="メールアドレスでログイン").count() > 0:
        log("Login appears to have failed (login form still visible — wrong creds or CAPTCHA?).")
        return False
    return True


def claim_one(page: Page, product_id: str, idx: int) -> str:
    """
    Attempt to claim a single free product.
    Returns one of: "claimed", "already", "blocked", "no_button".
    """
    log(f"[{product_id}] Opening product page...")
    page.goto(f"{BASE_URL}/product/{product_id}", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    shot(page, f"{idx:02d}_product_{product_id}.png")

    body = page.inner_text("body")
    if "残り：0" in body:
        log(f"[{product_id}] Already claimed this period (残り：0). Skipping.")
        return "already"

    receive = page.get_by_role("button", name="受け取る")
    if receive.count() == 0:
        log(f"[{product_id}] No 受け取る button found.")
        return "no_button"

    log(f"[{product_id}] Clicking 受け取る...")
    receive.first.click()
    page.wait_for_timeout(2500)  # server action + any dialog
    shot(page, f"{idx:02d}_after_receive_{product_id}.png")

    body = page.inner_text("body")
    if is_blocked(body):
        log(f"[{product_id}] BLOCKED: region restriction (error 70003).")
        shot(page, f"{idx:02d}_BLOCKED_{product_id}.png")
        return "blocked"

    # Optional confirmation dialog.
    dialog = page.get_by_role("dialog")
    if dialog.count() > 0:
        for label in CONFIRM_LABELS:
            btn = dialog.get_by_role("button", name=label)
            if btn.count() > 0 and btn.first.is_enabled():
                log(f"[{product_id}] Confirmation dialog; clicking '{label}'...")
                btn.first.click()
                page.wait_for_timeout(2500)
                shot(page, f"{idx:02d}_after_confirm_{product_id}.png")
                break

    body = page.inner_text("body")
    if is_blocked(body):
        log(f"[{product_id}] BLOCKED: region restriction (error 70003) after confirm.")
        shot(page, f"{idx:02d}_BLOCKED_{product_id}.png")
        return "blocked"

    log(f"[{product_id}] Claimed (no region error).")
    return "claimed"


def run_flow(page: Page, email: str, password: str) -> int:
    if not login(page, email, password):
        return 2

    results = {}
    for i, pid in enumerate(FREE_PRODUCT_IDS, start=2):  # 01_* is the login screenshot
        try:
            results[pid] = claim_one(page, pid, i)
        except PWTimeout as e:
            log(f"[{pid}] timeout: {e}")
            results[pid] = "error"
        except Exception as e:  # noqa: BLE001
            log(f"[{pid}] unexpected: {e!r}")
            results[pid] = "error"

    log(f"Summary: {results}")

    if any(v == "blocked" for v in results.values()):
        return 1
    if any(v == "error" for v in results.values()):
        return 3
    return 0  # everything claimed or already claimed


def main() -> int:
    email = os.environ.get("WIZARDRY_JP_EMAIL")
    password = os.environ.get("WIZARDRY_JP_PASSWORD")
    if not email or not password:
        log("ERROR: set WIZARDRY_JP_EMAIL and WIZARDRY_JP_PASSWORD environment variables.")
        return 2

    ARTIFACT_DIR.mkdir(exist_ok=True)

    launch_kwargs = {"headless": True, "args": CHROMIUM_ARGS}
    proxy = os.environ.get("WIZARDRY_JP_PROXY")
    if proxy:
        log(f"Routing through proxy: {proxy}")
        launch_kwargs["proxy"] = {"server": proxy}

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context(locale="ja-JP")
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()
        rc = 3
        try:
            rc = run_flow(page, email, password)
        except PWTimeout as e:
            log(f"ERROR: timed out: {e}")
            shot(page, "error_timeout.png")
        except Exception as e:  # noqa: BLE001
            log(f"ERROR: unexpected: {e!r}")
            shot(page, "error_unexpected.png")
        finally:
            context.tracing.stop(path=str(ARTIFACT_DIR / "trace_jp.zip"))
            browser.close()
        return rc


if __name__ == "__main__":
    sys.exit(main())
