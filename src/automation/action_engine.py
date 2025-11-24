import logging
import asyncio
from automation.ui_state_detector import find_active_modal

logger = logging.getLogger(__name__)

class ActionEngine:
    def __init__(self, page):
        self.page = page
        self.scope = page
        self.active_modal = None



    async def run_step(self, step: dict):
        action = step.get("action")
        selector = step.get("selector")
        value = step.get("value")

        logger.info(
            f"Running action: {action} with selector: {selector} and value: {value}"
        )

        try:
            if action == "navigate":
                return await self._do_navigate(step)

            if action == "click":
                return await self._do_click(selector)

            if action == "right_click":
                return await self._do_right_click(selector)

            if action == "type":
                return await self._do_type(selector, value)

            if action == "press":
                return await self._do_press(selector, value)

            if action == "wait_for":
                return await self._do_wait_for(selector)

            if action == "wait_for_user":
                return await self._do_wait_for_user(value)

            if action == "screenshot":
                return True, None

            return False, f"Unknown action: {action}"

        except Exception as e:
            logger.error(f"Error during action '{action}': {e}")
            return False, str(e)


    async def _do_navigate(self, step: dict):
        url = step.get("value")
        if not url:
            return False, "Missing URL for navigate"

        logger.info(f"Navigating to {url}")
        try:
            await self.page.goto(url, wait_until="load")
            self.active_modal = None
            return True, None
        except Exception as e:
            return False, str(e)


    async def _extract_text(self, selector: str | None):
        if not selector:
            return None
        if selector.startswith("text="):
            return selector.split("=", 1)[1].strip().strip('"').strip("'")
        return None


    async def _do_click(self, selector: str | None):
        if not selector:
            return False, "Missing selector"


        if "[text=" in selector:
            import re
            selector = re.sub(r"\[text=(['\"])(.*?)\1\]", r":has-text(\1\2\1)", selector)
            logger.info(f"Sanitized selector to: {selector}")

        logger.info(f"Clicking: {selector}")

        text = await self._extract_text(selector)
        if text:
            variations = {
                text,
                text.replace("...", "…"),
                text.replace("…", "..."),
                text.strip(),
                text.lower(),
                text.title(),
            }

            roles = ["button", "link", "menuitem", "tab", "checkbox", "radio"]

            for name in variations:
                for role in roles:
                    try:
                        await self.page.get_by_role(role, name=name).first.click(
                            timeout=2000
                        )
                        self.active_modal = await find_active_modal(self.page)
                        logger.info(f"Clicked via role={role}, name='{name}'")
                        return True, None
                    except Exception:
                        pass

                try:
                    await self.page.get_by_text(name, exact=True).first.click(
                        timeout=2000
                    )
                    self.active_modal = await find_active_modal(self.page)
                    logger.info(f"Clicked via exact text '{name}'")
                    return True, None
                except Exception:
                    pass

                try:
                    await self.page.get_by_text(name).first.click(timeout=2000)
                    self.active_modal = await find_active_modal(self.page)
                    logger.info(f"Clicked via fuzzy text '{name}'")
                    return True, None
                except Exception:
                    pass

                try:
                    await self.page.locator("button, a, div, span").filter(
                        has_text=name
                    ).first.click(timeout=2000)
                    self.active_modal = await find_active_modal(self.page)
                    logger.info(f"Clicked via generic element has_text '{name}'")
                    return True, None
                except Exception:
                    pass

        contexts = []

        if self.active_modal:
            contexts.append(self.active_modal)

        contexts.extend(
            [
                self.page,
                self.page.locator("body"),
                self.page.locator("div[role='menu']"),
                self.page.locator("div[data-radix-context-menu-content]"),
                self.page.locator("div[class*='ContextMenuContent']"),
                self.page.locator("div[data-portal-root]"),
                self.page.locator("div[data-overlay-container']"),
            ]
        )

        for attempt in range(1, 4):
            try:
                for ctx in contexts:
                    try:
                        await ctx.locator(selector).first.click(timeout=2000)
                        self.active_modal = await find_active_modal(self.page)
                        logger.info(
                            f"Clicked via raw selector '{selector}' on attempt {attempt}"
                        )
                        return True, None
                    except Exception:
                        continue

                raise Exception("Not found")

            except Exception:
                if attempt == 3:
                    for ctx in contexts:
                        try:
                            await ctx.locator(selector).first.click(
                                force=True, timeout=1500
                            )
                            self.active_modal = await find_active_modal(self.page)
                            logger.info(
                                f"Force-clicked via raw selector '{selector}' "
                                f"on final attempt"
                            )
                            return True, None
                        except Exception:
                            continue

                    return False, f"Could not click {selector}"

                await asyncio.sleep(0.25)

    async def _do_right_click(self, selector: str | None):
        if not selector:
            return False, "Missing selector"

        logger.info(f"Right-clicking: {selector}")

        contexts = [self.page, self.page.locator("body")]
        if self.active_modal:
            contexts.insert(0, self.active_modal)

        for ctx in contexts:
            try:
                await ctx.locator(selector).first.click(button="right", timeout=4000)
                await asyncio.sleep(0.3)
                self.active_modal = await find_active_modal(self.page)
                logger.info(f"Right-clicked on selector '{selector}'")
                return True, None
            except Exception:
                continue

        return False, f"Could not right-click {selector}"

    async def _do_type(self, selector: str | None, value: str | None):
        logger.info(f"Typing: {value} into {selector}")

        if value is None:
            return False, "Missing value for type"

        contexts = [self.page]
        if self.active_modal:
            contexts.insert(0, self.active_modal)

        if selector == "focused":
            logger.info(f"Typing into FOCUSED element: {value}")
            try:
                await self.page.keyboard.type(value)
                return True, None
            except Exception as e:
                return False, f"Failed to type into focused element: {e}"

        for ctx in contexts:
            try:
                if selector and selector.startswith("label="):
                    label = selector.split("=", 1)[1].strip().strip('"').strip("'")
                    logger.info(f"Trying get_by_label('{label}')")
                    await ctx.get_by_label(label).fill(value, timeout=6000)
                    return True, None

                if selector:
                    logger.info(f"Trying direct locator('{selector}')")
                    is_complex = "div" in selector or "role='textbox'" in selector or "contenteditable" in selector
                    
                    if is_complex:
                        try:
                            await ctx.locator(selector).fill(value, timeout=3000)
                            return True, None
                        except Exception:
                            logger.info("Fill failed on complex element, trying click-and-type fallback")
                            return await self._click_and_type(ctx, selector, value)
                    else:
                        await ctx.locator(selector).fill(value, timeout=6000)
                        return True, None
            except Exception:
                continue

        primary_ctx = contexts[0]

        try:
            logger.info("Fallback: trying fuzzy placeholders (Name, Project, Title)")
            for fuzzy in ["Name", "Project", "Title", "Subject"]:
                try:
                    await primary_ctx.locator(f"input[placeholder*='{fuzzy}' i]").first.fill(
                        value, timeout=2000
                    )
                    return True, None
                except Exception:
                    continue
        except Exception:
            pass
            
        try:
            logger.info("Fallback: trying div[role='textbox']")
            if selector and "aria-label=" in selector:
                 label_text = selector.split("aria-label=", 1)[1].strip().strip('"').strip("'").split("]")[0].strip("'").strip('"')
                 await primary_ctx.locator(f"div[role='textbox'][aria-label='{label_text}']").first.click()
                 await self.page.keyboard.type(value)
                 return True, None
        except Exception:
            pass

        try:
            logger.info("Fallback: trying first input[value]")
            await primary_ctx.locator("input[value]").first.fill(value, timeout=6000)
            return True, None
        except Exception:
            pass

        try:
            logger.info("Fallback: trying first visible input or textarea")
            await primary_ctx.locator("input, textarea").first.fill(value, timeout=6000)
            return True, None
        except Exception:
            pass

        return False, f"Could not type into {selector}"

    async def _click_and_type(self, ctx, selector, value):
        try:
            await ctx.locator(selector).first.click()
            await self.page.keyboard.press("Control+A")
            await self.page.keyboard.press("Backspace")
            await self.page.keyboard.type(value)
            return True, None
        except Exception as e:
            return False, f"Click-and-type failed: {e}"

    async def _do_press(self, selector: str | None, value: str | None):
        if not value:
            return False, "Missing key to press (value)"

        logger.info(f"Pressing key: {value} on {selector or 'page'}")

        try:
            if selector:
                await self.page.locator(selector).first.press(value)
            else:
                await self.page.keyboard.press(value)
            return True, None
        except Exception as e:
            return False, str(e)

    async def _do_wait_for_user(self, message: str | None):
        msg = message or "Please perform the required manual action (e.g., Login)."
        print(f"\n[ACTION REQUIRED] {msg}")
        print("Press Enter in this terminal once you are done to continue...")
        
        await asyncio.get_event_loop().run_in_executor(None, input)
        
        logger.info("User confirmed manual action completion.")
        return True, None

    async def _do_wait_for(self, selector: str | None):
        if not selector:
            return False, "Missing selector for wait_for"

        try:
            if selector == "url" or selector.startswith("url="):
                target_url = selector.split("=", 1)[1] if "=" in selector else None
                if target_url:
                    await self.page.wait_for_url(lambda url: target_url in url, timeout=15000)
                    logger.info(f"Waited for URL to contain '{target_url}'")
                else:
                    await self.page.wait_for_load_state("load", timeout=15000)
                    logger.info("Waited for page load")
                return True, None

            await self.page.locator(selector).first.wait_for(timeout=10000)
            return True, None
        except Exception as e:
            return False, str(e)
