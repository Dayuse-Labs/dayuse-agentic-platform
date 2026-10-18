# Decision-model providers (state as of 2026-10-14)

This market is weeks old: re-check every line before relying on it. Anything marked **to collect** is unknown, not "no".

## Matrix

| Provider / model | LiteLLM id | Route | Input | ZDR | Processing region | Price (per 1M input tokens) | Dayuse status |
|---|---|---|---|---|---|---|---|
| TypeSafe **Jev** via **OpenRouter** (Dayuse route, decided 2026-10-14) | `openrouter/typesafe/jev-1.13.0` (`jev-latest`, `jev-preview`: forbidden) | OpenRouter `/api/alpha/decisions`, key `OPENROUTER_API_KEY` | text, JSON, arrays | TypeSafe: enterprise customers only; OpenRouter on this route: **to collect** | TypeSafe: **to collect**; OpenRouter: **to collect** | $0.042, output free (OpenRouter listing) | **Default for prototypes** — states without personal data until ZDR + region are confirmed for both processors |
| TypeSafe **Jev**, direct | `typesafe/jev-1.13.0` | `/v1/systemone`, key `TYPESAFE_API_KEY` | text, JSON, arrays | enterprise customers only | **to collect** | $0.042, output free | Not used: needs a TypeSafe account; one processor fewer than the OpenRouter route |
| OpenAI **GPT-6 Luna Decisions** (public beta) | `openai/gpt-6-luna` | `/v1/decisions` | text, images | eligible "with limitations", subject to OpenAI's prior approval | US or Europe (EEA + CH); Europe requires ZDR or a modified-retention arrangement | $0.10, output free; regional premiums apply | Alternative when images are needed; not evaluated |
| **Self-hosted open weights** (vLLM, SGLang, Ollama, llama.cpp) | `hosted_vllm/<model>` | `/v1/systemone` | depends on model | ours | ours (EU) | infra cost: **to collect** | **Target for states with personal data**; model choice **to collect** |
| Microsoft **Decision-1** (Foundry) | `azure_ai/<deployment>` | `/v1/systemone` | text | **to collect** | Azure region of the deployment: **to verify** | $0.042 (LLM Gateway listing) | Not evaluated |
| Cloudflare **Clef**, Perplexity **pplx-decider** | `cloudflare/clef`, `perplexity/pplx-decider-v1-27b` | `/v1/systemone` | text (hosted) | **to collect** | **to collect** | **to collect** | Not evaluated; both also ship Apache-2.0 open weights |

Open-weight candidates for EU self-hosting (Apache-2.0 per the awesome-decision-models list): Clef and pplx-decider (27B, Qwen-based), Standard One (3B / 8B, Ministral 3 base), Wald-4B, JevK5 (2B–9B). Several others are non-commercial (OpenJev, Vev, StartLux-Decision weights): **exclude** them.

## Required LiteLLM version

- The decision routes (`litellm.decisions` / `adecisions` / `systemone` / `asystemone`) exist from **v1.104.2** on the 1.104 line and **v1.105.0-rc.3** otherwise.
- **OpenRouter** as a decision provider appears in the **v1.105.0** release notes, not in the decisions docs' provider table. For the Dayuse route the minimum is therefore **1.105.0**; 1.104.x with OpenRouter: **to collect**.
- From 1.105.0, a decision request sending `safety_identifier` to a non-OpenAI provider fails unless `drop_params: true`.
- Fleet evidence (Spike A, 2026-10-14): `litellm==1.105.1` with `google-adk==2.12.0` resolves and passes every hermetic suite of `dayuse-agent-fleet`. **No real provider call yet** (the Cowork VM could not reach `openrouter.ai`). The plugin pins an exact version only after those calls and a ≥ 4-day release buffer.
- The old `litellm==1.90.2` pin blamed `orjson`: Spike A did not reproduce it. Compiled wheels start at 1.92.0 (not 1.91), and `orjson` is imported only under `litellm/proxy/`. The fleet declares `orjson==3.13.0` in its common lib as insurance.

## SDK contract of `litellm.asystemone` (read in LiteLLM 1.105.1's code by Spike A, not observed live)

