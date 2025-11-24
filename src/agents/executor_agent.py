import asyncio
from typing import List

from automation.browser_controller import BrowserController
from automation.action_engine import ActionEngine
from automation.screenshot_manager import ScreenshotManager
from automation.dom_tree import get_page_accessibility_tree
from storage.dataset_writer import DatasetWriter
from .message_protocol import (
    ActionStep,
    StepExecutionResult,
    ExecutionResult,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class ExecutorAgent:
    def __init__(self, headless: bool = True):
        self.browser = BrowserController(headless=headless)
        self.page = None
        self.action_engine = None
        self.dataset_writer = DatasetWriter()
        self.screenshot_mgr = None
        self.task_dir = None

    async def start(self, task: str):
        logger.info("Starting browser...")
        self.page = await self.browser.start()
        self.task_dir = self.dataset_writer.create_run_dir(task)

        self.screenshot_mgr = ScreenshotManager(self.task_dir)
        self.action_engine = ActionEngine(self.page)

        logger.info("Browser started.")

    async def stop(self):
        logger.info("Stopping browser...")
        await self.browser.stop()
        logger.info("Browser stopped.")

    async def execute(self, task: str, steps: List[ActionStep], keep_open: bool = False, existing_page=None, start_step_index: int = 0):
        if existing_page:
            self.page = existing_page
            self.action_engine = ActionEngine(self.page)
            
            if not self.task_dir:
                 self.task_dir = self.dataset_writer.create_run_dir(task)
            
            if not self.screenshot_mgr:
                 self.screenshot_mgr = ScreenshotManager(self.task_dir)
        else:
            await self.start(task)

        result = ExecutionResult(task=task)
        step_index = start_step_index

        for step in steps:
            step_index += 1
            logger.info(f"Executing step {step_index}: {step.dict()}")

            step_payload = step.dict()

            success, error_msg = await self.action_engine.run_step(step_payload)

            shot_meta = None
            screenshot_filename = f"{step_index:04d}.png"
            
            if not success:
                try:
                    shot_meta = await self.screenshot_mgr.capture(
                        self.page,
                        step.name or f"step_{step_index}",
                        full_page=True,
                        filename=screenshot_filename
                    )
                except Exception as e:
                    logger.warning(f"Screenshot failed for step {step_index}: {e}")
                    shot_meta = None

            step_record = StepExecutionResult(
                step_index=step_index,
                action=step.action,
                success=success,
                state_changed=success,
                screenshot_path=shot_meta["path"] if shot_meta else None,
                page_url=shot_meta["page_url"] if shot_meta else self.page.url,
                error=error_msg,
                details={"error": error_msg} if error_msg else {},
            )

            logger.info(f"Step {step_index} result: {step_record.dict()}")

            self.dataset_writer.write_step(task, step_record, self.task_dir)
            result.steps.append(step_record)

            if not success:
                logger.error(f"Step {step_index} failed. Error: {error_msg}")
                result.mark_failure(f"Step {step_index} failed.")
                
                try:
                    title = await self.page.title()
                    url = self.page.url
                    dom_tree = await get_page_accessibility_tree(self.page)
                    
                    observation = f"Current Page: {title} ({url})\nInteractive Elements:\n{dom_tree}"
                    
                    with open("d:/Softlight_Assesment/Softlight_Assesment/latest_observation.txt", "w", encoding="utf-8") as f:
                        f.write(observation)
                        
                    result.dataset_path = observation 
                except Exception as e:
                    logger.error(f"Failed to capture observation: {e}")

                if not keep_open and not existing_page:
                    await self.stop()
                return result

            logger.info(f"Step {step_index} completed successfully.")
            
            await asyncio.sleep(1.0)

            if success and step.action in ("navigate", "click", "type", "screenshot"):
                 try:
                    shot_meta = await self.screenshot_mgr.capture(
                        self.page,
                        step.name or f"step_{step_index}",
                        full_page=True,
                        filename=screenshot_filename
                    )
                    step_record.screenshot_path = shot_meta["path"]
                    step_record.page_url = shot_meta["page_url"]
                    self.dataset_writer.write_step(task, step_record, self.task_dir)
                 except Exception as e:
                    logger.warning(f"Post-stabilization screenshot failed for step {step_index}: {e}")
        
        try:
            title = await self.page.title()
            url = self.page.url
            
            focused_info = await self.page.evaluate("""() => {
                const active = document.activeElement;
                if (!active || active === document.body) return "None";
                return `Tag: ${active.tagName}, Placeholder: ${active.placeholder || 'None'}, Value: ${active.value || 'None'}, Text: ${active.innerText.slice(0, 50)}`;
            }""")

            from automation.ui_state_detector import find_active_modal
            modal_locator = await find_active_modal(self.page)
            modal_info = "None"
            if modal_locator:
                try:
                    modal_text = await modal_locator.inner_text()
                    modal_info = f"Visible (Text: {modal_text[:100]}...)"
                except Exception:
                    modal_info = "Visible (Text unavailable)"

            dom_tree = await get_page_accessibility_tree(self.page)
            
            observation = f"Current Page: {title} ({url})\nActive Modal: {modal_info}\nFocused Element: {focused_info}\nInteractive Elements:\n{dom_tree}"
            
            if not success:
                observation = f"!!! LAST ACTION FAILED: {error_msg} !!!\n\n{observation}"
                
            result.dataset_path = observation
        except Exception:
            pass

        if not keep_open and not existing_page:
            await self.stop()
        return result
