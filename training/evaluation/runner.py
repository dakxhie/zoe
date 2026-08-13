"""Evaluation runner: same prompts → base vs adapter (opt-in only).

Writes concrete Sprint 26 artifacts under training/evaluation/results/sprint26/
(or --artifact-dir). Never invents human rubric scores.

Success requires verified on-disk artifacts. No success banner without verification.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from training.evaluation.artifacts import (
    EXPECTED_SPRINT26_HELD_OUT_N,
    ARTIFACT_SCHEMA_VERSION,
    generation_row,
    prompt_messages_from_example,
    required_artifact_paths,
    resolve_artifact_dir,
    verify_mode_artifacts,
    write_mode_artifacts,
)
from training.evaluation.metrics import (
    PERSONALITY_EVAL_CHECKS,
    RUBRIC_DIMENSIONS,
    empty_scorecard,
    score_structured_output_validity,
    score_tool_claim_heuristic,
)


@dataclass
class EvaluationPlan:
    config_path: Path
    split: str
    modes: list[str]
    adapter_path: Path | None = None
    output_path: Path | None = None  # legacy single JSON dump (optional)
    artifact_dir: Path | None = None


def describe_plan(plan: EvaluationPlan) -> str:
    artifact = plan.artifact_dir or "(auto: cwd or repo training/evaluation/results/sprint26)"
    lines = [
        "Zoe evaluation plan (not executed unless --execute + ack):",
        f"  config: {plan.config_path}",
        f"  split: {plan.split}",
        f"  modes: {plan.modes}",
        f"  adapter: {plan.adapter_path}",
        f"  artifact_dir: {artifact}",
        f"  legacy_output: {plan.output_path}",
        f"  rubric dimensions: {list(RUBRIC_DIMENSIONS)}",
        f"  personality checks: {list(PERSONALITY_EVAL_CHECKS)}",
        f"  legacy metric names: {list(empty_scorecard())}",
        "  rule: held_out_eval must never have been used for training",
        "  tools_available during this offline generation eval: false",
        "  NOTE: dry plan writes NO baseline artifacts.",
        "  NOTE: BASELINE MEASUREMENT COMPLETE prints only after artifact verification.",
    ]
    return "\n".join(lines)


def load_eval_examples(split_path: Path) -> list[dict[str, Any]]:
    """Load held-out examples. Prefer Sprint 26 file when a directory is given."""
    if split_path.is_file():
        files = [split_path]
    else:
        preferred = split_path / "eval_sprint26.jsonl"
        legacy = split_path / "eval_sprint23.jsonl"
        if preferred.exists():
            files = [preferred]
        elif legacy.exists():
            files = [legacy]
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


def _resolve_config_path(config_path: Path, repo_root: Path) -> Path:
    if config_path.is_absolute() and config_path.is_file():
        return config_path.resolve()
    cwd_candidate = (Path.cwd() / config_path).resolve()
    if cwd_candidate.is_file():
        return cwd_candidate
    repo_candidate = (repo_root / config_path).resolve()
    if repo_candidate.is_file():
        return repo_candidate
    # Fall back to absolute resolve for clearer errors.
    return config_path.resolve()


def run_evaluation(plan: EvaluationPlan) -> int:
    """Load models and generate — only after explicit ack in CLI."""
    from training.scripts import load_yaml_config

    repo_root = Path(__file__).resolve().parents[2]
    cwd = Path.cwd().resolve()
    print(f"[baseline] cwd={cwd}")
    print(f"[baseline] repo_root_from_file={repo_root}")

    config_path = _resolve_config_path(Path(plan.config_path), repo_root)
    print(f"[baseline] config={config_path}")
    if not config_path.is_file():
        print(f"ERROR: config not found: {config_path}")
        return 1

    cfg = load_yaml_config(config_path)
    data = cfg.get("data", {})
    if plan.split == "held_out_eval":
        split_path = Path(data["held_out_eval_path"])
    else:
        split_path = Path(data["validation_path"])

    if not split_path.is_absolute():
        cwd_split = (cwd / split_path).resolve()
        repo_split = (repo_root / split_path).resolve()
        if cwd_split.exists():
            split_path = cwd_split
        elif repo_split.exists():
            split_path = repo_split
        else:
            split_path = cwd_split
    else:
        split_path = split_path.resolve()

    print(f"[baseline] resolved_eval_dataset={split_path}")
    if not split_path.exists():
        print(f"ERROR: evaluation dataset not found: {split_path}")
        return 1

    if plan.split == "held_out_eval" and split_path.name != "eval_sprint26.jsonl":
        print(
            "ERROR: canonical Sprint 26 baseline requires "
            f"eval_sprint26.jsonl, got {split_path.name}"
        )
        return 1

    examples = load_eval_examples(split_path)
    print(f"[baseline] examples_loaded={len(examples)}")
    if not examples:
        print(f"ERROR: No eval examples found under {split_path}")
        return 1
    if plan.split == "held_out_eval" and len(examples) != EXPECTED_SPRINT26_HELD_OUT_N:
        print(
            "ERROR: Sprint 26 held-out size mismatch: "
            f"expected {EXPECTED_SPRINT26_HELD_OUT_N}, got {len(examples)}"
        )
        return 1

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed
    except ImportError as exc:
        print(f"ERROR: Missing eval dependencies: {exc}")
        return 1

    if "adapter" in plan.modes:
        try:
            from peft import PeftModel  # noqa: F401
        except ImportError as exc:
            print(f"ERROR: Missing peft for adapter mode: {exc}")
            return 1

    model_name = cfg["model"]["name"]
    model_revision = cfg["model"].get("revision")
    gen_cfg = cfg.get("evaluation", {})
    seed = int(gen_cfg.get("seed", cfg.get("training", {}).get("seed", 42)))
    set_seed(seed)
    print(f"[baseline] model_identifier={model_name}")
    print(f"[baseline] model_revision={model_revision}")
    print(f"[baseline] generation_seed={seed}")

    tok_kwargs: dict[str, Any] = {}
    if model_revision:
        tok_kwargs["revision"] = model_revision
    tokenizer = AutoTokenizer.from_pretrained(model_name, **tok_kwargs)

    artifact_dir = resolve_artifact_dir(
        plan.artifact_dir,
        repo_root=repo_root,
        cwd=cwd,
    )
    print(f"[baseline] artifact_dir={artifact_dir}")
    for mode in plan.modes:
        expected = required_artifact_paths(artifact_dir, mode=mode)
        print(f"[baseline] expected_{mode}_artifacts=")
        for kind, path in expected.items():
            print(f"    {kind}: {path}")

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
        "rubric_version": gen_cfg.get("rubric_version", "colab_v1"),
        "split_path": str(split_path).replace("\\", "/"),
        "n_examples": len(examples),
        "modes": plan.modes,
        "adapter_path": str(plan.adapter_path) if plan.adapter_path else None,
        "artifact_dir": str(artifact_dir).replace("\\", "/"),
        "cwd": str(cwd).replace("\\", "/"),
        "repo_root_from_file": str(repo_root).replace("\\", "/"),
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "note": (
            "Human rubric scoring still required for personality/quality. "
            "Automated fields are heuristics only — not invented rubric averages."
        ),
    }

    results: list[dict[str, Any]] = []
    for mode in plan.modes:
        if mode == "adapter" and plan.adapter_path is None:
            print("ERROR: adapter mode requested but --adapter-path missing")
            return 1
        if mode == "adapter":
            from peft import PeftModel
        else:
            PeftModel = None  # type: ignore[assignment]

        print(f"[baseline] generation_start mode={mode}")
        dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        model_kwargs: dict[str, Any] = {
            "dtype": dtype,
        }
        if model_revision:
            model_kwargs["revision"] = model_revision
        if torch.cuda.is_available():
            model_kwargs["device_map"] = "auto"
        base = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)
        if not torch.cuda.is_available():
            base = base.to("cpu")
        model = base
        if mode == "adapter":
            assert PeftModel is not None
            model = PeftModel.from_pretrained(base, str(plan.adapter_path))
            if not torch.cuda.is_available():
                model = model.to("cpu")
        model.eval()

        for idx, ex in enumerate(examples, start=1):
            error: str | None = None
            text = ""
            auto_metrics: dict[str, Any] = {}
            try:
                messages = prompt_messages_from_example(ex)
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
                auto_struct = score_structured_output_validity(text)
                auto_tool = score_tool_claim_heuristic(text)
                auto_metrics = {
                    auto_struct.name: auto_struct.value,
                    auto_tool.name: auto_tool.value,
                    "auto_tool_notes": auto_tool.notes,
                }
            except Exception as exc:  # noqa: BLE001 — record per-example failure
                error = f"{type(exc).__name__}: {exc}"
                text = ""
                auto_metrics = {}
                print(f"[baseline] generation_error id={ex.get('id')} err={error}")

            results.append(
                generation_row(
                    example=ex,
                    mode=mode,
                    response=text,
                    error=error,
                    auto_metrics=auto_metrics,
                )
            )
            if idx == 1 or idx == len(examples) or idx % 25 == 0:
                print(f"[baseline] generation_progress mode={mode} {idx}/{len(examples)}")

        ok_n = sum(1 for r in results if r.get("mode") == mode and r.get("ok"))
        fail_n = sum(1 for r in results if r.get("mode") == mode and not r.get("ok"))
        print(
            f"[baseline] generation_complete mode={mode} "
            f"ok={ok_n} failed={fail_n} total={ok_n + fail_n}"
        )
        if ok_n < 1:
            print(
                f"ERROR: zero successful generations for mode={mode}; "
                "refusing success."
            )
            # Still attempt to write diagnostic artifacts below only if we have rows.
            # But overall exit will be non-zero.

        del model
        del base
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    written: dict[str, dict[str, Path]] = {}
    try:
        print(f"[baseline] artifact_writing_start dir={artifact_dir}")
        for mode in plan.modes:
            written[mode] = write_mode_artifacts(
                artifact_dir=artifact_dir,
                mode=mode,
                generations=results,
                run_meta=run_meta,
            )
            print(f"[baseline] artifact_writing_complete mode={mode}")
            for kind, path in written[mode].items():
                print(f"    wrote {kind}: {path}")
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: artifact writing failed: {exc}")
        return 1

    # Optional legacy combined dump (not the primary artifact).
    if plan.output_path is not None:
        legacy = plan.output_path
        if not legacy.is_absolute():
            legacy = (cwd / legacy).resolve()
        legacy.parent.mkdir(parents=True, exist_ok=True)
        payload = {"run_meta": run_meta, "results": results}
        legacy.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        legacy.with_suffix(".meta.json").write_text(
            json.dumps(run_meta, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"[baseline] wrote_legacy_combined_json={legacy}")

    # Hard verification gate — never claim complete without files on disk.
    all_ok = True
    for mode in plan.modes:
        ok, errors = verify_mode_artifacts(artifact_dir, mode=mode)
        print(f"[baseline] artifact_verification mode={mode} ok={ok}")
        if not ok:
            all_ok = False
            for err in errors:
                print(f"  VERIFY FAIL: {err}")
        mode_ok = sum(1 for r in results if r.get("mode") == mode and r.get("ok"))
        if mode_ok < 1:
            all_ok = False
            print(f"  VERIFY FAIL: zero successful generations for mode={mode}")

    if not all_ok:
        print("BASELINE MEASUREMENT FAILED — required artifacts missing or invalid.")
        print(f"Checked directory: {artifact_dir}")
        return 1

    if plan.modes == ["base"]:
        print("BASELINE MEASUREMENT COMPLETE")
    else:
        print("EVALUATION MEASUREMENT COMPLETE")
    for mode, paths in written.items():
        print(f"  mode={mode}")
        for kind, path in paths.items():
            print(f"    {kind}: {path}")
    print(
        "Human / judge scoring still required for personality and quality metrics. "
        "Do not invent missing rubric averages."
    )
    return 0
