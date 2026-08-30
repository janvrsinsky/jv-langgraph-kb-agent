"""Offline tests: exercise the full graph loop with a scripted fake model,
so the agent wiring (conditional edges, ToolNode, checkpointer memory) is
verified without an API key.

Run: .venv/bin/pytest tests/ -q
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.messages import AIMessage, ToolMessage

from agent import build_graph, search_kb


class ScriptedModel:
    """Plays a fixed ReAct trace: first turn calls search_kb, second answers.
    Duck-types the two methods the graph actually uses."""

    def __init__(self) -> None:
        self.invocations = 0

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        self.invocations += 1
        if self.invocations % 2 == 1:
            return AIMessage(
                content="",
                tool_calls=[{
                    "name": "search_kb",
                    "args": {"query": "vacation days"},
                    "id": f"call_{self.invocations}",
                    "type": "tool_call",
                }],
            )
        return AIMessage(content="You get 27 vacation days (hr-policies.md).")


def test_search_kb_finds_the_right_doc():
    result = search_kb.invoke({"query": "how many vacation days per year"})
    assert "hr-policies.md" in result
    assert "27 vacation days" in result


def test_search_kb_abstains_instead_of_answering_anyway():
    """The tool must hand the model nothing when nothing matches.

    A hybrid retriever always has a nearest neighbour, so without the abstain
    path the model would receive four plausible passages for an unanswerable
    question. The floor itself is measured and tested in test_retrieval.py.
    """
    result = search_kb.invoke({"query": "xyzzy quux frobnicate"})
    assert "No matching passages" in result


def test_graph_runs_full_react_loop():
    app = build_graph(model=ScriptedModel())
    config = {"configurable": {"thread_id": "t1"}}
    out = app.invoke({"messages": [("user", "How many vacation days?")]}, config)

    types = [type(m).__name__ for m in out["messages"]]
    # human -> ai(tool_call) -> tool result -> final ai answer
    assert "ToolMessage" in types
    assert isinstance(out["messages"][-1], AIMessage)
    assert out["messages"][-1].content.startswith("You get 27")

    tool_msgs = [m for m in out["messages"] if isinstance(m, ToolMessage)]
    assert any("hr-policies.md" in m.content for m in tool_msgs)


def test_checkpointer_keeps_memory_per_thread():
    app = build_graph(model=ScriptedModel())
    cfg_a = {"configurable": {"thread_id": "a"}}
    cfg_b = {"configurable": {"thread_id": "b"}}

    first = app.invoke({"messages": [("user", "q1")]}, cfg_a)
    second = app.invoke({"messages": [("user", "q2")]}, cfg_a)
    other = app.invoke({"messages": [("user", "q1")]}, cfg_b)

    # thread a accumulated both turns, thread b only its own
    assert len(second["messages"]) > len(first["messages"])
    assert len(other["messages"]) == len(first["messages"])
