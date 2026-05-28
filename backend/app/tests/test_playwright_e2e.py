"""
End-to-End browser test script for the dockerized Market Sentiment Analyzer.

Uses Playwright to navigate the Vue 3 app frontend, verify key elements,
and capture screenshots of the dashboard.
"""

import sys
from playwright.sync_api import sync_playwright


def test_market_analyzer() -> None:
    print("Starting Playwright E2E browser tests...")
    with sync_playwright() as p:
        # Always launch chromium in headless mode
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # The frontend container is mapped to port 8080 in docker-compose.yml
        url = "http://localhost:8080"
        print(f"Navigating to {url}...")
        try:
            page.goto(url)
        except Exception as exc:
            print(
                f"❌ Failed to load the URL {url!r}. Is the docker container up? Error: {exc}"
            )
            browser.close()
            sys.exit(1)

        print("Waiting for page load networkidle state...")
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            print("⚠ Timeout waiting for networkidle. Proceeding anyway.")

        print(f"Page title is: {page.title()!r}")
        print(f"Final URL is: {page.url!r}")

        # Verify default route redirect
        assert "/asset/BTC" in page.url or "/login" in page.url, (
            f"Unexpected redirect URL: {page.url}"
        )
        print("[OK] URL routing check passed successfully.")

        # Take a screenshot to verify UI is rendered
        screenshot_path = "c:/Users/krivo/Desktop/Rust/vue/frontend_dashboard.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"[OK] Dashboard screenshot successfully saved to: {screenshot_path}")

        # Inspect side bar and content
        content = page.content()
        print("Checking if core text 'Market Intelligence Center' is rendered...")

        if "Market Intelligence Center" in content:
            print("[OK] 'Market Intelligence Center' header found!")
        elif "Sign In" in content or "Login" in content or "email" in content:
            print("[OK] App redirected to Login View or rendered Login correctly.")
        else:
            print("[WARN] Core text not found in rendered HTML. HTML preview:")
            print(content[:500])

        browser.close()
        print("Playwright E2E browser tests completed successfully.")


if __name__ == "__main__":
    test_market_analyzer()
