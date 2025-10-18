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
        # -> Click 'Use sample.csv' button to load sample data for sampling test
        frame = context.pages[-1]
        # Click 'Use sample.csv' button to load sample data
        elem = frame.locator('xpath=html/body/div/div/div/div/div/div[2]/div/button[2]').nth(0)
        await page.wait_for_timeout(3000); await elem.click(timeout=5000)
        

        # -> Click 'Analyze' button to invoke /api/inspect endpoint and capture sample rows from the response
        frame = context.pages[-1]
        # Click 'Analyze' button to invoke /api/inspect endpoint with current sampling parameters
        elem = frame.locator('xpath=html/body/div/div/div/div/div/div[6]/button').nth(0)
        await page.wait_for_timeout(3000); await elem.click(timeout=5000)
        

        # -> Click 'Analyze' button again to re-invoke /api/inspect endpoint with the same parameters and capture sample rows for comparison
        frame = context.pages[-1]
        # Click 'Analyze' button again to re-invoke /api/inspect endpoint with identical parameters
        elem = frame.locator('xpath=html/body/div/div/div/div[2]/div/div[4]/div/div/a').nth(0)
        await page.wait_for_timeout(3000); await elem.click(timeout=5000)
        

        # --> Assertions to verify final state
        frame = context.pages[-1]
        await expect(frame.locator('text=a\tb').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=count\t2.000000\t2.000000').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=mean\t2.000000\t3.000000').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=std\t1.414214\t1.414214').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=min\t1.000000\t2.000000').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=25%\t1.500000\t2.500000').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=50%\t2.000000\t3.000000').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=75%\t2.500000\t3.500000').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=max\t3.000000\t4.000000').first).to_be_visible(timeout=30000)
        await asyncio.sleep(5)
    
    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()
            
asyncio.run(run_test())
    