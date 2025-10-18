import asyncio
from playwright import async_api
from playwright.async_api import expect

async def run_test():
    pw = None
    browser = None
    context = None
    
    try:
        # Start a Playwright session in asynchronous mode
        pw = await async_api.async_playwright().start()
        
        # Launch a Chromium browser in headless mode with custom arguments
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--window-size=1280,720",         # Set the browser window size
                "--disable-dev-shm-usage",        # Avoid using /dev/shm which can cause issues in containers
                "--ipc=host",                     # Use host-level IPC for better stability
                "--single-process"                # Run the browser in a single process mode
            ],
        )
        
        # Create a new browser context (like an incognito window)
        context = await browser.new_context()
        context.set_default_timeout(5000)
        
        # Open a new page in the browser context
        page = await context.new_page()
        
        # Navigate to your target URL and wait until the network request is committed
        await page.goto("http://localhost:4371", wait_until="commit", timeout=10000)
        
        # Wait for the main page to reach DOMContentLoaded state (optional for stability)
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=3000)
        except async_api.Error:
            pass
        
        # Iterate through all iframes and wait for them to load as well
        for frame in page.frames:
            try:
                await frame.wait_for_load_state("domcontentloaded", timeout=3000)
            except async_api.Error:
                pass
        
        # Interact with the page elements to simulate user flow
        # -> Click 'Use sample.csv' button to upload the sample data file to proceed with inspection
        frame = context.pages[-1]
        # Click 'Use sample.csv' button to upload sample data file
        elem = frame.locator('xpath=html/body/div/div/div/div/div/div[2]/div/button[2]').nth(0)
        await page.wait_for_timeout(3000); await elem.click(timeout=5000)
        

        # -> Set sampling strategy to 'head' with specific row limit and seed, then click Analyze to call /api/inspect endpoint
        frame = context.pages[-1]
        # Set Rows limit to 5 for head sampling strategy
        elem = frame.locator('xpath=html/body/div/div/div/div/div/div[4]/div/input').nth(0)
        await page.wait_for_timeout(3000); await elem.fill('5')
        

        frame = context.pages[-1]
        # Set Seed to 123 for reproducible sampling
        elem = frame.locator('xpath=html/body/div/div/div/div/div/div[4]/div[2]/input').nth(0)
        await page.wait_for_timeout(3000); await elem.fill('123')
        

        frame = context.pages[-1]
        # Click Analyze button to call /api/inspect endpoint with sampling parameters
        elem = frame.locator('xpath=html/body/div/div/div/div/div/div[6]/button').nth(0)
        await page.wait_for_timeout(3000); await elem.click(timeout=5000)
        

        # --> Assertions to verify final state
        frame = context.pages[-1]
        await expect(frame.locator('text=Selected: data.csv (0.0 KB)').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=Uploaded path: /Users/benjaminsobel/Code/hackathon_oct_25/backend/uploads/d2aa27b2b55b46d29b07fc8d8f6541d8.csv').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=Use sample.csv').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=csv').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=Seed').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=pandas').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=plotly').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text={"a": "int64", "b": "int64"}').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=[{"a": 1, "b": 2}, {"a": 3, "b": 4}]').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=Overall Describe Table').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=Histogram of a').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=Histogram of b').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=Correlation Heatmap').first).to_be_visible(timeout=30000)
        await asyncio.sleep(5)
    
    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()
            
asyncio.run(run_test())
    