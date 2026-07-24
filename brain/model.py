from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

from core.config import load_settings

settings = load_settings()

MODEL_NAME = settings["MODEL_NAME"]

tokenizer = None
model = None

def load_model():
    global tokenizer, model

    if tokenizer is not None and model is not None:
        return tokenizer, model

    print(f"Loading {MODEL_NAME}...")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16,
        device_map="auto"
    )

    print("✅ Zoe is ready!")

    return tokenizer, model


def generate_response(prompt: str, max_new_tokens: int = 256):

    tokenizer, model = load_model()

    messages = [
        {
            "role": "system",
            "content": (
                "You are Zoe, a friendly, intelligent AI companion. "
                "Answer naturally, clearly, and helpfully."
            )
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    inputs = tokenizer(text, return_tensors="pt").to(model.device)

    outputs = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=True,
        temperature=0.7,
        top_p=0.9,
    )

    response = tokenizer.decode(
        outputs[0][inputs.input_ids.shape[1]:],
        skip_special_tokens=True
    )

    return response.strip()
