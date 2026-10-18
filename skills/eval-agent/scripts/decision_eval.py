#!/usr/bin/env python3
"""decision_eval.py — measure a decision point before it leaves shadow mode.

Asks a decision model, through LiteLLM only, one labelled question per case — twice for a
`choice` question (options as given, then reversed) — and writes what the policy needs:
accuracy, per-label recall, calibration, a min_confidence sweep, order flips, refusals, latency.

    python decision_eval.py --cases cases.jsonl --question question.json --out report.md \
        [--no-personal-data] [--raw raw.jsonl] [--concurrency 4] [--timeout 10]

cases.jsonl   one object per line: {"id": "...", "state": <string|object|array>, "label": "..."}
question.json {"name": "...", "type": "choice" | "noul", "instructions": "...",
               "options": {"<label>": "<description>", ...}}      (options: choice only;
               a noul question is labelled "yes" / "no")
Model         DAYUSE_DECISION_MODEL (pinned); provider key from the environment (token broker).

States are never printed or written to the report. Requires litellm>=1.105.0 (OpenRouter as a decision provider).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import sys
import time
from collections import Counter
from collections.abc import Mapping
from typing import Any

# Only these prefixes keep the state on infrastructure we run in the EU (gdpr-guardrails §4).
SELF_HOSTED_PREFIXES = ("hosted_vllm/",)
SWEEP = [round(0.50 + 0.05 * i, 2) for i in range(10)]


def main() -> int:
    args = _parse()
    model = os.environ.get("DAYUSE_DECISION_MODEL", "")
    if not model:
        sys.exit("DAYUSE_DECISION_MODEL is not set.")
    if model.endswith(("-latest", "-preview")):
        sys.exit(f"{model!r} is an alias: pin an exact version before measuring it.")
    if not model.startswith(SELF_HOSTED_PREFIXES) and not args.no_personal_data:
        sys.exit(
            f"{model!r} is a third-party provider. Confirm the cases hold no personal data with "
            "--no-personal-data, or point DAYUSE_DECISION_MODEL at a self-hosted EU model."
        )
    question = json.load(open(args.question, encoding="utf-8"))
    cases = [json.loads(line) for line in open(args.cases, encoding="utf-8") if line.strip()]
    _validate(question, cases)

    records = asyncio.run(_run_all(model, question, cases, args.concurrency, args.timeout))
    report = _report(model, question, records)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(report)
    if args.raw:
        with open(args.raw, "w", encoding="utf-8") as fh:
            for r in records:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(report.split("\n## ")[0])
    return 0


def _parse() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--cases", required=True)
    p.add_argument("--question", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--raw", help="optional JSONL of per-case results (ids, picks, no state)")
    p.add_argument("--no-personal-data", action="store_true",
                   help="I confirm the cases contain no personal data")
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--timeout", type=float, default=10.0)
    return p.parse_args()


def _validate(question: Mapping[str, Any], cases: list[dict[str, Any]]) -> None:
    qtype = question.get("type")
    if qtype not in ("choice", "noul"):
        sys.exit("question.type must be 'choice' or 'noul'.")
    labels = set(question.get("options", {})) if qtype == "choice" else {"yes", "no"}
    if qtype == "choice" and len(labels) < 2:
        sys.exit("a choice question needs at least two options.")
    bad = [c.get("id") for c in cases if c.get("label") not in labels or "state" not in c]
    if bad:
        sys.exit(f"cases with a missing state or a label outside {sorted(labels)}: {bad[:10]}")


async def _run_all(model, question, cases, concurrency, timeout) -> list[dict[str, Any]]:
    import litellm  # imported here so the module loads without it (tests, --help)

    sem = asyncio.Semaphore(concurrency)

    async def ask(state: Any, spec: Mapping[str, Any]) -> dict[str, Any]:
        async with sem:
            started = time.perf_counter()
            try:
                resp = await asyncio.wait_for(
                    litellm.asystemone(model=model, state=state, questions={question["name"]: spec}),
                    timeout=timeout,
                )
            except Exception as exc:
                return {"status": "error", "error": type(exc).__name__}
            body = _as_dict(resp)
            answer = (body.get("answers") or {}).get(question["name"]) or {}
            out = {"latency_s": time.perf_counter() - started, "model": body.get("model")}
            if not answer or answer.get("type") == "refusal":
                return {**out, "status": "refusal"}
            if question["type"] == "noul":
                p = float(answer["noul"])
                return {**out, "status": "ok", "pick": "yes" if p >= 0.5 else "no",
                        "confidence": max(p, 1 - p), "p_yes": p}
            return {**out, "status": "ok", "pick": answer.get("choice"),
                    "confidence": answer.get("confidence")}

    def spec(reverse: bool) -> dict[str, Any]:
        s = {"type": question["type"], "instructions": question["instructions"]}
        if question["type"] == "choice":
            items = list(question["options"].items())
            s["criteria"] = dict(reversed(items) if reverse else items)
        return s

    async def one(case: dict[str, Any]) -> dict[str, Any]:
        first = await ask(case["state"], spec(False))
        rec = {"id": case.get("id"), "label": case["label"], **first}
        if question["type"] == "choice":
            second = await ask(case["state"], spec(True))
            rec["pick_reversed"] = second.get("pick") if second.get("status") == "ok" else None
        return rec

    return await asyncio.gather(*(one(c) for c in cases))


def _as_dict(response: Any) -> dict[str, Any]:
    if isinstance(response, Mapping):
        return dict(response)
    dump = getattr(response, "model_dump", None)
    if callable(dump):
        return dump()
    raise TypeError(f"unexpected decision response type: {type(response).__name__}")


def _report(model: str, question: Mapping[str, Any], records: list[dict[str, Any]]) -> str:
    n = len(records)
    ok = [r for r in records if r["status"] == "ok" and r.get("confidence") is not None]
    refusals = sum(r["status"] == "refusal" for r in records)
    errors = sum(r["status"] == "error" for r in records)
    correct = [r["pick"] == r["label"] for r in ok]
    acc = _pct(sum(correct), len(ok))
    versions = sorted({str(r.get("model")) for r in records if r.get("model")})

    lines = [
        f"# Decision eval — `{question['name']}` ({question['type']})",
        "",
        f"- Model requested: `{model}` — versions that answered: {', '.join(versions) or 'none'}",
        f"- Cases: {n} — answered: {len(ok)} — refusals: {refusals} — errors: {errors}",
        f"- Accuracy on answered cases: {acc}",
    ]
    if len(versions) > 1:
        lines.append("- WARNING: more than one model version answered — the numbers mix versions.")

    lines += ["", "## Per label", "", "Refusals and errors count as misses.", "",
              "| label | cases | recall |", "|---|---|---|"]
    by_label = Counter(r["label"] for r in records)
    for label, count in sorted(by_label.items()):
        hits = sum(1 for r in ok if r["label"] == label and r["pick"] == label)
        lines.append(f"| {label} | {count} | {_pct(hits, count)} |")

    lines += ["", "## Calibration (10 bins)", "",
              "| confidence | cases | mean confidence | accuracy |", "|---|---|---|---|"]
    ece = 0.0
    for b in range(10):
        lo, hi = b / 10, (b + 1) / 10
        in_bin = [r for r in ok if lo <= r["confidence"] < hi or (b == 9 and r["confidence"] == 1.0)]
        if not in_bin:
            continue
        mean_conf = sum(r["confidence"] for r in in_bin) / len(in_bin)
        bin_acc = sum(r["pick"] == r["label"] for r in in_bin) / len(in_bin)
        ece += len(in_bin) / len(ok) * abs(mean_conf - bin_acc)
        lines.append(f"| {lo:.1f}–{hi:.1f} | {len(in_bin)} | {mean_conf:.3f} | {bin_acc:.3f} |")
    lines += ["", f"Expected calibration error: {ece:.3f}" if ok else "Expected calibration error: n/a"]

    lines += ["", "## min_confidence sweep", "",
              "Below the threshold, and on any refusal or error, the case goes to the safe branch. "
              "Coverage = share of all cases the decision model would decide.",
              "", "| min_confidence | coverage | accuracy when enforced |", "|---|---|---|"]
    for t in SWEEP:
        enforced = [r for r in ok if r["confidence"] >= t]
        hits = sum(r["pick"] == r["label"] for r in enforced)
        lines.append(f"| {t:.2f} | {_pct(len(enforced), n)} | {_pct(hits, len(enforced))} |")

    if question["type"] == "choice":
        pairs = [r for r in ok if r.get("pick_reversed") is not None]
        flips = sum(r["pick"] != r["pick_reversed"] for r in pairs)
        lines += ["", "## Option order", "",
                  f"Answers that changed when the option order was reversed: {_pct(flips, len(pairs))} "
                  f"({flips}/{len(pairs)})"]

    lat = sorted(r["latency_s"] for r in records if "latency_s" in r)
    lines += ["", "## Latency (first call per case, measured on this run)", "",
              f"P50 {_quantile(lat, 0.50)} — P95 {_quantile(lat, 0.95)} — calls: {len(lat)}", ""]
    return "\n".join(lines)


def _pct(num: int, den: int) -> str:
    return f"{100 * num / den:.1f} %" if den else "n/a"


def _quantile(values: list[float], q: float) -> str:
    if not values:
        return "n/a"
    rank = max(0, math.ceil(q * len(values)) - 1)  # nearest-rank
    return f"{values[rank]:.3f} s"


if __name__ == "__main__":
    raise SystemExit(main())
