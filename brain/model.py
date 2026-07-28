"""Hugging Face model loading and chat generation for Zoe AI."""

from __future__ import annotations

from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, PreTrainedModel, PreTrainedTokenizerBase

from code.retriever import search_code
from core.config import load_settings
from memory.retriever import search_memories
from memory.store import save_memory
from pdf.retriever import search_documents
from rag.retriever import search

tokenizer: PreTrainedTokenizerBase | None = None
model: PreTrainedModel | None = None

MEMORY_ACKNOWLEDGEMENT = "Got it. I'll remember that."
NOTES_HEADING = "========================\nPersonal Notes\n========================"
MEMORIES_HEADING = "========================\nLearned Memories\n========================"
PDF_HEADING = "========================\nPDF Documents\n========================"
CODE_HEADING = "========================\nCode\n========================"


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


def _retrieve_notes(user_prompt: str, top_k: int = 3) -> list[dict[str, str]]:
    """Retrieve relevant personal notes from the RAG index."""
    try:
        return search(user_prompt, top_k=top_k)
    except Exception:
        return []


def _retrieve_memories(user_prompt: str, top_k: int = 3) -> list[dict[str, str]]:
    """Retrieve relevant learned conversation memories."""
    try:
        return search_memories(user_prompt, top_k=top_k)
    except Exception:
        return []


def _retrieve_documents(user_prompt: str, top_k: int = 5) -> list[dict[str, str | int]]:
    """Retrieve relevant PDF document chunks."""
    try:
        return search_documents(user_prompt, top_k=top_k)
    except Exception:
        return []


def _retrieve_code(user_prompt: str, top_k: int = 5) -> list[dict[str, str]]:
    """Retrieve relevant indexed code chunks."""
    try:
        return search_code(user_prompt, top_k=top_k)
    except Exception:
        return []


def _join_content(items: list[dict[str, str | int]]) -> str:
    """Join retrieved document content into one text block."""
    return "\n\n".join(item["content"] for item in items)


def _build_merged_context(user_prompt: str) -> str:
    """Merge note, memory, PDF, and code retrieval results into one context string."""
    # RAG + memory + PDF + code injection: search all sources before every response.
    notes = _retrieve_notes(user_prompt, top_k=3)
    memories = _retrieve_memories(user_prompt, top_k=3)
    documents = _retrieve_documents(user_prompt, top_k=5)
    code_results = _retrieve_code(user_prompt, top_k=5)

    sections: list[str] = []

    if notes:
        sections.append(f"{NOTES_HEADING}\n\n{_join_content(notes)}")

    if memories:
        sections.append(f"{MEMORIES_HEADING}\n\n{_join_content(memories)}")

    if documents:
        sections.append(f"{PDF_HEADING}\n\n{_join_content(documents)}")

    if code_results:
        sections.append(f"{CODE_HEADING}\n\n{_join_content(code_results)}")

    return "\n\n".join(sections)


def _build_chat_messages(user_question: str) -> list[dict[str, str]]:
    """Build chat messages, injecting merged note, memory, PDF, and code context when available."""
    context = _build_merged_context(user_question)

    if not context:
        return [{"role": "user", "content": user_question}]

    return [
        {
            "role": "system",
            "content": (
                "You are Zoe.\n"
                "Answer using the provided context whenever possible.\n"
                "If the answer is not in the context, answer normally.\n\n"
                "Context:\n"
                + context
            ),
        },
        {
            "role": "user",
            "content": user_question,
        },
    ]


def _try_save_memory(text: str) -> bool:
    """Attempt to store a conversation memory without interrupting chat."""
    try:
        return save_memory(text)
    except Exception:
        return False


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
    # Memory storage injection: save personal messages before generation.
    if _try_save_memory(prompt):
        return MEMORY_ACKNOWLEDGEMENT

    loaded_tokenizer, loaded_model = load_model()

    # RAG + memory + PDF + code injection point: build chat messages with merged context.
    messages = _build_chat_messages(prompt)
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
