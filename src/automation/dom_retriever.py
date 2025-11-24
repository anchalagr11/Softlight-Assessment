# src/automation/dom_retriever.py
import asyncio
from typing import List, Dict, Any
from playwright.async_api import Page, Locator

async def get_interactive_elements(page: Page) -> List[Dict[str, Any]]:
    """
    Retrieves all interactive elements from the page and assigns them a unique ID.
    Interactive elements are buttons, links, inputs, and elements with specific roles.
    """
    interactive_elements = []
    selectors = [
        "a", "button", "input:not([type='hidden'])",
        "textarea", "select", "[role='button']", "[role='link']",
        "[role='menuitem']", "[role='tab']", "[role='option']"
    ]

    combined_selector = ", ".join(selectors)
    elements = await page.locator(combined_selector).all()
    
    id_counter = 0
    for element in elements:
        try:
            # Skip non-visible elements
            if not await element.is_visible():
                continue

            accessible_name = await element.evaluate(
                "(el) => {"
                "  try {"
                "    const accessibility = window.getComputedAccessibleNode(el);"
                "    return accessibility.name;"
                "  } catch (e) {"
                "    return el.innerText || el.getAttribute('aria-label') || '';"
                "  }"
                "}"
            )
            
            text = (await element.text_content() or "").strip()
            
            # Use accessible name as the primary text, fallback to inner text
            display_text = (accessible_name or text or "").strip()

            # Assign a temporary, unique ID for the LLM to reference
            element_id = f"llm-element-{id_counter}"
            await element.evaluate(f"(el, id) => el.setAttribute('data-llm-id', id)", element_id)

            interactive_elements.append({
                "llm_id": element_id,
                "text": display_text,
                "tag": await element.evaluate("el => el.tagName.toLowerCase()"),
            })
            id_counter += 1
            
        except Exception:
            # Element might have become detached or is not an element anymore.
            # It's safe to ignore it.
            continue
            
    return interactive_elements
