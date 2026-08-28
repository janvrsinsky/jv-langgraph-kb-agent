#!/usr/bin/env python3
"""Live check: run the graph against a real Claude model and print the full trace.

The offline tests in tests/ prove the graph is *wired* correctly, using a
scripted fake model. They cannot tell you what the ReAct loop actually does
when a real model decides whether to search. This does, and it prints every
step so the behaviour is inspectable, not just asserted.

Run:  ANTHROPIC_API_KEY=... .venv/bin/python live_check.py
      MODEL=claude-haiku-4-5 .venv/bin/python live_check.py   # cheaper
"""

import os
import sys
import time

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent import MODEL, build_graph

# Anthropic API list price, USD per 1M tokens (input, output).
PRICES = {
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-haiku-4-5": (1.00, 5.00),
}

# Each scenario is (thread_id, question, what we are probing for).
SCENARIOS = [
    ("t-kb", "How many vacation days do I get?",
     "plain KB question - does it search before answering, and does it cite?"),
    ("t-kb", "And how much of that can I roll over?",
     "same thread - does checkpointer memory make the pronoun resolvable?"),
    ("t-gap", "What is our parental leave policy in the German office?",
     "not in the KB - does it say so, or invent policy?"),
    ("t-gen", "What is the capital of France?",
     "general knowledge - does it search anyway (over-search) or just answer?"),
    ("t-multi",
     "I start on Monday as a field engineer. What do I have to do on day one, "
     "and what torque can the AcmeArm I will be working with deliver?",
     "two facts in two documents - one search or two loop iterations?"),
    ("t-empty", "How do I claim reimbursement for a taxi ride to the airport?",
     "BM25 returns nothing - does it stop cleanly or keep flailing?"),
    ("t-loop", "What is the company policy on pets in the office?",
     "plausible but absent - does the model reformulate and search a second time?"),
    ("t-loop2",
     "Find me the exact warranty length for the AcmeArm, and if it is not in "
     "the knowledge base keep searching with different wording before you give up.",
     "forces several loop iterations - the ReAct cycle the offline test cannot reach"),
]


def describe(msg) -> str:
    if isinstance(msg, HumanMessage):
        return f"  HUMAN     {msg.content!r}"
    if isinstance(msg, ToolMessage):
        first = msg.content.splitlines()[0] if msg.content else ""
        srcs = sorted({ln.strip("[]") for ln in msg.content.splitlines()
                       if ln.startswith("[") and ln.endswith("]")})
        return (f"  TOOL      {len(msg.content)} chars, sources={srcs or ['-']}"
                f"  first line: {first[:60]!r}")
    if isinstance(msg, AIMessage):
        parts = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                parts.append(f"CALL {tc['name']}({tc['args']})")
        text = getattr(msg, "text", msg.content)
        if callable(text):  # langchain-core < 1.6 exposed .text() as a method
            text = text()
        if isinstance(text, str) and text.strip():
            parts.append(f"TEXT {text.strip()[:300]!r}")
        return "  AI        " + " | ".join(parts or ["<empty>"])
    return f"  {type(msg).__name__}  {msg}"


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set - this script needs a real key.")
        return 1

    print(f"model: {MODEL}\nlangchain-anthropic graph, hand-built StateGraph\n")
    app = build_graph()

    totals = {"in": 0, "out": 0, "calls": 0, "seconds": 0.0}
    seen = {}  # thread_id -> messages already printed

    for thread_id, question, probe in SCENARIOS:
        cfg = {"configurable": {"thread_id": thread_id}}
        print("=" * 78)
        print(f"[{thread_id}] {question}")
        print(f"probing: {probe}")
        t0 = time.time()
        try:
            out = app.invoke({"messages": [("user", question)]}, cfg)
        except Exception as exc:  # noqa: BLE001 - we want the class name in the report
            print(f"  !! {type(exc).__name__}: {exc}")
            continue
        elapsed = time.time() - t0

        start = seen.get(thread_id, 0)
        new = out["messages"][start:]
        seen[thread_id] = len(out["messages"])

        for m in new:
            print(describe(m))

        ai = [m for m in new if isinstance(m, AIMessage)]
        tool_msgs = [m for m in new if isinstance(m, ToolMessage)]
        tin = sum((m.usage_metadata or {}).get("input_tokens", 0) for m in ai)
        tout = sum((m.usage_metadata or {}).get("output_tokens", 0) for m in ai)
        totals["in"] += tin
        totals["out"] += tout
        totals["calls"] += len(tool_msgs)
        totals["seconds"] += elapsed
        print(f"  -- {len(ai)} model turns, {len(tool_msgs)} tool executions, "
              f"{tin} in / {tout} out tokens, {elapsed:.1f}s, "
              f"stop={ai[-1].response_metadata.get('stop_reason') if ai else '?'}")
        print()

    if MODEL in PRICES:
        pin, pout = PRICES[MODEL]
        price = f"~${totals['in'] / 1e6 * pin + totals['out'] / 1e6 * pout:.4f} at list price"
    else:
        price = f"cost unknown ({MODEL} is not in PRICES)"
    print("=" * 78)
    print(f"TOTAL  {totals['in']} in / {totals['out']} out tokens · "
          f"{totals['calls']} tool executions · {totals['seconds']:.1f}s · {price}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
