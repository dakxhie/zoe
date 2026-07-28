"""Pytest coverage for model caching behavior."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import brain.generation as generation


def test_load_model_caches_tokenizer_and_weights() -> None:
    """Load the model only once and reuse cached objects afterward."""
    generation.tokenizer = None
    generation.model = None
    generation._model_load_count = 0

    mock_tokenizer = MagicMock()
    mock_tokenizer.chat_template = None
    mock_model = MagicMock()

    with patch.object(generation, "_get_model_name", return_value="test-model"), patch.object(
        generation.AutoTokenizer,
        "from_pretrained",
        return_value=mock_tokenizer,
    ) as tokenizer_loader, patch.object(
        generation.AutoModelForCausalLM,
        "from_pretrained",
        return_value=mock_model,
    ) as model_loader:
        first_tokenizer, first_model = generation.load_model()
        second_tokenizer, second_model = generation.load_model()

    assert tokenizer_loader.call_count == 1
    assert model_loader.call_count == 1
    assert generation.get_model_load_count() == 1
    assert generation.is_model_loaded()
    assert first_tokenizer is second_tokenizer
    assert first_model is second_model
