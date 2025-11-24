# ui_state_detector.py
from playwright.async_api import Page, Locator
import asyncio
import time

async def detect_state_change(page: Page, timeout: float = 2.0, poll: float = 0.2) -> bool:
    """
    Use the injected mutation counter to detect DOM changes after an action.
    Returns True if mutation count increased within timeout.
    """
    try:
        before = await page.evaluate("window.__mutationCount || 0")
        end = time.time() + timeout
        while time.time() < end:
            await asyncio.sleep(poll)
            after = await page.evaluate("window.__mutationCount || 0")
            if after > before:
                return True
        return False
    except Exception:
        return False

async def find_active_modal(page: Page) -> Locator | None:
    """
    Finds if there is an active modal dialog on the page.
    A common heuristic for modals is the `role="dialog"` attribute.
    """
    try:
        # Broader modal detection strategy
        selectors = [
            '[role="dialog"]',
            '[class*="modal"]',
            '[class*="dialog"]',
            '[aria-modal="true"]',
            'div[style*="z-index"][style*="fixed"]' # Heuristic for overlays
        ]
        
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if await locator.is_visible():
                    return locator
            except:
                continue
                
        return None
    except Exception:
        # No modal found or it's not visible
        return None