from langgraph.graph import END, START, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from tools import retriever_tool
from nodes import (
    generate_query_or_respond,
    grade_documents,
    rewrite_question,
    generate_answer,
)

workflow = StateGraph(MessagesState)

# Define the nodes we will cycle between
workflow.add_node(generate_query_or_respond)
workflow.add_node("retrieve", ToolNode([retriever_tool]))
workflow.add_node(rewrite_question)
workflow.add_node(generate_answer)

# Start node transition
workflow.add_edge(START, "generate_query_or_respond")

# Route based on whether the model requested tool calls.
def route_on_tool_calls(state: MessagesState):
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"
    return END

# Decide whether to retrieve or respond directly
workflow.add_conditional_edges(
    "generate_query_or_respond",
    route_on_tool_calls,
    {
        "tools": "retrieve",
        END: END,
    },
)

# Edges taken after the `retrieve` node is called (grading step)
workflow.add_conditional_edges(
    "retrieve",
    grade_documents,
    {
        "generate_answer": "generate_answer",
        "rewrite_question": "rewrite_question",
        "max_retries": "generate_answer",
    }
)

# Transitions from final nodes
workflow.add_edge("generate_answer", END)
workflow.add_edge("rewrite_question", "generate_query_or_respond")

# Compile the graph
graph = workflow.compile()
