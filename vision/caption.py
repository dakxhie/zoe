"""Image captioning for Zoe AI."""

from __future__ import annotations

import logging

import torch
from PIL import Image
from transformers import BlipForConditionalGeneration, BlipProcessor

from vision.loader import VisionLoaderError, load_image

logger = logging.getLogger(__name__)

DEFAULT_CAPTION_MODEL = "Salesforce/blip-image-captioning-base"

_processor: BlipProcessor | None = None
_model: BlipForConditionalGeneration | None = None


def _use_cuda() -> bool:
    """Return True when a CUDA GPU is available for inference."""
    return torch.cuda.is_available()


def _load_caption_model() -> tuple[BlipProcessor, BlipForConditionalGeneration] | None:
    """Load the BLIP captioning model once and reuse it."""
    global _processor, _model

    if _processor is not None and _model is not None:
        return _processor, _model

    try:
        loaded_processor = BlipProcessor.from_pretrained(DEFAULT_CAPTION_MODEL)
        loaded_model = BlipForConditionalGeneration.from_pretrained(DEFAULT_CAPTION_MODEL)

        if _use_cuda():
            loaded_model = loaded_model.to("cuda")

        loaded_model.eval()
    except Exception as exc:
        logger.warning("Failed to load caption model: %s", exc)
        return None

    _processor = loaded_processor
    _model = loaded_model
    return _processor, _model


def describe_loaded_image(image: Image.Image) -> str:
    """Generate a caption for a loaded PIL image."""
    loaded = _load_caption_model()
    if loaded is None:
        return ""

    processor, model = loaded

    try:
        rgb_image = image.convert("RGB")
        inputs = processor(images=rgb_image, return_tensors="pt")

        if _use_cuda():
            inputs = {key: value.to(model.device) for key, value in inputs.items()}

        with torch.no_grad():
            outputs = model.generate(**inputs, max_new_tokens=50)

        caption = processor.decode(outputs[0], skip_special_tokens=True)
        return caption.strip()
    except Exception as exc:
        logger.warning("Image caption generation failed: %s", exc)
        return ""


def describe_image(image_path: str) -> str:
    """Generate a caption for an image file."""
    try:
        image = load_image(image_path)
    except VisionLoaderError as exc:
        logger.warning("Caption image load failed: %s", exc)
        return ""
    except Exception as exc:
        logger.warning("Unexpected caption image load failure: %s", exc)
        return ""

    return describe_loaded_image(image)
