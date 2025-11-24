# langgraph_builder.py

from langgraph.graph import StateGraph, END
from agents.message_protocol import AgentState

def build_graph(planner_node, executor_node):
    graph = StateGraph(AgentState)
# langgraph_builder.py

from langgraph.graph import StateGraph, END
from agents.message_protocol import AgentState

def build_graph(planner_node, executor_node):
    graph = StateGraph(AgentState)
# langgraph_builder.py

from langgraph.graph import StateGraph, END
from agents.message_protocol import AgentState

def build_graph(planner_node, executor_node):
    graph = StateGraph(AgentState)
# langgraph_builder.py

from langgraph.graph import StateGraph, END
from agents.message_protocol import AgentState

def build_graph(planner_node, executor_node):
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)

    graph.set_entry_point("planner")

    def should_continue(state: AgentState):
        # If final flag is set, we are done
        if state.final:
            return False
        
        # If too many retries on the SAME step/error, maybe abort?
        # But for now, let's trust the planner to eventually give up or succeed.
        # We check retry_count to prevent infinite loops on errors.
        if state.execution and state.execution.error and state.retry_count >= 3:
             return False

        # Otherwise, go back to planner for next steps
        return True

    graph.add_edge("planner", "executor")

    graph.add_conditional_edges(
        "executor",
        should_continue,
        {
            True: "planner",
            False: END
        }
    )

    return graph.compile()