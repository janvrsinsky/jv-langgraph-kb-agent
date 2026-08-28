# What the graph actually does against a live model

The tests in `tests/` prove the graph is **wired** correctly: they drive the whole
loop with a scripted fake model, so they run offline, in CI, without a key. What
they cannot tell you is what the loop **does** when a real model is the one
deciding whether to search. `live_check.py` answers that: eight probes, full
message trace printed, token and cost accounting at the end.

Reproduce with:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
.venv/bin/python live_check.py                       # claude-opus-5
MODEL=claude-haiku-4-5 .venv/bin/python live_check.py # ~6x cheaper
```

## Run summary

Same eight probes, run end to end on both models:

| | Claude Opus 5 | Claude Haiku 4.5 |
|---|---|---|
| Tool executions | 16 | 16 |
| Tokens | 14 666 in / 3 642 out | 17 304 in / 2 077 out |
| Wall clock | 64.7 s | 30.0 s |
| Cost at list price | ~$0.164 | ~$0.028 |

Structurally the two behave the same - both search before answering, both answer
the same-thread follow-up from memory without searching, and both drive the loop
around more than once on the probe that pushes for it. Opus writes roughly twice
as many output tokens per answer; Haiku is ~6x cheaper and ~2x faster.

Every factual claim in every answer was checked back against `kb/`. **Nothing was
invented**: the 27 vacation days, the 5-day carryover, the 18/6-week parental
leave split, the 9:30 Prague start and the AcmeArm's 310 Nm are all literally in
the source documents.

## Six things the scripted tests could not have shown

**1 · The real model calls the tool twice in parallel, every time.** The scripted
fake emits one tool call per turn. Claude emits two or four in a single assistant
message, and `ToolNode` executes them all and returns one `ToolMessage` each. The
graph handles it, and nothing in the offline suite exercises that shape.

**2 · A tool-calling turn is not an empty turn.** The fake returns
`AIMessage(content="", tool_calls=[...])`. The real model returns *both*: a short
preamble (`"I'll look that up in the knowledge base."`) **and** the tool calls, in
the same message. Any downstream code that assumes "if there are tool calls there
is no text" is wrong against a live model, and the tests would never catch it.

**3 · The ReAct loop really does loop, but only under pressure.** Five of the eight
probes went round exactly once (agent → tools → agent → END) and two never called the
tool at all. Only the probe that explicitly asks the agent to keep trying different
wording drove the conditional edge around three times: **4 model turns, 6 tool
executions**, the model narrating its own retries (`"Neither of those hit it. Let me
try different phrasings."`) before concluding the answer is genuinely absent. That is
the cycle the offline test can only assert without ever observing.

**4 · The model silently compensates for weak retrieval.** `search_kb` is plain BM25
over markdown paragraphs. Handed the user's literal words, *"my computer got stolen
last night what do i do"*, BM25 returns **nothing**. The model never passes the
literal words: it rewrites the question into keywords (`"stolen computer theft
security incident reporting"`) and gets a clean hit. The retrieval quality you
measure in isolation is therefore not the retrieval quality the user experiences;
part of it is the model doing free query rewriting.

**5 · The memory rule and the grounding rule collide.** The system prompt says
*"For any company-specific question, call search_kb BEFORE answering."* On the
follow-up turn in the same thread (*"And how much of that can I roll over?"*) the
model answered with **zero tool calls**, from the `ToolMessage` still sitting in the
checkpointed state. The answer was correct and cited. But strictly read, the rule
was broken, and it was the checkpointer that made breaking it possible. In a
grounded assistant with an auditor over it, that is the interesting failure mode,
and it only appears once memory and a live model are in the same run.

**6 · Citation format drifts and nothing enforces it.** The same model cited
`(hr-policies.md)` in one answer and `[onboarding.md]` in the next. If citation
shape matters downstream, it has to be constrained by the tool's output format or
by structured outputs; a system-prompt instruction does not hold it.

## What still is not proven

- **Not production.** Demo scale, a fictional knowledge base (Acme Robotics), four
  markdown files. Nobody has used it but me.
- **No eval harness.** The live check prints a trace for a human to read; it does
  not score answers, and there is no regression gate on answer quality.
- **`MemorySaver` is in-process.** Memory dies with the process. Swapping in
  `SqliteSaver` to persist it has not been done.
- **No human-in-the-loop gate.** `interrupt_before=["tools"]` is not wired.

## One thing the run changed in the code

`max_tokens` was 1024. The longest single answer in the first run came within 27
tokens of that, and hitting the cap truncates mid-sentence with
`stop_reason: "max_tokens"`, which in a printed trace reads exactly like a
finished answer. It is now 4096, and the re-run above produced a **1090-token**
turn: the old ceiling would have cut it.
