# src/main.py

import asyncio
import argparse
import json
import sys
from agents.orchestrator_agent import OrchestratorAgent
from agents.executor_agent import ExecutorAgent
from agents.message_protocol import AgentState
from graph.langgraph_builder import build_graph
from automation.action_engine import ActionEngine
from dotenv import load_dotenv

load_dotenv()

# Global agent instance to persist browser across graph steps
_executor_agent = None

def planner_node(state: AgentState):
    orch = OrchestratorAgent()
    
    # Extract history if available
    history = []
    if state.execution and state.execution.steps:
        history = state.execution.steps
        
    # Pass observation and history to planner
    plan = orch.create_plan(state.task, state.observation, history)

    # If plan is empty, we are done
    is_final = len(plan.steps) == 0

    return state.model_copy(update={
        "plan": plan,
        "final": is_final
    })


async def executor_node(state: AgentState):
    global _executor_agent
    if _executor_agent is None:
        _executor_agent = ExecutorAgent(headless=False)

    # Calculate start_step_index from existing history
    start_step_index = 0
    if state.execution and state.execution.steps:
        start_step_index = len(state.execution.steps)

    # Execute steps using the persistent agent
    # Pass existing_page to reuse the browser
    execution = await _executor_agent.execute(
        state.task,
        state.plan.steps,
        keep_open=state.keep_open,
        existing_page=_executor_agent.page,
        start_step_index=start_step_index
    )

    # Extract observation from execution result (we hacked it into dataset_path)
    observation = execution.dataset_path
    
    # Calculate new retry count
    new_retry_count = state.retry_count
    if execution.error:
        new_retry_count += 1
    else:
        # Reset retry count on success to allow long tasks
        new_retry_count = 0

    # Accumulate history
    current_steps = []
    if state.execution and state.execution.steps:
        current_steps.extend(state.execution.steps)
    current_steps.extend(execution.steps)
    
    # Update execution object with accumulated steps
    execution.steps = current_steps

    new_state = state.model_copy(update={
        "execution": execution,
        "retry_count": new_retry_count,
        "observation": observation
    })

    return new_state


async def run(task: str, keep_open: bool = False):
    # We need to modify the graph builder to support the loop
    # Ideally we'd change langgraph_builder.py, but we can also just loop here if the graph is simple.
    # However, the proper way is to update the graph definition.
    # For now, let's rely on the existing graph structure but update the conditional edge logic.
    
    # We need to update langgraph_builder.py to loop back to planner if not final.
    # But first let's set up the nodes here.
    
    graph = build_graph(planner_node, executor_node)

    initial = AgentState(task=task, keep_open=keep_open)
    final = await graph.ainvoke(initial, config={"recursion_limit": 100})

    print("=== Task Completed ===")

    # Support both Pydantic models (have .json()) and plain dicts
    if hasattr(final, "json") and callable(getattr(final, "json")):
        out = final.json(indent=2)
    else:
        try:
            out = json.dumps(final, indent=2)
        except TypeError:
            # some inner types may not be JSON-serializable; pretty-print fallback
            import pprint
            out = pprint.pformat(final, indent=2)

    print(out)

    if keep_open:
        print("\n[INFO] Browser is kept open. Press Enter to close and exit...")
        await asyncio.get_event_loop().run_in_executor(None, input)
        # Cleanup
        if _executor_agent:
            await _executor_agent.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", "-t", required=True)
    parser.add_argument("--keep-open", action="store_true", default=True, help="Keep browser open after task completion (default: True)")
    args = parser.parse_args()

    # Run the async pipeline and propagate exceptions to show tracebacks
    try:
        if sys.platform.startswith("win"):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        asyncio.run(run(args.task, args.keep_open))
    except RuntimeError as e:
        if str(e) == "Event loop is closed":
            # Known issue on Windows with ProactorEventLoop and subprocesses
            pass
        else:
            raise
    except Exception as e:
        # non-zero exit for CI / scripts
        print(f"Error: {e}")
        raise
