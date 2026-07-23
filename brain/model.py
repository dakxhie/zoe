from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

MODEL_NAME="Qwen/Qwen2.5-3B-Instruct"

tokenizer=None
model=None

def load_model():
    global tokenizer,model

    tokenizer=AutoTokenizer.from_pretrained(MODEL_NAME)

    model=AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        dtype=torch.float16,
        device_map="auto"
    )

    return tokenizer,model
