import os
import time
from playwright.sync_api import sync_playwright

def run():
    print("Launching Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Capture console logs from browser
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        
        page.on("console", lambda msg: print(f"[Browser Console] {msg.type}: {msg.text}"))
        
        url = "http://localhost:8080/asset/BTC"
        print(f"Going to {url}...")
        page.goto(url)
        page.wait_for_load_state("networkidle")
        time.sleep(3) # Wait for hydration and feed render
        
        print("Taking initial screenshot...")
        page.screenshot(path="screenshot_before.png")
        print("Saved screenshot_before.png")
        
        # Locate the "Request Live AI Sentiment" button
        # In FeedItem.vue it is: <button @click="triggerAiAnalysis"> ... Request Live AI Sentiment </button>
        buttons = page.locator("button:has-text('Request Live AI')").all()
        print(f"Found {len(buttons)} 'Request Live AI Sentiment' buttons.")
        
        if not buttons:
            print("No buttons found. Page HTML:")
            print(page.content()[:1000])
            browser.close()
            return
            
        print("Clicking the first 'Request Live AI' button...")
        # Scroll into view and click
        buttons[0].scroll_into_view_if_needed()
        buttons[0].click()
        
        print("Button clicked. Waiting for real-time AI analysis (10s)...")
        time.sleep(10)
        
        print("Taking post-click screenshot...")
        page.screenshot(path="screenshot_after.png")
        print("Saved screenshot_after.png")
        
        # Print the text content of the first feed item
        feed_items = page.locator(".glass-card").all()
        if feed_items:
            print("\nFirst feed item text:")
            print(feed_items[0].inner_text())
            
        browser.close()
        print("Finished successfully.")

if __name__ == "__main__":
    run()