- `async asystemone(model, state=None, questions=None, api_key=None, api_base=None, timeout=None, custom_llm_provider=None, extra_headers=None, safety_identifier=None, **kwargs)`.
- Providers: `openai`, `openrouter`, `azure_ai`, `perplexity`, `typesafe`, `strands_decider`, `cloudflare`, `hosted_vllm`.
- Returns a **frozen pydantic object**: `r.model`, `r.answers[name]`, `r.usage`. Choice answers have `.choice`, `.confidence`, `.probabilities`; noul answers `.noul` (a float); score answers `.score`, `.confidence`, `.legend`, `.probabilities`. `r["answers"]` raises `TypeError`; `r.model_dump()` gives the JSON shape.
- Request errors are **raised**: `BadRequestError` (unknown provider, invalid questions), `UnsupportedParamsError` (`safety_identifier` to a provider without it), `AuthenticationError`, mapped upstream errors such as `APIConnectionError`.
- Model-level refusal shape and the `model` value returned through OpenRouter: **to collect**.

## Known weaknesses (measured by others — re-measure on our data)

- **Option order**: reordering 16 options changed 7.0 % of Jev's answers (model-card figures reported by redreamality).
- **Calibration is per distribution**: on Decision Index 0.3.1, Jev's mean confidence was 0.81 for 0.74 accuracy. A confidence is calibrated for a model *and* a data distribution, not in general.
- **Drift under an alias**: 20 Jev answers changed between two Decision Index runs a month apart → pin versions.
- **Trained classifiers can win**: on prompt-injection detection (English), a ~200M DeBERTa classifier scored 89.01 % at 54 ms vs Jev 86.35 % at 348 ms (Red Hat, via redreamality).
- **Language**: benchmarks are English-first. Jev's quality on French states: **to collect**.
- **Latency**: Jev on OpenRouter, P50 0.21 s / P95 0.34 s / P99 0.75 s (telemetry as of 2026-10-01). The helper's default timeout (2 s) is a starting point, not a measurement of ours.

## To collect before going beyond prototype

1. A first real `asystemone` call on `openrouter/typesafe/jev-1.13.0` (blocked by egress on 2026-10-14): returned `model`, refusal shape, latency.
2. Processing region and a written ZDR commitment for **both** processors: OpenRouter (this route) and TypeSafe (enterprise terms).
3. Jev accuracy and calibration on a labelled sample of **our** French traffic.
4. Order-flip rate on our option sets.
5. Self-hosted EU candidate: model, licence check, GPU cost, latency.
6. The exact LiteLLM pin, from the fleet once real calls pass.

## Sources

- LiteLLM — Decisions / System One routes, providers, SDK functions: https://docs.litellm.ai/docs/decisions
- LiteLLM v1.105.0 release notes: https://docs.litellm.ai/release_notes/v1.105.0/v1-105-0
- LiteLLM — TypeSafe pass-through, model ids: https://docs.litellm.ai/docs/pass_through/typesafe.md
- Promptfoo — TypeSafe provider (limits, ZDR, pinned versions): https://www.promptfoo.dev/docs/providers/typesafe/
- ZenMux — System One request/response fields: https://zenmux.ai/docs/api/typesafe/systemone
- DigitalOcean — System One API: https://docs.digitalocean.com/products/inference/how-to/use-system-one-api/
- OpenRouter — GPT-6 Luna Decisions: https://openrouter.ai/openai/gpt-6-luna-decisions
- LLM Gateway — Decisions API, GPT-6 Luna, Decision-1, Jev: https://llmgateway.io/blog/openai-decisions-api
- Beri — Decisions API ZDR and residency (citing OpenAI's data-controls page): https://www.beri.net/article/openai-decisions-api-public-beta-gpt-6-luna-pricing-cache-discount-vs-jev-clef-zdr-residency
- Firecrawl — Decisions API vs Jev (latency telemetry): https://www.firecrawl.dev/blog/openai-decisions-api-vs-jev
- awesome-decision-models (open weights, licences, runtimes): https://github.com/AnotiaWang/awesome-decision-models
- One month after Jev — counter-evidence and benchmarks: https://redreamality.com/blog/open-decision-models-2026-survey-benchmarks/
- Jev as an ADK model router (`before_model_callback`): https://github.com/vinaychawla-ops/jev-adk-model-router
- Spike A report — `dayuse-agent-fleet`, branch `spike/a-litellm-adk`, `SPIKE-A-REPORT.md` (2026-10-14): versions, hermetic results, SDK contract read in code.
