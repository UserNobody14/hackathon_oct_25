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
        # -> Click the 'Use sample.csv' button to load sample data for inspection.
        frame = context.pages[-1]
        # Click 'Use sample.csv' button to load sample data for inspection
        elem = frame.locator('xpath=html/body/div/div/div/div/div/div[2]/div/button[2]').nth(0)
        await page.wait_for_timeout(3000); await elem.click(timeout=5000)
        

        # -> Click the 'Analyze' button to trigger the inspection and code generation process.
        frame = context.pages[-1]
        # Click 'Analyze' button to trigger inspection and code generation
        elem = frame.locator('xpath=html/body/div/div/div/div/div/div[6]/button').nth(0)
        await page.wait_for_timeout(3000); await elem.click(timeout=5000)
        

        # --> Assertions to verify final state
        frame = context.pages[-1]
        await expect(frame.locator('text=AIDA — File').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=Selected: data.csv (0.0 KB)').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=Uploaded path: /Users/benjaminsobel/Code/hackathon_oct_25/backend/uploads/4de247ff4f494dbda33f1efa403c4717.csv').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=Use sample.csv').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=Format').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=csv').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=Engine').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=pandas').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=Viz Library').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=plotly').first).to_be_visible(timeout=30000)
        await expect(frame.locator('text=HTTP 500: {"returncode":1,"stdout":"","stderr":"Traceback (most recent call last):\n File \"/Users/benjaminsobel/Code/hackathon_oct_25/backend/scripts/analysis_1760828157.py\", line 39, in <module>\n fig.write_image(histogram_path)\n ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^\n File \"/Users/benjaminsobel/Code/hackathon_oct_25/backend/.venv/lib/python3.13/site-packages/plotly/basedatatypes.py\", line 3895, in write_image\n return pio.write_image(self, *args, **kwargs)\n ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^\n File \"/Users/benjaminsobel/Code/hackathon_oct_25/backend/.venv/lib/python3.13/site-packages/plotly/io/_kaleido.py\", line 528, in write_image\n img_data = to_image(\n fig,\n ...<5 lines>...\n engine=engine,\n )\n File \"/Users/benjaminsobel/Code/hackathon_oct_25/backend/.venv/lib/python3.13/site-packages/plotly/io/_kaleido.py\", line 345, in to_image\n raise ValueError(\n ...<6 lines>...\n )\nValueError: \nImage export using the \"kaleido\" engine requires the Kaleido package,\nwhich can be installed using pip:\n\n $ pip install --upgrade kaleido\n\n","artifacts":[{"type":"html","path":"/Users/benjaminsobel/Code/hackathon_oct_25/backend/artifacts/b2340f78ccff458c9ca2cb1e2769c50c/describe.html","title":"Describe"}]}').first).to_be_visible(timeout=30000)
        await asyncio.sleep(5)
    
    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()
            
asyncio.run(run_test())
    