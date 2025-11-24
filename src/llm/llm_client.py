import os
import json
from dotenv import load_dotenv
from google.genai import Client
from google.genai import types
from .json_postprocessor import parse_json_from_llm, ParseError

load_dotenv()

def load_prompt(name: str) -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(script_dir, "prompt_templates", name)
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

SYSTEM_PROMPT = load_prompt("base_prompt.txt")

class LLMClient:
    def __init__(self):
        key = os.getenv("GEMINI_API_KEY")
        self.client = None
        self.model = "gemini-2.5-flash"
        config=types.GenerateContentConfig( temperature=0.1 )


        if not key:
            print("[LLM WARNING] GEMINI_API_KEY missing. Using fallback planner.")
            return

        self.client = Client(api_key=key)

    def plan(self, task: str, observation: str = None, history: list = None):


        if self.client is None:
            return self._fallback()

        prompt = SYSTEM_PROMPT + "\nUser task: " + task
        
        if history:
            prompt += "\n\nPREVIOUS ACTIONS (HISTORY):\n"
            for step in history:
                status = "Success" if step.success else f"Failed: {step.error}"
                prompt += f"- Step {step.step_index}: {step.action} {step.details} -> {status}\n"

        if observation:
            prompt +=f"\n\nCURRENT PAGE OBSERVATION:\n{observation}\n\nBased on this observation, what are the NEXT steps? If the task is complete, return an empty list []."

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
            )

            raw = response.text.strip()

            steps = parse_json_from_llm(raw)

            cleaned = []

            for s in steps:
                if "action" not in s:
                    continue

                if s["action"] == "navigate":
                    # Ensure value is present
                    if not s.get("value"):
                        continue
                    s["selector"] = None
                    cleaned.append(s)
                    continue

                sel = s.get("selector")
                if sel is None:
                    s["selector"] = None
                elif not isinstance(sel, str):
                    # If it's not None and not a string, that's an issue, but let's be lenient
                    s["selector"] = str(sel)
                else:
                    s["selector"] = sel.strip()
                
                cleaned.append(s)

            # We no longer force a navigate step here. 
            # The LLM should provide it based on the prompt.
            if not cleaned:
                 # Fallback if LLM returns nothing useful
                 return self._fallback()

            return cleaned

        except Exception as e:
            print(f"LLM Error: {e}")
            if 'raw' in locals():
                print(f"FAILED RAW RESPONSE: {raw}")
            return self._fallback()

    def _fallback(self):
        """
        Guaranteed safe fallback steps.
        """
        """
        Guaranteed safe fallback steps.
        """
        # Generic fallback - maybe just go to google or return empty?
        # For now, let's return an empty list or a safe default if we really can't plan.
        # But to keep it safe, let's just return an empty list and let the orchestrator handle it?
        # Or maybe a generic "I failed" step?
        # Let's stick to a safe default that doesn't crash but maybe doesn't do much.
        return []
