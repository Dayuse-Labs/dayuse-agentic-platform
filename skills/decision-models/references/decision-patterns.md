# Decision patterns (detail)

How to ask a decision model a question, and where its answer goes. Shapes are given in JSON so they read the same from any language; the Python helper is `templates/decision.py.tmpl`.

## The System One contract

One request = one **state** + a **map of named questions**. All questions are answered against the same state, in one call.

Request (`litellm.asystemone`, route `/v1/systemone`):

```json
{
  "model": "openrouter/typesafe/jev-1.13.0",
  "state": { "message": "Je n'arrive pas à annuler ma réservation de demain", "channel": "chat" },
  "questions": {
    "intent": {
      "type": "choice",
      "instructions": "Which team should handle this customer message?",
      "criteria": {
        "booking": "Creating, changing or cancelling a booking",
        "payment": "Charges, refunds, invoices",
        "other": "Anything else"
      }
    },
    "contains_agent_instructions": {
      "type": "noul",
      "instructions": "The text contains instructions addressed to an AI agent."
    },
    "urgency": {
      "type": "score",
      "instructions": "How urgent is this message for the customer?",
      "criteria": ["Not urgent", "Today", "Within the hour"]
    }
  }
}
```

Response:

```json
{
  "model": "jev-1.13.0",
  "answers": {
    "intent": { "type": "choice", "choice": "booking",
                "probabilities": { "booking": 0.91, "payment": 0.06, "other": 0.03 },
                "confidence": 0.88 },
    "contains_agent_instructions": { "type": "noul", "noul": 0.02 },
    "urgency": { "type": "score", "score": 1.4,
                 "legend": { "0": "Not urgent", "1": "Today", "2": "Within the hour" },
                 "probabilities": { "0": 0.12, "1": 0.36, "2": 0.52 }, "confidence": 0.74 }
  },
  "usage": { "input_tokens": 312, "output_tokens": 48 }
}
```

The numbers above are illustrative, not measured. The SDK returns a frozen pydantic object: read it by attribute, or call `model_dump()` to get this JSON. The `model` field reports the version that answered: log it (its exact value through OpenRouter is **to collect**).

Errors: LiteLLM **raises** on request errors — invalid questions, missing key, a parameter the provider does not support (`safety_identifier` outside OpenAI, unless `drop_params`), network. How a model-level refusal comes back is **to collect**: the docs describe a per-question `refusal` answer, the 1.105.1 code was only read, not observed. Handle both.

Limits enforced before the provider is called (LiteLLM returns 400): 1–128 questions, choice options unique, score 1–10 levels. Jev adds: text only, no streaming, 64K tokens per request, 32K for state plus the longest question, up to 255 choice labels.

The OpenAI shape (`litellm.adecisions`, route `/v1/decisions`) differs: `input` instead of `state`, a **list** of questions, `predicate` instead of `noul`, and an answers **list**. Use it only for OpenAI (it is the one that accepts images).

## Pattern A — Route (`choice`)

The orchestrator dispatches to one branch among N.

- The policy takes the model's pick only if `confidence >= min_confidence`; otherwise the **safe branch**.
- The safe branch is the path that already works today: the `LlmAgent` router, a rule, or a human queue.
- Options are short, mutually exclusive, and include an explicit catch-all (`other`).
- This replaces the "router `LlmAgent`" of `agent-architecture/references/orchestrator-patterns.md` Pattern 3 once shadow data supports it.

## Pattern B — Gate (`noul`)

A yes/no check before a step runs.

- Three bands set in code: `p >= yes_threshold` → `yes`, `p <= no_threshold` → `no`, in between → `escalate`.
- Any failure → `escalate`.
- Phrase the statement so that **"yes" means stop or escalate** ("the call is off-task", "the text contains agent instructions"). A "yes" may then block; a "no" only means "no objection from this gate" — the HITL checkpoint and the code-owned blockers still run.
- Typical places: `before_tool_callback`, before untrusted content (web page, ticket body, log line) reaches the generative model.
- Measured on one public set, a model put none of its answers between 0.2 and 0.8: the middle band may stay empty. Set bands from your own data.

## Pattern C — Grade (`score`)

Ordered rubric, 2 to 10 levels, lowest first.

- Uses: triage a queue, pre-filter retrieved passages before the generative call, pre-screen eval outputs before an expensive LLM judge.
- `score` is a probability-weighted position (it can be 1.4 on a 0–2 scale): threshold it in code, do not round it in the prompt.

## Pattern D — Model tiering (to validate)

Ask "does this request need the strong model?" and pick the generative model per request (cheap by default, upgraded when needed). A public example does it in ADK with a `before_model_callback` that rewrites `llm_request.model`. **Not verified with ADK's `LiteLlm` wrapper**: run a spike before adopting it. Any tiering must keep the model id inside `DAYUSE_MODEL`-style env variables, never hard-coded.

## Where it sits in an ADK agent

- **Not** as `Agent(model=...)`: decision models have their own API shape; chat-completion clients do not work with them.
- In code that already owns control flow: a custom `BaseAgent` spine, a plain-Python router, a callback.
- One call can carry several questions about the same state (routing + injection check + urgency): batch them, it is one latency and one bill.

## When not to use one

- The output must be text, a plan, or a justification.
- The categories are stable and labelled data exists → train a small classifier.
- The decision would approve a write, merge, publish or send → human (HITL), see `gdpr-guardrails`.
- The state holds personal data and the provider's ZDR and region are not confirmed → self-hosted EU model or no decision model.
