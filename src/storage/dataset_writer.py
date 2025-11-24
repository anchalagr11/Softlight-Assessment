import os
import json
from datetime import datetime
from agents.message_protocol import StepExecutionResult

def _slug(text: str):
    return "".join(c if c.isalnum() else "_" for c in text).lower()

class DatasetWriter:
    def __init__(self, base_dir: str = "dataset"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def create_run_dir(self, task: str):
        existing = [d for d in os.listdir(self.base_dir) if d.isdigit() and os.path.isdir(os.path.join(self.base_dir, d))]
        if existing:
            next_id = max(int(d) for d in existing) + 1
        else:
            next_id = 1
        
        path = os.path.join(self.base_dir, f"{next_id:04d}")
        os.makedirs(path, exist_ok=True)
        return path

    def write_step(self, task: str, step: StepExecutionResult, run_dir: str):
        steps_file = os.path.join(run_dir, "steps.json")

        if os.path.exists(steps_file):
            steps = json.load(open(steps_file))
        else:
            steps = []

        steps.append(step.dict())

        json.dump(steps, open(steps_file, "w"), indent=2)

        manifest = {
            "task": task,
            "updated_at": datetime.utcnow().isoformat(),
            "num_steps": len(steps)
        }
        json.dump(
            manifest,
            open(os.path.join(run_dir, "manifest.json"), "w"),
            indent=2
        )