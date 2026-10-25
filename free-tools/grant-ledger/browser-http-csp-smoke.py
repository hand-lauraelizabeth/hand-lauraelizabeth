"""HTTP-served, synthetic-only FT-06 cross-browser export and CSP regression."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

def verify(browser_type, url, width):
    browser = browser_type.launch(headless=True)
    page = browser.new_page(viewport={"width": width, "height": 800}, accept_downloads=True)
    errors, requests = [], []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("request", lambda req: requests.append(req.url))
    page.goto(url, wait_until="networkidle")
    assert page.get_by_role("heading", name="Grant Budget and Evidence Ledger").count() == 1
    assert page.locator("#privacyNotice").is_visible()
    category = page.locator("#categoryForm")
    category.locator('[name="categoryId"]').fill("001")
    category.locator('[name="label"]').fill("Program delivery")
    category.locator('[name="budget"]').fill("10.00")
    category.locator('button[type="submit"]').click()
    assert page.locator("#budgetRows tr").count() == 1
    expense = page.locator("#expenseForm")
    expense.locator('[name="transactionId"]').fill("000123")
    expense.locator('[name="sourceId"]').fill(" SRC-0007 ")
    expense.locator('[name="date"]').fill("2026-02-01")
    expense.locator('[name="categoryId"]').select_option("001")
    expense.locator('[name="amount"]').fill("5.00")
    expense.locator('[name="evidenceRef"]').fill("receipt-01")
    expense.locator('button[type="submit"]').click()
    assert page.locator("#expenseRows tr").count() == 1
    with page.expect_download() as info:
        page.locator("#downloadTransactions").click()
    csv = Path(info.value.path()).read_text(encoding="utf-8-sig")
    assert '"000123"' in csv and '" SRC-0007 "' in csv, "CSV exact identifiers"
    assert '"500"' in csv, "integer cents preserved"
    category.locator('[name="categoryId"]').fill("002")
    category.locator('[name="label"]').fill("=2+2")
    category.locator('[name="budget"]').fill("1.00")
    category.locator('button[type="submit"]').click()
    assert page.locator("#budgetRows tr").count() == 2
    page.locator("#downloadBudget").click()
    assert page.locator("#error").is_visible(), "unsafe CSV blocked"
    assert "label" in page.locator("#error").inner_text()
    assert page.evaluate("document.activeElement.id") == "error", "error focus"
    assert "CSV unavailable" in page.locator("#status").inner_text()
    with page.expect_download() as info:
        page.locator("#downloadJSON").click()
    data = Path(info.value.path()).read_text(encoding="utf-8")
    import json
    evidence = json.loads(data)
    assert evidence["lines"][1]["label"] == "=2+2", "JSON retains risky original"
    assert evidence["expenses"][0]["sourceId"] == " SRC-0007 "
    assert page.locator("#error").is_hidden(), "successful Evidence JSON must clear stale CSV error"
    assert "grant-evidence.json downloaded" in page.locator("#status").inner_text(), "JSON success announced"
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "viewport reflow"
    assert not errors, errors
    assert all(req.startswith(url.rsplit("/", 1)[0] + "/") for req in requests), requests
    page.close()
    browser.close()
    print(f"PASS: {browser_type.name} {width}px HTTP/CSP/CSV/JSON/focus/reflow/local-only")

def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/index.html"
    try:
        with sync_playwright() as p:
            for engine in (p.chromium, p.firefox, p.webkit):
                for width in (320, 1280):
                    verify(engine, url, width)
    finally:
        server.shutdown()
        server.server_close()
    print("PASS: 6 synthetic HTTP-served browser scenarios")

if __name__ == "__main__":
    main()
