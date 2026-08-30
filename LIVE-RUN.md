# What the graph actually does against a live model

The tests in `tests/` prove the graph is **wired** correctly and that retrieval
does what `README.md` claims: they drive the whole loop with a scripted fake
model, so they run offline, in CI, without a key. What they cannot tell you is
what the loop **does** when a real model is the one deciding whether to search,
and what it types into the search box when it does. `live_check.py` answers
that: nine probes, full message trace printed, token and cost accounting at the
end.

Reproduce with:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
.venv/bin/python live_check.py                       # claude-opus-5
MODEL=claude-haiku-4-5 .venv/bin/python live_check.py # ~7x cheaper
```

## Run summary

Same nine probes, run end to end on both models on 30 August 2026, against the
13-document knowledge base.

| | Claude Opus 5 | Claude Haiku 4.5 |
|---|---|---|
| Tool executions | 19 | 16 |
| Tokens | 24 011 in / 4 379 out | 21 159 in / 2 198 out |
| Wall clock | 73.5 s | 30.3 s |
| Cost at list price | ~$0.2295 | ~$0.0321 |

Both models answered every answerable probe correctly and refused every
unanswerable one. Opus costs about seven times as much and takes about two and a
half times as long for the same nine questions. On this knowledge base that
difference bought no additional correct answers, and it did buy visibly more
careful hedging about what the documents do not say.

## Seven things the scripted tests could not have shown

**1 · The model never sends the user's words.** Not once, on either model, in
any of the nine probes. Asked *"what do I do when my phone is stolen?"*, Opus
searched for `"lost or stolen phone device policy"`. Asked about vacation, it
searched `"vacation days policy annual leave entitlement"`. The agent rewrites
every question into the vocabulary it expects a corporate knowledge base to use,
before the retriever ever sees it. Any retrieval quality you measure on raw user
phrasing is therefore measuring an input this agent rarely produces.

**2 · Which matters, because the retriever is fragile about phrasing.** The
offline dense branch is a hashed character n-gram stand-in, so it scores surface
overlap. *"what do I do when my phone is stolen"* reaches the security policy;
*"stolen phone what to do"*, the same question reordered, lands on data
protection, engineering and FleetMind instead. Haiku hit exactly that: its first
query was the more literal `"stolen phone what to do"`, it got the wrong three
documents, said so in plain words, rewrote the query, and then answered
correctly. The model's rewriting habit is doing part of the retrieval work, and
finding 1 is why that keeps working.

**3 · One generic word defeats the abstain gate.** `search_kb` refuses to return
anything when no branch recognises the query. Probed with *"What is our policy on
xyzzy frobnication?"*, Opus issued two searches: `"xyzzy frobnication policy"`
came back with four unrelated passages, because "policy" is a word this corpus
uses and the lexical branch scored a hit on it; the bare `"frobnication"` query
abstained cleanly. So the gate holds on a clean nonsense query and leaks on a
padded one. Both models still answered correctly, and both explicitly said the
passages they got were unrelated, which is the prompt rule doing the work the
retriever could not.

**4 · A tool-calling turn is not an empty turn.** Both models put explanatory
text and tool calls in the same message (*"I'll look that up in the knowledge
base."* alongside two `search_kb` calls). The scripted fake returns an empty
`content` when it calls a tool, so any code that assumes "tool call implies no
text" passes the offline suite and drops real output on the floor.

**5 · Parallel tool calls are the norm, and the count varies by model.** Opus
issued two calls in one message on almost every probe. Haiku went as wide as
four in a single message on the probe that pushes for exhaustive search. The
`ToolNode` handles the fan-out, but a naive implementation that assumed one call
per turn would have looked correct against the fake model.

**6 · The memory rule and the grounding rule collide, and the two models resolve
it differently.** The system prompt says to search before answering any company
question. The checkpointer means the answer may already be in the thread. Asked
the same-thread follow-up *"And how much of that can I roll over?"*, Haiku
answered straight from memory with no search at all, while Opus searched again
and re-cited. Both are defensible readings of the prompt, and nothing in the code
picks one.

**7 · The loop really does loop, but only under pressure.** Most probes finish
in two model turns. The probe that explicitly demands several rewordings before
giving up drove Opus to four turns and six tool executions, and Haiku to three
turns and seven. That is the ReAct cycle the offline test cannot reach, because a
scripted model has no reason to keep trying.

## What still is not proven

- **Not production.** Demo scale, a fictional knowledge base (Acme Robotics),
  13 markdown documents and 85 passages. Nobody has used it but me.
- **The dense branch here is a stand-in.** Hashed character n-grams, with real
  embeddings only behind `USE_ST=1`, and this run did not measure that path.
  Finding 2 is the cost of the stand-in.
- **No eval harness.** The live check prints a trace for a human to read; it does
  not score answers, and there is no regression gate on answer quality. The
  retrieval numbers that are gated live in a different repo.
- **`MemorySaver` is in-process.** Memory dies with the process. Swapping in
  `SqliteSaver` to persist it has not been done.
- **No human-in-the-loop gate.** `interrupt_before=["tools"]` is not wired.

## Two things the run changed in the code

`live_check.py` was reading message text through `.text`, which has been both a
method and a property across langchain-core versions. The method form emits a
deprecation warning, and those warnings printed into the middle of the trace this
file is made of. It now reads `content` directly.

Finding 2 became `test_fallback_dense_branch_is_sensitive_to_phrasing`. The
limitation was already true before the run; the run is what made it visible, and
a limit worth knowing is worth failing a build over when it changes.
