#!/usr/bin/env python3
"""Brain: a ReAct-style agent over a company knowledge base, built in LangGraph.

The graph is hand-built (StateGraph, not the prebuilt create_agent) on purpose,
that's the LangGraph literacy this project is for:

    START -> agent -(tool_calls?)-> tools -> agent -> ... -> END

- `agent` node: Claude with the search tool bound; decides to search or answer
- `tools` node: executes the tool calls, results come back as ToolMessages
- conditional edge (tools_condition): loops until the model stops calling tools
- MemorySaver checkpointer + thread_id: multi-turn conversation memory

Run:  ANTHROPIC_API_KEY=... .venv/bin/python agent.py
"""

import os
import re
from pathlib import Path

from langchain_core.messages import SystemMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from rank_bm25 import BM25Okapi

KB_DIR = Path(__file__).resolve().parent / "kb"
MODEL = os.environ.get("MODEL", "claude-opus-5")

SYSTEM_PROMPT = """You are Brain, the internal assistant of Acme Robotics.
Answer employee questions using the company knowledge base.

Rules:
- For any company-specific question, call search_kb BEFORE answering. Do not
  answer company questions from general knowledge.
- Cite the source document name for every fact you state.
- If the knowledge base does not contain the answer, say so plainly and suggest
  who to ask instead. Never invent policy.
"""


# ---------- retrieval tool (BM25 over markdown paragraphs) ----------
# Lexical BM25 keeps this repo dependency-light and key-free for retrieval.
# In production this would be a vector store with hybrid dense+lexical search
# and rank fusion; here the point is the graph, not the retriever.

def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _load_kb() -> list[dict]:
    passages = []
    for doc in sorted(KB_DIR.glob("*.md")):
        for para in re.split(r"\n\s*\n", doc.read_text(encoding="utf-8")):
            para = para.strip()
            if len(para) > 40:
                passages.append({"source": doc.name, "text": para})
    return passages


_PASSAGES = _load_kb()
_BM25 = BM25Okapi([_tokenize(p["text"]) for p in _PASSAGES])


@tool
def search_kb(query: str) -> str:
    """Search the Acme Robotics internal knowledge base (HR policies, IT,
    products, onboarding). Returns the most relevant passages with their
    source document names."""
    scores = _BM25.get_scores(_tokenize(query))
    ranked = sorted(range(len(scores)), key=lambda i: -scores[i])[:4]
    hits = [i for i in ranked if scores[i] > 0]
    if not hits:
        return "No matching passages in the knowledge base."
    return "\n\n".join(f"[{_PASSAGES[i]['source']}]\n{_PASSAGES[i]['text']}" for i in hits)


# ---------- the graph ----------

def build_graph(model=None):
    """Compile the agent graph. `model` is injectable so tests can run the
    full loop with a scripted fake model, no API key needed."""
    if model is None:
        from langchain_anthropic import ChatAnthropic
        # 1024 was tight: the longest answer in the live check came within
        # 27 tokens of it, and hitting the cap truncates mid-sentence with
        # stop_reason="max_tokens" - which reads like a finished answer.
        model = ChatAnthropic(model=MODEL, max_tokens=4096)
    model_with_tools = model.bind_tools([search_kb])

    def agent_node(state: MessagesState) -> dict:
        messages = [SystemMessage(SYSTEM_PROMPT), *state["messages"]]
        return {"messages": [model_with_tools.invoke(messages)]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode([search_kb]))
    graph.add_edge(START, "agent")
    # routes to "tools" when the last AI message contains tool calls, else END
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    return graph.compile(checkpointer=MemorySaver())


# ---------- CLI chat ----------

def main() -> None:
    app = build_graph()
    config = {"configurable": {"thread_id": "demo"}}  # memory lives per thread_id
    print("Brain (Acme Robotics KB agent). Ctrl-C or 'exit' to quit.")
    print("Try: How many vacation days do I get? / What torque does the AcmeArm have?\n")
    while True:
        try:
            question = input("you>  ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question or question.lower() in {"exit", "quit"}:
            break
        result = app.invoke({"messages": [("user", question)]}, config)
        print(f"brain> {result['messages'][-1].content}\n")


if __name__ == "__main__":
    main()
