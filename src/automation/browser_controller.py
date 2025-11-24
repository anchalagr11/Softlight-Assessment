import os
from playwright.async_api import async_playwright

class BrowserController:
    def __init__(self, headless: bool = True):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.headless = os.getenv("PLAYWRIGHT_HEADLESS", "1") == "1" if headless else False

    async def start(self):
        self.playwright = await async_playwright().start()
        
        user_data_dir = os.path.abspath("browser_profile")
        if not os.path.exists(user_data_dir):
            os.makedirs(user_data_dir)

        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir,
            headless=self.headless,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
            viewport={"width": 1280, "height": 720}
        )

        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()

        await self.page.add_init_script("""
            if (!window.__mutationCount) {
                window.__mutationCount = 0;
                new MutationObserver(() => { window.__mutationCount++; })
                  .observe(document, { childList: true, subtree: true });
            }
        """)

        return self.page

    async def stop(self):
        try:
            if self.context:
                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
        except:
            pass
