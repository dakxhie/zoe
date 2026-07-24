"""Hugging Face model loading and chat generation for Zoe AI."""

from __future__ import annotations

from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, PreTrainedModel, PreTrainedTokenizerBase

from core.config import load_settings
from rag.retriever import search

tokenizer: PreTrainedTokenizerBase | None = None
model: PreTrainedModel | None = None


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


def _format_prompt(loaded_tokenizer: PreTrainedTokenizerBase, prompt: str) -> str:
    """Format the user prompt with the tokenizer chat template when supported."""
    messages = [{"role": "user", "content": prompt}]

    if getattr(loaded_tokenizer, "chat_template", None):
        return loaded_tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

    return prompt


def _retrieve_context(user_prompt: str, top_k: int = 3) -> list[dict[str, str]]:
    """Retrieve relevant personal notes from ChromaDB for RAG."""
    try:
        return search(user_prompt, top_k=top_k)
    except Exception:
        # If retrieval is unavailable, generation falls back to the normal prompt.
        return []


def _format_retrieved_notes(notes: list[dict[str, str]]) -> str:
    """Join retrieved note content into one context block."""
    return "\n\n".join(note["content"] for note in notes)


def _build_rag_prompt(user_question: str, context: str) -> str:
    """Build the RAG-augmented prompt using retrieved note context."""
    return (
        "You are Zoe.\n\n"
        "Use the following context to answer.\n\n"
        "Context:\n\n"
        f"{context}\n\n"
        "If the answer is not contained in the context, answer normally.\n\n"
        f"User:\n\n{user_question}"
    )


def _build_generation_prompt(user_prompt: str) -> str:
    """Prepare the prompt passed to the model, injecting RAG context when available."""
    # RAG injection: search personal notes before every response.
    retrieved_notes = _retrieve_context(user_prompt, top_k=3)

    if not retrieved_notes:
        return user_prompt

    context = _format_retrieved_notes(retrieved_notes)
    return _build_rag_prompt(user_prompt, context)


def load_model() -> tuple[PreTrainedTokenizerBase, PreTrainedModel]:
    """Load the configured Hugging Face model once and reuse it."""
    global tokenizer, model

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

    except OSError as exc:
        raise ModelLoadError(
            f"Could not download or load '{model_name}'. Check the name and your connection."
        ) from exc
    except Exception as exc:
        raise ModelLoadError(
            f"Failed to load '{model_name}': {exc}"
        ) from exc

    tokenizer = loaded_tokenizer
    model = loaded_model

    print("Zoe is ready!")

    return tokenizer, model


def generate_response(prompt: str, max_new_tokens: int = 256) -> str:
    """Generate an assistant reply for the given user prompt."""
    loaded_tokenizer, loaded_model = load_model()

    # RAG injection point: augment the user prompt with retrieved notes.
    generation_prompt = _build_generation_prompt(prompt)
    text = _format_prompt(loaded_tokenizer, generation_prompt)
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
