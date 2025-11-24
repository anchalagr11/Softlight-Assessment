import re
from llm.llm_client import LLMClient
from .message_protocol import ActionStep, Plan
from utils.logger import get_logger

logger = get_logger(__name__)


def normalize_selector(sel):
    if not sel:
        return None

    if isinstance(sel, str):
        return sel

    if isinstance(sel, dict):
        if len(sel) == 1:
            k, v = list(sel.items())[0]
            if v is None:
                return None
            return f'{k}="{v}"'
        parts = [f'{k}="{v}"' for k, v in sel.items() if v is not None]
        return " ".join(parts)

    return None


def clean_selector(selector: str | None):
    if not selector:
        return selector

    if selector.startswith("text="):
        key, val = selector.split("=", 1)
        cleaned_val = val.strip().strip('"').strip("'")
        return f'text="{cleaned_val}"'

    match = re.match(r"input\[value=(.*)\]", selector)
    if match:
        value = match.group(1).strip().strip('"').strip("'")
        return f"input[value='{value}']"

    xpath_patterns = [
        (r"\[text\(\)\s*=\s*['\"]([^'\"]+)['\"]\]", r':has-text("\1")'),
        (r"\[text\s*=\s*['\"]([^'\"]+)['\"]\]", r':has-text("\1")'),
    ]
    
    for pattern, replacement in xpath_patterns:
        if re.search(pattern, selector):
            new_selector = re.sub(pattern, replacement, selector)
            logger.warning(f"Detected invalid XPath syntax in selector: {selector}")
            logger.warning(f"Converted to valid CSS: {new_selector}")
            return new_selector

    return selector



class OrchestratorAgent:
    def __init__(self):
        self.llm = LLMClient()

    def create_plan(self, task: str, observation: str = None, history: list = None) -> Plan:
        logger.info(f"Creating plan for task: {task}")
        if observation:
            logger.info(f"With observation: {observation[:100]}...")

            lower_task = task.lower()
            if any(k in lower_task for k in ["play", "watch", "listen", "music", "video"]):
                match = re.search(r"Current Page: .* \((https?://[^\)]+)\)", observation)
                if match:
                    current_url = match.group(1)
                    if "youtube.com/watch" in current_url:
                        logger.info("GUARDRAIL: Media playback detected on YouTube. Stopping task.")
                        return Plan(
                            steps=[],
                            raw_llm_output="GUARDRAIL: Media playback detected.",
                            model_used="system-guardrail",
                            planning_success=True,
                        )

        raw_steps = self.llm.plan(task, observation, history)
        logger.info(f"Raw LLM response: {raw_steps}")

        processed_steps = []
        for step in raw_steps:
            s = dict(step)

            if "selector" in s and s["selector"]:
                s["selector"] = normalize_selector(s["selector"])
                s["selector"] = clean_selector(s["selector"])

            processed_steps.append(s)

        steps = [ActionStep(**s) for s in processed_steps]
        
        logger.info(f"Generated plan with {len(steps)} steps:")
        for i, step in enumerate(steps):
            logger.info(f"  Step {i+1}: {step.action} -> {step.value or step.selector}")

        return Plan(
            steps=steps,
            raw_llm_output=str(raw_steps),
            model_used="gemini-2.5-flash",
            planning_success=True,
        )
