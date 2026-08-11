"""Evaluation runner: same prompts → base vs adapter (opt-in only)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from training.evaluation.metrics import (
    PERSONALITY_EVAL_CHECKS,
    RUBRIC_DIMENSIONS,
    empty_scorecard,
    placeholder_human_metrics,
    score_structured_output_validity,
    score_tool_claim_heuristic,
)


@dataclass
class EvaluationPlan:
    config_path: Path
    split: str
    modes: list[str]
    adapter_path: Path | None = None
    output_path: Path | None = None


def describe_plan(plan: EvaluationPlan) -> str:
    lines = [
        "Zoe evaluation plan (not executed unless --execute + ack):",
        f"  config: {plan.config_path}",
        f"  split: {plan.split}",
        f"  modes: {plan.modes}",
        f"  adapter: {plan.adapter_path}",
        f"  rubric dimensions: {list(RUBRIC_DIMENSIONS)}",
        f"  personality checks: {list(PERSONALITY_EVAL_CHECKS)}",
        f"  legacy metric names: {list(empty_scorecard())}",
        "  rule: held_out_eval must never have been used for training",
        "  tools_available during this offline generation eval: false",
    ]
    return "\n".join(lines)


def load_eval_examples(split_path: Path) -> list[dict[str, Any]]:
    """Load held-out examples. Prefer eval_sprint23.jsonl when a directory is given."""
    if split_path.is_file():
        files = [split_path]
    else:
        preferred = split_path / "eval_sprint23.jsonl"
        if preferred.exists():
            files = [preferred]
        else:
            files = sorted(split_path.glob("*.jsonl"))
    rows: list[dict[str, Any]] = []
    for f in files:
        if not f.exists():
            continue
        for raw in f.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            rows.append(json.loads(line))
    return rows


def _messages_without_last_assistant(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    if messages and messages[-1].get("role") == "assistant":
        return messages[:-1]
    return list(messages)


def run_evaluation(plan: EvaluationPlan) -> int:
    """Load models and generate — only after explicit ack in CLI."""
    from training.scripts import load_yaml_config

    cfg = load_yaml_config(plan.config_path)
    data = cfg.get("data", {})
    if plan.split == "held_out_eval":
        split_path = Path(data["held_out_eval_path"])
    else:
        split_path = Path(data["validation_path"])

    examples = load_eval_examples(split_path)
    if not examples:
        print(f"No eval examples found under {split_path}")
        return 1

    try:
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed
    except ImportError as exc:
        print(f"Missing eval dependencies: {exc}")
        return 1

    model_name = cfg["model"]["name"]
    model_revision = cfg["model"].get("revision")
    gen_cfg = cfg.get("evaluation", {})
    seed = int(gen_cfg.get("seed", cfg.get("training", {}).get("seed", 42)))
    set_seed(seed)

    tok_kwargs: dict[str, Any] = {}
    if model_revision:
        tok_kwargs["revision"] = model_revision
    tokenizer = AutoTokenizer.from_pretrained(model_name, **tok_kwargs)

    run_meta = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_name": model_name,
        "model_revision": model_revision,
        "generation": {
            "max_new_tokens": int(gen_cfg.get("max_new_tokens", 256)),
            "temperature": float(gen_cfg.get("temperature", 0.7)),
            "top_p": float(gen_cfg.get("top_p", 0.9)),
            "do_sample": bool(gen_cfg.get("do_sample", True)),
            "seed": seed,
        },
        "system_prompt_source": gen_cfg.get("system_prompt_source", "dataset_messages"),
        "tools_available": bool(gen_cfg.get("tools_available", False)),
        "rubric_version": gen_cfg.get("rubric_version", "sprint24_v1"),
        "split_path": str(split_path),
        "n_examples": len(examples),
        "modes": plan.modes,
        "adapter_path": str(plan.adapter_path) if plan.adapter_path else None,
        "note": "Human rubric scoring still required; auto heuristics are partial.",
    }

    results: list[dict[str, Any]] = []
    for mode in plan.modes:
        if mode == "adapter" and plan.adapter_path is None:
            print("adapter mode requested but --adapter-path missing")
            return 1
        print(f"Loading mode={mode} ...")
        dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        model_kwargs: dict[str, Any] = {
            "dtype": dtype,
        }
        if model_revision:
            model_kwargs["revision"] = model_revision
        # Avoid device_map="auto" on CPU — it can meta-offload and crash (0xC0000005).
        if torch.cuda.is_available():
            model_kwargs["device_map"] = "auto"
        base = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)
        if not torch.cuda.is_available():
            base = base.to("cpu")
        model = base
        if mode == "adapter":
            model = PeftModel.from_pretrained(base, str(plan.adapter_path))
            if not torch.cuda.is_available():
                model = model.to("cpu")
        model.eval()

        for ex in examples:
            messages = _messages_without_last_assistant(ex["messages"])
            prompt = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
            inputs = tokenizer(prompt, return_tensors="pt")
            if torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}
            gen_kwargs = {
                "max_new_tokens": int(gen_cfg.get("max_new_tokens", 256)),
                "do_sample": bool(gen_cfg.get("do_sample", True)),
            }
            if gen_kwargs["do_sample"]:
                gen_kwargs["temperature"] = float(gen_cfg.get("temperature", 0.7))
                gen_kwargs["top_p"] = float(gen_cfg.get("top_p", 0.9))
            with torch.no_grad():
                out = model.generate(**inputs, **gen_kwargs)
            text = tokenizer.decode(
                out[0][inputs["input_ids"].shape[-1] :],
                skip_special_tokens=True,
            )
            meta = ex.get("metadata") or {}
            auto_struct = score_structured_output_validity(text)
            auto_tool = score_tool_claim_heuristic(text)
            row = {
                "id": ex.get("id"),
                "mode": mode,
                "response": text,
                "category": meta.get("category"),
                "personality_mode": meta.get("personality_mode"),
                "gold_assistant": ex["messages"][-1]["content"]
                if ex.get("messages") and ex["messages"][-1].get("role") == "assistant"
                else None,
                "auto_metrics": {
                    auto_struct.name: auto_struct.value,
                    auto_tool.name: auto_tool.value,
                    "auto_tool_notes": auto_tool.notes,
                },
                "rubric_scores": {dim: None for dim in RUBRIC_DIMENSIONS},
                "pending_metrics": [m.name for m in placeholder_human_metrics()],
                "personality_checks": {k: None for k in PERSONALITY_EVAL_CHECKS},
            }
            results.append(row)

        del model
        del base
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    out_path = plan.output_path or Path("training/adapters/eval_results_latest.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"run_meta": run_meta, "results": results}
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    meta_path = out_path.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(run_meta, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(results)} judgements to {out_path}")
    print(f"Wrote run metadata to {meta_path}")
    print("Human / judge scoring still required for personality and quality metrics.")
    return 0
