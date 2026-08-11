"""Colab GPU QLoRA training entrypoint for Zoe.

SAFETY: Importing this module does nothing.
Training and model download happen only when main() is invoked with
`--i-understand-this-starts-training`.

Canonical config: training/config/colab_qlora.yaml
Target hardware: Google Colab + NVIDIA GPU + 4-bit QLoRA (bitsandbytes).

CPU / non-CUDA training is intentionally unsupported.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from training.scripts.guards import assert_train_not_held_out  # noqa: E402

TRAIN_ACK_FLAG = "--i-understand-this-starts-training"
FORCE_OVERWRITE_FLAG = "--force-overwrite-output"
CANONICAL_CONFIG = _REPO / "training" / "config" / "colab_qlora.yaml"


def _refuse_without_ack(argv: list[str]) -> int:
    print("Zoe QLoRA trainer — SAFE MODE")
    print("No model weights were downloaded. No training was started.")
    print()
    print("Canonical Colab GPU QLoRA (requires CUDA + explicit ack):")
    print(
        "  python -m training.scripts.train_qlora "
        "--config training/config/colab_qlora.yaml "
        f"{TRAIN_ACK_FLAG}"
    )
    print()
    print("See docs/COLAB_FINE_TUNING_RUNBOOK.md")
    print("Prerequisites: prepare_dataset --pilot, validate_dataset, dry-check-config")
    if argv:
        print(f"(received argv without ack: {argv!r})")
    return 2


def _adapter_artifacts_present(out_dir: Path) -> bool:
    markers = (
        "adapter_model.safetensors",
        "adapter_model.bin",
        "adapter_config.json",
        "TRAINING_COMPLETE",
    )
    return any((out_dir / name).exists() for name in markers)


def _write_status(out_dir: Path, status: str, payload: dict | None = None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    body = {"status": status, "updated_at_utc": datetime.now(timezone.utc).isoformat()}
    if payload:
        body.update(payload)
    (out_dir / "TRAINING_STATUS.json").write_text(
        json.dumps(body, indent=2) + "\n", encoding="utf-8"
    )
    if status == "COMPLETE":
        (out_dir / "TRAINING_COMPLETE").write_text(
            datetime.now(timezone.utc).isoformat() + "\n", encoding="utf-8"
        )
        for name in ("TRAINING_INCOMPLETE", "TRAINING_FAILED"):
            marker = out_dir / name
            if marker.exists():
                marker.unlink()
    elif status == "RUNNING":
        (out_dir / "TRAINING_INCOMPLETE").write_text(
            "Training started but not marked complete.\n", encoding="utf-8"
        )
        complete = out_dir / "TRAINING_COMPLETE"
        if complete.exists():
            complete.unlink()
    elif status == "FAILED":
        (out_dir / "TRAINING_FAILED").write_text(
            datetime.now(timezone.utc).isoformat() + "\n", encoding="utf-8"
        )
        (out_dir / "TRAINING_INCOMPLETE").write_text(
            "Training failed; do not treat as a valid adapter.\n", encoding="utf-8"
        )


def _snapshot_run(cfg: dict, config_path: Path, out_dir: Path, extra: dict | None = None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    card = {
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_path),
        "config": cfg,
        "platform_intent": "google_colab_gpu_qlora",
        "note": "Adapter is experimental until held-out eval passes ship gate.",
    }
    if extra:
        card.update(extra)
    (out_dir / "run_card.json").write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
    # Snapshot the YAML bytes for reproducibility.
    try:
        (out_dir / "config_snapshot.yaml").write_text(
            config_path.read_text(encoding="utf-8"), encoding="utf-8"
        )
    except OSError:
        pass


def _run_training(config_path: Path, *, force_overwrite: bool) -> int:
    from training.scripts import load_yaml_config

    cfg = load_yaml_config(config_path)
    train_cfg = cfg["training"]
    data_cfg = cfg["data"]
    safety = cfg.get("safety") or {}
    q = cfg.get("quantization") or {}

    train_path = Path(data_cfg["train_path"])
    val_path = Path(data_cfg["validation_path"])
    held = Path(data_cfg["held_out_eval_path"])
    out_dir = Path(train_cfg["output_dir"])

    overlap_errors = assert_train_not_held_out(train_path, held, val_path)
    if overlap_errors and safety.get("refuse_on_held_out_overlap", True):
        print("Refusing to train due to data safety checks:")
        for err in overlap_errors[:30]:
            print(f"  - {err}")
        return 1

    if not train_path.exists() and safety.get("refuse_if_train_empty", True):
        print(f"Refusing: train path missing: {train_path}")
        print("Run: python -m training.scripts.prepare_dataset --sprint26-balanced --pilot")
        return 1

    if out_dir.exists() and _adapter_artifacts_present(out_dir) and not force_overwrite:
        print(f"Refusing to overwrite existing adapter artifacts in {out_dir}")
        print(f"Pass {FORCE_OVERWRITE_FLAG} only if intentional, or change output_dir.")
        return 1

    try:
        import torch
        from datasets import load_dataset
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        from trl import SFTConfig, SFTTrainer
    except ImportError as exc:
        print(
            "Missing training dependencies. On Colab, install requirements-training.txt "
            "after ensuring a CUDA PyTorch build is present.\n"
            f"Import error: {exc}"
        )
        return 1

    cuda = torch.cuda.is_available()
    want_4bit = bool(q.get("load_in_4bit", True))
    require_cuda = bool(safety.get("require_cuda", True))
    require_4bit = bool(safety.get("require_4bit", True))

    if require_cuda and not cuda:
        print("BLOCKER: Colab GPU QLoRA requires CUDA.")
        print("In Google Colab: Runtime → Change runtime type → GPU (T4/L4/A100).")
        print("CPU fine-tuning is not supported for this project.")
        return 1

    if require_4bit and not want_4bit:
        print("BLOCKER: Canonical Colab path requires load_in_4bit: true (QLoRA).")
        return 1

    if want_4bit and not cuda:
        print("BLOCKER: 4-bit QLoRA requires CUDA.")
        return 1

    model_name = cfg["model"]["name"]
    model_revision = cfg["model"].get("revision")
    lora = cfg["lora"]

    _snapshot_run(
        cfg,
        config_path,
        out_dir,
        extra={
            "cuda_available": cuda,
            "cuda_device_name": torch.cuda.get_device_name(0) if cuda else None,
            "load_in_4bit": True,
            "assistant_only_loss": True,
            "force_overwrite": force_overwrite,
        },
    )
    _write_status(out_dir, "RUNNING", {"config_path": str(config_path)})

    tok_kwargs: dict = {
        "trust_remote_code": bool(cfg["model"].get("trust_remote_code", False)),
    }
    if model_revision:
        tok_kwargs["revision"] = model_revision
    tokenizer = AutoTokenizer.from_pretrained(model_name, **tok_kwargs)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=getattr(
            torch, str(q.get("bnb_4bit_compute_dtype", "float16"))
        ),
        bnb_4bit_quant_type=str(q.get("bnb_4bit_quant_type", "nf4")),
        bnb_4bit_use_double_quant=bool(q.get("bnb_4bit_use_double_quant", True)),
    )
    model_kwargs: dict = {
        "trust_remote_code": bool(cfg["model"].get("trust_remote_code", False)),
        "quantization_config": bnb,
        "device_map": "auto",
    }
    if model_revision:
        model_kwargs["revision"] = model_revision

    model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)
    model = prepare_model_for_kbit_training(model)

    peft_config = LoraConfig(
        r=int(lora["r"]),
        lora_alpha=int(lora["lora_alpha"]),
        lora_dropout=float(lora["lora_dropout"]),
        bias=str(lora.get("bias", "none")),
        task_type=str(lora.get("task_type", "CAUSAL_LM")),
        target_modules=list(lora.get("target_modules") or []),
    )
    model = get_peft_model(model, peft_config)

    def _resolve_data_files(p: Path) -> str | list[str]:
        if p.is_file():
            return str(p)
        files = sorted(str(x) for x in p.glob("*.jsonl"))
        if not files:
            raise FileNotFoundError(f"No JSONL under {p}")
        return files

    ds = load_dataset(
        "json",
        data_files={
            "train": _resolve_data_files(train_path),
            "validation": _resolve_data_files(val_path),
        },
    )

    # Keep messages for chat-template + assistant-only loss (metadata never trained).
    def keep_messages(example: dict) -> dict:
        return {"messages": example["messages"]}

    drop_cols = [c for c in ds["train"].column_names if c != "messages"]
    ds = ds.map(keep_messages, remove_columns=drop_cols)

    max_len = int(train_cfg.get("max_seq_length", 2048))
    packing = bool(train_cfg.get("packing", False))

    sft_kwargs = {
        "output_dir": str(out_dir),
        "num_train_epochs": float(train_cfg["num_train_epochs"]),
        "per_device_train_batch_size": int(train_cfg["per_device_train_batch_size"]),
        "per_device_eval_batch_size": int(train_cfg["per_device_eval_batch_size"]),
        "gradient_accumulation_steps": int(train_cfg["gradient_accumulation_steps"]),
        "learning_rate": float(train_cfg["learning_rate"]),
        "lr_scheduler_type": str(train_cfg.get("lr_scheduler_type", "cosine")),
        "warmup_ratio": float(train_cfg.get("warmup_ratio", 0.03)),
        "logging_steps": int(train_cfg.get("logging_steps", 10)),
        "save_steps": int(train_cfg.get("save_steps", 100)),
        "eval_steps": int(train_cfg.get("eval_steps", 100)),
        "save_total_limit": int(train_cfg.get("save_total_limit", 3)),
        "fp16": bool(train_cfg.get("fp16", True)),
        "bf16": bool(train_cfg.get("bf16", False)),
        "gradient_checkpointing": bool(train_cfg.get("gradient_checkpointing", True)),
        "seed": int(train_cfg.get("seed", 42)),
        "report_to": train_cfg.get("report_to", "none"),
        "save_strategy": "steps",
        "eval_strategy": "steps",
        "max_length": max_len,
        "packing": packing,
        # Critical: train on assistant tokens only (Qwen chat template path).
        "assistant_only_loss": True,
    }

    args = SFTConfig(**sft_kwargs)
    trainer = SFTTrainer(
        model=model,
        args=args,
        train_dataset=ds["train"],
        eval_dataset=ds["validation"],
        processing_class=tokenizer,
    )

    t0 = time.time()
    try:
        train_result = trainer.train()
        duration_s = time.time() - t0
        metrics = dict(getattr(train_result, "metrics", {}) or {})
        try:
            eval_metrics = trainer.evaluate()
            metrics.update(
                {
                    (f"eval_{k}" if not str(k).startswith("eval") else k): v
                    for k, v in (eval_metrics or {}).items()
                }
            )
        except Exception as exc:  # noqa: BLE001
            metrics["eval_error"] = str(exc)

        # PEFT adapter only — never overwrite base model files on disk.
        trainer.model.save_pretrained(out_dir)
        tokenizer.save_pretrained(out_dir)

        summary = {
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": duration_s,
            "base_model": model_name,
            "model_revision": model_revision,
            "train_path": str(train_path),
            "validation_path": str(val_path),
            "held_out_eval_path": str(held),
            "train_count": len(ds["train"]),
            "validation_count": len(ds["validation"]),
            "learning_rate": float(train_cfg["learning_rate"]),
            "num_train_epochs": float(train_cfg["num_train_epochs"]),
            "lora": lora,
            "quantization_effective": {
                "load_in_4bit": True,
                "bnb_4bit_quant_type": str(q.get("bnb_4bit_quant_type", "nf4")),
                "bnb_4bit_use_double_quant": bool(q.get("bnb_4bit_use_double_quant", True)),
                "bnb_4bit_compute_dtype": str(q.get("bnb_4bit_compute_dtype", "float16")),
            },
            "assistant_only_loss": True,
            "seed": int(train_cfg.get("seed", 42)),
            "adapter_output": str(out_dir),
            "metrics": metrics,
            "cuda_available": True,
            "cuda_device_name": torch.cuda.get_device_name(0),
            "chat_format": "tokenizer.apply_chat_template via TRL messages + assistant_only_loss",
            "platform_intent": "google_colab_gpu_qlora",
            "ship_gate": "docs/ADAPTER_ACCEPTANCE_CRITERIA.md",
        }
        (out_dir / "training_summary.json").write_text(
            json.dumps(summary, indent=2) + "\n", encoding="utf-8"
        )
        _write_status(out_dir, "COMPLETE", {"duration_seconds": duration_s})

        print(f"Adapter saved to {out_dir}")
        print(f"Training duration seconds: {duration_s:.1f}")
        print(f"Metrics: {json.dumps(metrics)}")
        print("Do NOT ship this adapter without held-out comparison + human review.")
        return 0
    except Exception as exc:
        _write_status(out_dir, "FAILED", {"error": str(exc)})
        print(f"Training failed: {exc}")
        raise


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        description="Zoe Colab GPU QLoRA trainer (requires explicit acknowledgement).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=CANONICAL_CONFIG,
    )
    parser.add_argument(TRAIN_ACK_FLAG, action="store_true", dest="ack")
    parser.add_argument(FORCE_OVERWRITE_FLAG, action="store_true", dest="force_overwrite")
    parser.add_argument("--dry-check-config", action="store_true")
    args, _unknown = parser.parse_known_args(argv)

    if args.dry_check_config:
        try:
            import torch
            from training.scripts import load_yaml_config

            cfg = load_yaml_config(args.config)
            print("Config OK. Top-level keys:", sorted(cfg.keys()))
            print("Canonical intended config: training/config/colab_qlora.yaml")
            print("Model:", cfg.get("model", {}).get("name"))
            print("Train path:", cfg.get("data", {}).get("train_path"))
            print("Val path:", cfg.get("data", {}).get("validation_path"))
            print("Held-out path:", cfg.get("data", {}).get("held_out_eval_path"))
            print("Output:", cfg.get("training", {}).get("output_dir"))
            print("CUDA available:", torch.cuda.is_available())
            if torch.cuda.is_available():
                print("CUDA device:", torch.cuda.get_device_name(0))
            print("load_in_4bit:", (cfg.get("quantization") or {}).get("load_in_4bit"))
            data = cfg.get("data") or {}
            train_p = Path(data["train_path"])
            val_p = Path(data["validation_path"])
            held_p = Path(data["held_out_eval_path"])
            if not train_p.exists():
                print(
                    f"NOTE: train split missing at {train_p} "
                    "(run prepare_dataset --pilot on the Colab host)."
                )
            errs = assert_train_not_held_out(train_p, held_p, val_p) if train_p.exists() else []
            if errs:
                print("Guard findings:")
                for err in errs:
                    print(f"  - {err}")
                return 1
            if train_p.exists():
                print("Guards OK.")
            if not torch.cuda.is_available():
                print(
                    "WARNING: CUDA not available — Colab QLoRA will refuse to train "
                    "until a GPU runtime is selected."
                )
            return 0
        except Exception as exc:  # noqa: BLE001
            print(f"Config check failed: {exc}")
            return 1

    if not args.ack:
        return _refuse_without_ack(argv)

    print("ACK received — starting Colab GPU QLoRA path (may download/load model weights).")
    return _run_training(args.config, force_overwrite=bool(args.force_overwrite))


if __name__ == "__main__":
    raise SystemExit(main())
