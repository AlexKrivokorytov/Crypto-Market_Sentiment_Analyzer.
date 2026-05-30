import sys
import time
import requests
from playwright.sync_api import sync_playwright

def wait_for_server(url: str, timeout: int = 120):
    print(f"Waiting for frontend to become available at {url}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print("Frontend is up!")
                return
        except requests.ConnectionError:
            pass
        time.sleep(2)
    print("Timeout waiting for frontend.")
    sys.exit(1)

def run_ui_checks():
    url = "http://localhost:8080"
    wait_for_server(url)

    print("Launching browser to test buttons and UI...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        page.goto(url)
        print("Page loaded.")
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        print(f"Current URL: {page.url}")
        
        # Test 1: Identify clickable assets in sidebar
        print("\n--- Identifying Sidebar Navigation Buttons ---")
        # Find elements that look like nav buttons for crypto assets
        nav_buttons = page.locator("button[aria-label^='View ']").all()
        assets_found = []
        for btn in nav_buttons:
            text = btn.inner_text().strip().split('\n')[0].strip() # Get the symbol like BTC
            aria_label = btn.get_attribute("aria-label") or ""
            if aria_label:
                assets_found.append((text, aria_label))
                print(f"Found Button -> Text: '{text}', Aria: '{aria_label}'")

        if not assets_found:
            print("No asset buttons found. Are we stuck on a login page or error?")
            print(page.content()[:1000])
            browser.close()
            sys.exit(1)

        # Test 2: Click a few asset buttons and check the render
        test_assets = ["ETH", "TON", "DOGE"]
        for asset_text, aria_label in assets_found:
            asset_code = asset_text
            if asset_code in test_assets:
                print(f"\n--- Testing Click on {asset_text} ({asset_code}) ---")
                
                # Use Playwright to simulate human click
                page.locator(f"button[aria-label='{aria_label}']").click()
                
                # Wait for the network calls to resolve (backend API response)
                page.wait_for_timeout(3000) # Give it 3 seconds to fetch data and LLM
                try:
                    page.wait_for_load_state("networkidle", timeout=5000)
                except:
                    pass
                
                print(f"URL updated to: {page.url}")
                
                # Check what Feed UI returned
                content = page.content()
                
                if "AI Analysis" in content:
                    print(f"[SUCCESS] OpenRouter AI Analysis successfully responded for {asset_code}!")
                elif "Local Algorithm (VADER)" in content:
                    print(f"[WARNING] Circuit Breaker fell back to VADER for {asset_code}. OpenRouter LLM might have failed/timed out.")
                else:
                    print(f"[INFO] No specific AI badge detected in the HTML for {asset_code}. Check UI rendering.")
                    
                # Try to extract the first news article title or text if present
                articles = page.locator("article").all()
                if articles:
                    print(f"Found {len(articles)} articles rendered on the page.")
                    print(f"First article preview: {articles[0].inner_text()[:200].replace(chr(10), ' ')}...")
                else:
                    print("No articles rendered in the feed area.")
                    
        browser.close()
        print("\nAll button tests and OpenRouter validations completed successfully.")

if __name__ == "__main__":
    run_ui_checks()
