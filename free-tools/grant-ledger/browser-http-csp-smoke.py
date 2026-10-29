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
    # Correct the recorded transaction without losing its ID or unrelated evidence.
    edit = page.locator('#expenseRows button[data-edit-index="0"]')
    assert edit.get_attribute("aria-label") == "Edit expenditure 000123"
    edit.click()
    assert expense.locator('[name="transactionId"]').input_value() == "000123"
    assert expense.locator('[name="transactionId"]').evaluate("(e) => e.readOnly")
    assert page.evaluate("document.activeElement.name") == "sourceId"
    assert page.locator("#cancelExpenseEdit").is_visible()
    expense.locator('[name="sourceId"]').fill(" SRC-CORRECTED ")
    expense.locator('[name="amount"]').fill("8.00")
    expense.locator('[name="note"]').fill("Corrección – \u65e5\u672c\u8a9e")
    expense.locator('button[type="submit"]').click()
    assert page.locator("#expenseRows tr").count() == 1
    assert " SRC-CORRECTED " in page.locator("#expenseRows tr").first.evaluate("(e) => e.textContent")
    assert "$8.00" in page.locator("#expenseRows").inner_text()
    assert page.evaluate("document.activeElement.dataset.editIndex") == "0", "save restores edit focus"
    assert "corrected" in page.locator("#status").inner_text()
    assert "1 expenditure correction recorded" in page.locator("#correctionSummary").inner_text()
    edit = page.locator('#expenseRows button[data-edit-index="0"]')
    edit.click()
    expense.locator('[name="amount"]').fill("not-a-number")
    expense.locator('button[type="submit"]').click()
    assert page.locator("#error").is_visible(), "invalid correction reported"
    assert page.evaluate("document.activeElement.id") == "error"
    assert "$8.00" in page.locator("#expenseRows").inner_text(), "invalid correction must not change saved amount"
    page.locator("#cancelExpenseEdit").click()
    assert page.locator("#error").is_hidden()
    assert page.evaluate("document.activeElement.dataset.editIndex") == "0", "cancel restores edit focus"
    assert "$8.00" in page.locator("#expenseRows").inner_text(), "cancel retains saved amount"
    assert "1 expenditure correction recorded" in page.locator("#correctionSummary").inner_text(), "invalid/cancel edits never append history"
    # Review flags must carry the exact source, transaction, and category IDs.
    # The synthetic HTML-looking identifier must remain inert text.
    unsafe_source = " SRC-0008 <img src=x onerror=alert(1)> "
    expense.locator('[name="transactionId"]').fill("000124")
    expense.locator('[name="sourceId"]').fill(unsafe_source)
    expense.locator('[name="date"]').fill("2027-01-01")
    expense.locator('[name="categoryId"]').select_option("001")
    expense.locator('[name="amount"]').fill("12.00")
    expense.locator('[name="percent"]').fill("50")
    expense.locator('[name="evidenceRef"]').fill("")
    expense.locator('button[type="submit"]').click()
    flags = page.locator("#reviewList li").all_inner_texts()
    assert len(flags) == 4, flags
    # Playwright inner_text normalizes visual whitespace; DOM textContent must retain raw spaces.
    visible_source = " ".join(unsafe_source.split())
    assert all("Transaction 000124" in f and "Source " + visible_source in f and "Category 001" in f for f in flags[:3]), flags
    assert "Source " + unsafe_source in page.locator("#reviewList li").first.evaluate("(node) => node.textContent"), "DOM retains raw identifier"
    assert any("Date outside award period" in f for f in flags), flags
    assert any("Partial allocation lacks documented basis" in f for f in flags), flags
    assert any("Supporting evidence reference missing" in f for f in flags), flags
    assert any(f.startswith("Category 001: Budget comparison:") for f in flags), flags
    assert page.locator("#reviewList img").count() == 0, "untrusted identifier must render as text"
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
    # Current-only download deliberately excludes prior correction values, not current user-entered data.
    assert page.get_by_role("button", name="Current-state JSON (no correction history)").count() == 1
    assert page.get_by_role("button", name="Evidence JSON (with correction history)").count() == 1
    with page.expect_download() as current_info:
        page.locator("#downloadCurrentJSON").click()
    assert current_info.value.suggested_filename == "grant-current-state.json"
    import json
    current_state_text = Path(current_info.value.path()).read_text(encoding="utf-8")
    current_state = json.loads(current_state_text)
    assert "correctionHistory" not in current_state, "current-only export must omit correction log"
    assert " SRC-0007 " not in current_state_text, "old source ID must not leak from history"
    assert current_state["expenses"][0]["sourceId"] == " SRC-CORRECTED "
    assert current_state["expenses"][0]["totalCents"] == 800
    assert current_state["expenses"][0]["note"] == "Corrección – 日本語"
    assert current_state["lines"][1]["label"] == "=2+2", "current data preserved exactly"
    assert "grant-current-state.json downloaded" in page.locator("#status").inner_text()
    assert page.locator("#error").is_hidden(), "current-state JSON clears stale CSV error"
    with page.expect_download() as info:
        page.locator("#downloadJSON").click()
    data = Path(info.value.path()).read_text(encoding="utf-8")
    evidence = json.loads(data)
    assert evidence["lines"][1]["label"] == "=2+2", "JSON retains risky original"
    assert evidence["expenses"][0]["transactionId"] == "000123", "correction preserves transaction ID"
    assert evidence["expenses"][0]["sourceId"] == " SRC-CORRECTED ", "corrected source ID exact"
    assert evidence["expenses"][0]["totalCents"] == 800, "corrected amount preserved"
    assert evidence["expenses"][0]["note"] == "Corrección – 日本語", "corrected Unicode preserved"
    assert evidence["correctionHistory"]["schema"] == "expenditure-corrections-v1"
    assert len(evidence["correctionHistory"]["entries"]) == 1
    change = evidence["correctionHistory"]["entries"][0]
    assert change["revision"] == 1 and change["transactionId"] == "000123"
    assert change["before"]["sourceId"] == " SRC-0007 " and change["before"]["amount"] == "5.00"
    assert change["after"]["sourceId"] == " SRC-CORRECTED " and change["after"]["amount"] == "8.00"
    assert change["after"]["note"] == "Corrección – 日本語"
    assert "Award and budget-category edits are not recorded." in evidence["correctionHistory"]["scope"]
    assert evidence["expenses"][1]["sourceId"] == unsafe_source, "JSON preserves untrusted source ID exactly"
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
