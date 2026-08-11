"""Model loading and text generation for Zoe AI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, PreTrainedModel, PreTrainedTokenizerBase

from core.config import load_settings

tokenizer: PreTrainedTokenizerBase | None = None
model: PreTrainedModel | None = None
_model_load_count: int = 0
_adapter_attached: bool = False


class ModelLoadError(RuntimeError):
    """Raised when the configured Hugging Face model cannot be loaded."""


def _get_model_name() -> str:
    """Read MODEL_NAME from config/settings.txt via core.config."""
    model_name = load_settings().get("MODEL_NAME")
    if not model_name:
        raise ModelLoadError("MODEL_NAME is missing from config/settings.txt.")
    return model_name


def _use_cuda() -> bool:
    """Return True when a CUDA GPU is available for inference."""
    return torch.cuda.is_available()


def _torch_dtype() -> torch.dtype:
    """Use half precision on GPU and full precision on CPU."""
    return torch.float16 if _use_cuda() else torch.float32


def _model_device(loaded_model: PreTrainedModel) -> torch.device:
    """Resolve the device where model weights live."""
    if hasattr(loaded_model, "device"):
        return loaded_model.device
    return next(loaded_model.parameters()).device


def _format_prompt(
    loaded_tokenizer: PreTrainedTokenizerBase,
    messages: list[dict[str, str]],
) -> str:
    """Format chat messages with the tokenizer chat template when supported."""
    if getattr(loaded_tokenizer, "chat_template", None):
        return loaded_tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

    return messages[-1]["content"]


def is_model_loaded() -> bool:
    """Return True when the model and tokenizer are cached in memory."""
    return tokenizer is not None and model is not None


def get_model_load_count() -> int:
    """Return how many times the model weights were loaded in this process."""
    return _model_load_count


def is_adapter_attached() -> bool:
    """Return True when an optional PEFT adapter is attached to the base model."""
    return _adapter_attached


def _adapter_enabled() -> bool:
    """Optional PEFT adapter is OFF unless explicitly enabled in settings."""
    settings = load_settings()
    flag = str(settings.get("ADAPTER_ENABLED", "false")).strip().lower()
    return flag in {"1", "true", "yes", "on"}


def _adapter_path() -> Path | None:
    settings = load_settings()
    raw = str(settings.get("ADAPTER_PATH", "")).strip()
    if not raw:
        return None
    return Path(raw)


def _maybe_attach_adapter(loaded_model: PreTrainedModel) -> PreTrainedModel:
    """Attach a reviewed PEFT adapter when explicitly enabled.

    Default runtime behavior is unchanged: no adapter unless ADAPTER_ENABLED=true
    and ADAPTER_PATH points at a completed adapter directory.
    """
    global _adapter_attached
    if not _adapter_enabled():
        _adapter_attached = False
        return loaded_model

    path = _adapter_path()
    if path is None:
        raise ModelLoadError(
            "ADAPTER_ENABLED is true but ADAPTER_PATH is empty. "
            "Disable the adapter or set a valid path."
        )
    if not path.exists():
        raise ModelLoadError(f"ADAPTER_PATH does not exist: {path}")
    # Refuse incomplete/failed training artifacts.
    incomplete = path / "TRAINING_INCOMPLETE"
    failed_marker = path / "TRAINING_FAILED"
    status_file = path / "TRAINING_STATUS.json"
    complete = path / "TRAINING_COMPLETE"
    if failed_marker.exists() or (incomplete.exists() and not complete.exists()):
        raise ModelLoadError(
            f"Adapter at {path} looks incomplete or failed. "
            "Do not enable until training finishes and held-out review passes."
        )
    if status_file.exists():
        try:
            status = json_loads_status(status_file)
        except Exception:
            status = {}
        if str(status.get("status", "")).upper() in {"FAILED", "RUNNING"}:
            raise ModelLoadError(
                f"Adapter at {path} status is {status.get('status')!r}; refusing to load."
            )
    if not complete.exists():
        raise ModelLoadError(
            f"Adapter at {path} is missing TRAINING_COMPLETE. "
            "Refusing to enable an unverified or incomplete adapter."
        )
    if not (path / "adapter_config.json").exists():
        raise ModelLoadError(
            f"Adapter at {path} is missing adapter_config.json; refusing to load."
        )

    try:
        from peft import PeftModel
    except ImportError as exc:
        raise ModelLoadError(
            "ADAPTER_ENABLED requires the optional 'peft' package "
            "(see requirements-training.txt)."
        ) from exc

    print(f"Attaching PEFT adapter from {path} ...")
    adapted = PeftModel.from_pretrained(loaded_model, str(path))
    _adapter_attached = True
    return adapted


def json_loads_status(path: Path) -> dict[str, Any]:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def load_model() -> tuple[PreTrainedTokenizerBase, PreTrainedModel]:
    """Load the configured Hugging Face model once and reuse it."""
    global tokenizer, model, _model_load_count, _adapter_attached

    if tokenizer is not None and model is not None:
        return tokenizer, model

    model_name = _get_model_name()
    device_label = "CUDA GPU" if _use_cuda() else "CPU"
    print(f"Loading {model_name} on {device_label}...")

    try:
        loaded_tokenizer = AutoTokenizer.from_pretrained(model_name)
        dtype = _torch_dtype()

        if _use_cuda():
            loaded_model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=dtype,
                device_map="auto",
            )
        else:
            loaded_model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=dtype,
            )
            loaded_model.to("cpu")

        loaded_model = _maybe_attach_adapter(loaded_model)

    except OSError as exc:
        raise ModelLoadError(
            f"Could not download or load '{model_name}'. Check the name and your connection."
        ) from exc
    except ModelLoadError:
        raise
    except Exception as exc:
        raise ModelLoadError(
            f"Failed to load '{model_name}': {exc}"
        ) from exc

    tokenizer = loaded_tokenizer
    model = loaded_model
    _model_load_count += 1

    if _adapter_attached:
        print("Zoe is ready (base + optional adapter)!")
    else:
        print("Zoe is ready!")

    return tokenizer, model


def generate_text(
    loaded_tokenizer: PreTrainedTokenizerBase,
    loaded_model: PreTrainedModel,
    messages: list[dict[str, str]],
    max_new_tokens: int = 256,
) -> str:
    """Generate assistant text from formatted chat messages."""
    text = _format_prompt(loaded_tokenizer, messages)
    device = _model_device(loaded_model)
    inputs: Any = loaded_tokenizer(text, return_tensors="pt").to(device)

    outputs = loaded_model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=True,
        temperature=0.7,
        top_p=0.9,
    )

    input_length = inputs.input_ids.shape[1]
    response = loaded_tokenizer.decode(
        outputs[0][input_length:],
        skip_special_tokens=True,
    )

    return response.strip()
