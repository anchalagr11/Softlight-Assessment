import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from playwright.async_api import Page


def _safe_name(name: str) -> str:
    safe = "".join(c if c.isalnum() or c in ".-_" else "_" for c in name)
    return safe[:80]


class ScreenshotManager:
    def __init__(self, base_dataset_dir: str):
        self.base_dataset_dir = base_dataset_dir
        os.makedirs(base_dataset_dir, exist_ok=True)

    async def capture(
        self,
        page: Page,
        step_name: str,
        full_page: bool = True,
        custom_subdir: Optional[str] = None,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        safe_step = _safe_name(step_name or "step")
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        uid = uuid.uuid4().hex[:8]

        folder = self.base_dataset_dir
        if custom_subdir:
            folder = os.path.join(folder, _safe_name(custom_subdir))
            os.makedirs(folder, exist_ok=True)

        if not filename:
            filename = f"{timestamp}_{safe_step}_{uid}.png"
            
        filepath = os.path.join(folder, filename)

        try:
            await page.screenshot(path=filepath, full_page=full_page)
        except Exception:
            try:
                await page.screenshot(path=filepath, full_page=False)
            except Exception as e:
                raise RuntimeError(f"Screenshot failed: {e}") from e

        page_url = None
        viewport = None
        try:
            page_url = page.url if hasattr(page, "url") else None
        except Exception:
            page_url = None

        try:
            clip = await page.evaluate(
                """() => {
                    return {
                      width: window.innerWidth,
                      height: window.innerHeight,
                      scrollX: window.scrollX,
                      scrollY: window.scrollY
                    };
                }"""
            )
            viewport = clip
        except Exception:
            viewport = None

        metadata = {
            "path": filepath,
            "filename": filename,
            "step_name": step_name,
            "timestamp": timestamp,
            "page_url": page_url,
            "viewport": viewport,
        }

        return metadata
